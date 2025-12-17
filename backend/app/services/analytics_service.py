
import json
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import ScorecardVersion, ScoreRequest, Party, Feature
from app.scorecard import ScorecardEngine

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_scorecard_versions(self) -> List[Dict]:
        """Get all scorecard versions with metadata."""
        versions = self.db.query(ScorecardVersion).order_by(ScorecardVersion.created_at.desc()).all()
        return [
            {
                "id": v.id,
                "version": v.version,
                "status": v.status,
                "created_at": v.created_at,
                "activated_at": v.activated_at,
                "archived_at": v.archived_at,
                "ml_auc": self._safe_float(v.ml_auc),
                "training_data_count": v.training_data_count,
                "source": v.source,
                "notes": v.notes,  # Include rejection reason
                "weights": v.weights if isinstance(v.weights, dict) else json.loads(v.weights) if v.weights else {}
            }
            for v in versions
        ]

    def _safe_float(self, value: Any) -> float | None:
        """Safely convert float, returning None for NaN/Infinity."""
        import math
        if value is None:
            return None
        try:
            val = float(value)
            if math.isnan(val) or math.isinf(val):
                return None
            return val
        except (ValueError, TypeError):
            return None

    def get_weights_evolution(self, top_n: int = 5) -> Dict:
        """Get weight evolution for top features."""
        versions = self.db.query(ScorecardVersion).order_by(ScorecardVersion.id).all()
        
        # Parse weights
        history = []
        all_features = set()
        
        for v in versions:
            try:
                weights = v.weights if isinstance(v.weights, dict) else json.loads(v.weights)
                history.append({
                    "version": v.version,
                    "weights": weights,
                    "created_at": v.created_at
                })
                all_features.update(weights.keys())
            except Exception as e:
                logger.error(f"Failed to parse weights for v{v.version}: {e}")
                continue
                
        # Identify top features by variance across versions
        variances = {}
        for feature in all_features:
            values = []
            for h in history:
                w = h["weights"].get(feature, 0)
                values.append(w)
            
            # Simple variance
            import numpy as np
            if len(values) > 1:
                variances[feature] = np.var(values)
            else:
                variances[feature] = 0
                
        top_features = sorted(variances.items(), key=lambda x: x[1], reverse=True)[:top_n]
        top_feature_names = [f[0] for f in top_features]
        
        # Format for frontend chart
        # Series for each feature
        series = []
        for feature in top_feature_names:
            points = []
            for h in history:
                points.append({
                    "version": h["version"],
                    "weight": h["weights"].get(feature, 0),
                    "date": h["created_at"].isoformat()
                })
            series.append({"name": feature, "data": points})
            
        return {
            "versions": [h["version"] for h in history],
            "series": series
        }

    def get_score_impact(self, version_id: int, compare_to_id: int = None, sample_size: int = 100) -> Dict:
        """
        Analyze impact of a new scorecard version by re-scoring a sample of parties.
        Returns score distribution delta.
        """
        # Get target version
        target_v = self.db.query(ScorecardVersion).filter_by(id=version_id).first()
        if not target_v:
            raise ValueError("Target version not found")
            
        # Get comparison version (default to previous active)
        if compare_to_id:
            compare_v = self.db.query(ScorecardVersion).filter_by(id=compare_to_id).first()
        else:
            # Find the version before this one? Or the currently archived one?
            # Assuming sequential IDs
            compare_v = self.db.query(ScorecardVersion).filter(
                ScorecardVersion.id < version_id,
                ScorecardVersion.status.in_(['active', 'archived'])
            ).order_by(ScorecardVersion.id.desc()).first()
            
        if not compare_v:
             # Comparison against baseline (0?) or just return distribution
             logger.warning("No comparison version found")
             compare_v = None

        # Load engines
        target_config = target_v.to_config_dict()
        target_engine = ScorecardEngine(config=target_config)
        
        compare_engine = None
        if compare_v:
            compare_config = compare_v.to_config_dict()
            compare_engine = ScorecardEngine(config=compare_config)

        # Get sample of parties with recent scores
        # We want parties that have features available.
        # Fetching parties with features valid_to IS NULL
        parties = self.db.query(Party).join(Feature).group_by(Party.id).limit(sample_size).all()
        
        results = []
        
        for p in parties:
            # Fetch features
            features = self.db.query(Feature).filter(
                Feature.party_id == p.id,
                Feature.valid_to == None
            ).all()
            feature_dict = {f.feature_name: f.feature_value for f in features}
            
            # Score Target
            try:
                t_score_res = target_engine.compute_scorecard_score(feature_dict)
                t_score = t_score_res['score']
            except:
                t_score = 0
            
            # Score Compare
            c_score = 0
            if compare_engine:
                try:
                    c_score_res = compare_engine.compute_scorecard_score(feature_dict)
                    c_score = c_score_res['score']
                except:
                    c_score = 0
            
            results.append({
                "party_id": p.id,
                "party_name": p.name, # Assuming Name exists, models.py Step 108 said Party has no name? 
                # models.py has `name`. Wait, Step 134 thought: "Validating models.py: Party has `name`, `tax_id`."
                # So `p.name` is fine.
                "new_score": t_score,
                "old_score": c_score,
                "delta": t_score - c_score
            })
            
        # Aggregations
        avg_delta = sum(r['delta'] for r in results) / len(results) if results else 0
        
        return {
            "version_new": target_v.version,
            "version_old": compare_v.version if compare_v else "N/A",
            "avg_delta": round(avg_delta, 2),
            "sample_size": len(results),
            "details": results
        }
