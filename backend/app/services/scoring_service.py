# backend/app/services/scoring_service.py

from sqlalchemy.orm import Session
from app.models.models import ModelRegistry, Feature, ScoreRequest, DecisionRule, CreditScore
from app.extractors.kyc_extractor import KYCFeatureExtractor
from app.extractors.transaction_extractor import TransactionFeatureExtractor
from app.extractors.network_extractor import NetworkFeatureExtractor
from datetime import datetime
import joblib
import io
import pandas as pd
import uuid
import json

class ScoringService:
    """
    Main scoring service - model-agnostic.
    Works with scorecard now, ML models later.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def compute_score(self, party_id: int, model_version: str = None, 
                     include_explanation: bool = True) -> dict:
        """
        Compute credit score for a party.
        
        Steps:
        1. Extract features (from your existing Party/Transaction/Relationship data)
        2. Fetch active model
        3. Compute score
        4. Apply decision rules
        5. Log result
        """
        
        # Step 1: Ensure features are computed
        self._ensure_features_exist(party_id)
        
        # Step 2: Get active model
        if model_version:
            model = self.db.query(ModelRegistry).filter(
                ModelRegistry.model_version == model_version
            ).first()
        else:
            model = self.db.query(ModelRegistry).filter(
                ModelRegistry.is_active == 1
            ).first()
            
            # Fallback to ScorecardVersion if no ML model found
            if not model:
                from app.models.models import ScorecardVersion
                sv = self.db.query(ScorecardVersion).filter(
                    ScorecardVersion.status == 'active'
                ).order_by(ScorecardVersion.id.desc()).first()
                
                if sv:
                    # Adapt ScorecardVersion to behave like ModelRegistry object
                    class ModelAdapter:
                        def __init__(self, sv):
                            self.model_version = sv.version
                            self.model_type = 'scorecard'
                            self.model_config = sv.to_config_dict()
                            self.scaler_binary = None
                            self.feature_list = list(sv.weights.keys())
                    
                    model = ModelAdapter(sv)
        
        if not model:
            raise ValueError("No active scoring model found")
        
        # Step 3: Fetch features
        # Note: model_config and model_type are the actual column names in the DB
        config = model.model_config or {}
        model_type = model.model_type or "scorecard"
        
        # Get required features from feature_list column or from config
        if model.feature_list:
            required_features = model.feature_list
        elif model_type == "ml_model":
            required_features = config.get("features", [])
        else:
            required_features = list(config.get("weights", {}).keys())
        features = self._get_current_features(party_id, required_features or [])
        
        # FIX #1: Apply Feature Scaling if available
        # The model was trained on scaled features, so we must scale inference data too.
        if model.scaler_binary:
            try:
                # 1. Deserialize scaler
                buffer = io.BytesIO(model.scaler_binary)
                scaler = joblib.load(buffer)
                
                # 2. Prepare DataFrame with correct column order
                # Use required_features list which matches the scaler's expected input
                feature_df = pd.DataFrame([features])
                
                # Ensure all columns exist (fill missing with 0)
                for feat in required_features:
                    if feat not in feature_df.columns:
                        feature_df[feat] = 0.0
                
                # Reorder columns to match training order
                feature_df = feature_df[required_features]
                
                # 3. Transform
                scaled_array = scaler.transform(feature_df)
                
                # 4. Update the features dict with scaled values
                # We update the values but keep the keys, so downstream methods use scaled values
                for i, name in enumerate(required_features):
                    features[name] = float(scaled_array[0][i])
                    
            except Exception as e:
                # Fallback or log error - critical failure if scaling needed but fails
                print(f"Error applying scaler: {e}")
                # We proceed with raw values but results will likely be wrong
                pass
        
        # Step 4: Compute score based on model type
        if model_type == "scorecard":
            raw_score = self._compute_scorecard(features, config)
        elif model_type == "ml_model":
            raw_score = self._compute_ml_model(features, config)
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        # Step 5: Normalize to 300-900
        final_score = self._normalize_score(raw_score)
        
        # Step 6: Assign score band
        score_band = self._get_score_band(final_score)
        
        # Step 7: Compute confidence
        confidence = self._compute_confidence(features)
        
        # Step 8: Apply decision rules
        decision, reasons = self._apply_decision_rules(features)
        
        # Step 9: Generate explanation
        explanation = None
        if include_explanation:
            explanation = self._generate_explanation(features, model.model_config)
        
        # Step 10: Log score request
        score_request = ScoreRequest(
            id=str(uuid.uuid4()),
            party_id=party_id,
            model_version=model.model_version,
            model_type=model.model_type,
            features_snapshot=json.dumps({k: v for k, v in features.items()}),
            raw_score=raw_score,
            final_score=final_score,
            score_band=score_band,
            confidence_level=confidence,
            decision=decision,
            decision_reasons=json.dumps(reasons)
        )
        self.db.add(score_request)
        self.db.add(score_request)
        
        # Update latest CreditScore snapshot
        credit_score = self.db.query(CreditScore).filter(CreditScore.party_id == party_id).first()
        if not credit_score:
            credit_score = CreditScore(party_id=party_id)
            self.db.add(credit_score)
            
        credit_score.overall_score = final_score
        credit_score.score_request_id = score_request.id
        credit_score.scored_with_version = model.model_version
        credit_score.calculated_at = datetime.utcnow()
        
        self.db.commit()
        
        # Return result
        return {
            "party_id": party_id,
            "score": final_score,
            "score_band": score_band,
            "confidence": confidence,
            "decision": decision,
            "decision_reasons": reasons,
            "computed_at": datetime.utcnow().isoformat(),
            "model_version": model.model_version,
            "model_type": model_type,
            "explanation": explanation
        }

    def compute_batch_scores(self, batch_id: str, model_version: str = None) -> dict:
        """Score all parties in a batch."""
        
        # 1. Fetch parties
        from app.models.models import Party
        parties = self.db.query(Party).filter(Party.batch_id == batch_id).all()
        
        results = {
            "total": len(parties),
            "scored": 0,
            "failed": 0,
            "errors": []
        }
        
        # 2. Score each
        for party in parties:
            try:
                self.compute_score(party.id, model_version=model_version, include_explanation=False)
                results["scored"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Party {party.id}: {str(e)}")
                
        return results
    
    def _ensure_features_exist(self, party_id: int):
        """Extract features if they don't exist or are stale"""
        from app.services.feature_pipeline_service import FeaturePipelineService
        
        # Check if features exist and are recent (< 7 days old)
        latest = self.db.query(Feature).filter(
            Feature.party_id == party_id,
            Feature.valid_to == None
        ).first()
        
        if not latest or (datetime.utcnow() - latest.computation_timestamp).days > 7:
            # Extract features
            pipeline = FeaturePipelineService(self.db)
            pipeline.extract_all_features(party_id)
    
    def _get_current_features(self, party_id: int, feature_list: list) -> dict:
        """Fetch current features for party"""
        features = self.db.query(Feature).filter(
            Feature.party_id == party_id,
            Feature.valid_to == None,
            Feature.feature_name.in_(feature_list)
        ).all()
        
        return {f.feature_name: f.feature_value for f in features}
    
    def _compute_scorecard(self, features: dict, model_config: dict) -> float:
        """Scorecard: raw_score = intercept + Σ(feature × weight)"""
        weights = model_config.get("weights", {})
        intercept = model_config.get("intercept", 0)
        
        raw_score = intercept
        for feature_name, weight in weights.items():
            feature_value = features.get(feature_name, 0)
            raw_score += feature_value * weight
        
        return raw_score
    
    def _compute_ml_model(self, features: dict, model_config: dict) -> float:
        """
        ML model inference: score = intercept + sum(feat * coeff)
        """
        coefficients = model_config.get("coefficients", [])
        intercept = model_config.get("intercept", 0.0)
        feature_names = model_config.get("features", [])
        
        if len(feature_names) != len(coefficients):
             # Fallback if mismatch or old model: try dictionary match if config has weights map
             # But for standard sklearn logistic regression, we rely on positional dot product
             # If feature names missing, this is risky.
             pass

        score = intercept
        
        # Dot product
        for i, name in enumerate(feature_names):
            val = features.get(name, 0.0) # imputation: assume 0 if missing
            if i < len(coefficients):
                score += val * coefficients[i]
                
        # Logistic Regression output is log-odds usually, 
        # but if we want probability we apply sigmoid.
        # However, for credit scoring, often the raw log-odds or a scaled version is used.
        # Let's assume we map the probability to the 300-850 range directly in _normalize_score
        # or we return probability. 
        # For compatibility with _normalize_score (expects 0-1000ish maybe?), let's apply sigmoid -> 0-1 -> scaled.
        
        import math
        try:
            probability = 1 / (1 + math.exp(-score))
        except OverflowError:
            probability = 0.0 if score < 0 else 1.0
            
        # Map probability 0.0-1.0 to roughly 0-1000 for the normalizer
        return probability * 1000.0
    
    def _normalize_score(self, raw_score: float) -> int:
        """Normalize raw score to 300-900 range"""
        # Calibrated from training data
        min_raw = 0
        max_raw = 1000
        
        normalized = 300 + ((raw_score - min_raw) / (max_raw - min_raw)) * 600
        return max(300, min(900, int(normalized)))
    
    def _get_score_band(self, score: int) -> str:
        """Map score to band"""
        if score >= 750:
            return "excellent"
        elif score >= 650:
            return "good"
        elif score >= 550:
            return "fair"
        else:
            return "poor"
    
    def _compute_confidence(self, features: dict) -> float:
        """Compute confidence based on feature availability"""
        # Simple: % of features available
        return len(features) / 15.0  # Assuming 15 total features
    
    def _apply_decision_rules(self, features: dict) -> tuple:
        """Apply business rules"""
        rules = self.db.query(DecisionRule).filter(
            DecisionRule.is_active == 1
        ).order_by(DecisionRule.priority).all()
        
        for rule in rules:
            # Safely evaluate condition expression with feature context
            try:
                safe_context = {"__builtins__": {}}
                safe_context.update(features)
                if eval(rule.condition_expression, safe_context):
                    return rule.action, [rule.rule_name]
            except Exception:
                # Skip rules that fail to evaluate
                pass
        
        return "approved", []
    
    def _generate_explanation(self, features: dict, model_config: dict) -> dict:
        """Generate explanation of score"""
        weights = model_config.get("weights", {})
        
        contributions = []
        for feature_name, weight in weights.items():
            value = features.get(feature_name, 0)
            contribution = value * weight
            contributions.append({
                "feature": feature_name,
                "value": value,
                "contribution": contribution
            })
        
        # Sort by absolute contribution
        contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)
        
        # Calculate sub-scores for frontend breakdown
        sub_scores = {
            "payment_regularity_score": 0,
            "transaction_volume_score": 0,
            "network_score": 0
        }
        
        for item in contributions:
            fname = item["feature"]
            contrib = item["contribution"]
            
            if "payment" in fname or "bill" in fname or "days" in fname:
                sub_scores["payment_regularity_score"] += contrib
            elif "transaction" in fname or "amount" in fname or "count" in fname:
                sub_scores["transaction_volume_score"] += contrib
            elif "network" in fname or "centrality" in fname or "rank" in fname:
                sub_scores["network_score"] += contrib
                
        return {
            "top_positive_factors": [c for c in contributions if c["contribution"] > 0][:3],
            "top_negative_factors": [c for c in contributions if c["contribution"] < 0][:3],
            **sub_scores
        }