"""
Dagster definitions for KYCC Unified Pipeline.
Rebuilt to ensure clean architecture, robust path handling, and clear dependencies.
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from dagster import (
    Definitions,
    asset,
    AssetExecutionContext,
    define_asset_job,
    AssetSelection,
    AssetIn,
    AssetKey,
    Config,
    RunConfig
)

# Add workspace path
sys.path.insert(0, "/workspace")

# App Imports
from app.db.database import SessionLocal
from app.models.models import Batch, Party, Feature, ScoreRequest, GroundTruthLabel
from app.services.synthetic_seed_service import ingest_seed_file
from app.services.feature_pipeline_service import FeaturePipelineService
from app.services.feature_validation_service import FeatureValidationService
from app.scorecard import ScorecardEngine, get_version_service
from app.services.label_generation_service import LabelGenerationService
from app.validators.label_validator import LabelValidator
from app.validators.feature_label_validator import FeatureLabelValidator
from app.services.feature_matrix_builder import FeatureMatrixBuilder
from app.services.model_training_service import ModelTrainingService
from app.services.scorecard_version_service import ScorecardVersionService

# Helper to get robust data path
def get_data_path(filename: str) -> Path:
    """Resolve data path consistently across environments (Docker vs Host)."""
    # 1. Try relative to this file (backend/dagster_home/definitions.py -> backend/data)
    backend_root = Path(__file__).parent.parent
    path = backend_root / "data" / filename
    if path.exists():
        return path
    
    # 2. Try CWD fallback
    path_cwd = Path(os.getcwd()) / "data" / filename
    if path_cwd.exists():
        return path_cwd
        
    return path # Return primary path (caller handles non-existence)

# ==============================================================================
# SECTION 1: INGESTION
# ==============================================================================

@asset(
    name="ingest_synthetic_batch",
    description="Ingests customer profiles from JSON into Postgres",
    config_schema={"batch_id": str}
)
def ingest_synthetic_batch(context: AssetExecutionContext) -> str:
    batch_id = context.op_config["batch_id"]
    filename = f"{batch_id}_profiles.json"
    path = get_data_path(filename)
    
    if not path.exists():
        raise FileNotFoundError(f"Profiles file not found at {path}")
        
    context.log.info(f"Ingesting batch {batch_id} from {path}")
    
    # Validation: Ensure no labels in profiles
    with open(path, 'r') as f:
        data = json.load(f)
        parties = data.get("parties", []) if isinstance(data, dict) else data
        if parties and "will_default" in parties[0]:
             raise ValueError("Security Alert: Profiles file contains labels!")

    with SessionLocal() as db:
        result = ingest_seed_file(db, str(path), batch_id=batch_id)
        
        # Update Batch status to 'ingested' if needed, or rely on flow
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if batch:
            batch.status = 'ingested'
            db.commit()
            
    return batch_id

@asset(
    name="validate_ingestion",
    description="Validates ingestion counts"
)
def validate_ingestion(context: AssetExecutionContext, ingest_synthetic_batch: str):
    batch_id = ingest_synthetic_batch
    from app.db import crud
    
    with SessionLocal() as db:
        party_count = crud.count_parties(db, batch_id=batch_id) if hasattr(crud, "count_parties") else 0
        txn_count = crud.count_transactions(db, batch_id=batch_id) if hasattr(crud, "count_transactions") else 0
        
    context.log.info(f"Batch {batch_id}: {party_count} parties, {txn_count} transactions")
    
    if party_count == 0:
        raise ValueError(f"Ingestion failed: 0 parties found for {batch_id}")
        
    return {"batch_id": batch_id, "party_count": party_count}

# ==============================================================================
# SECTION 2: FEATURES
# ==============================================================================

@asset(name="kyc_features")
def kyc_features(context: AssetExecutionContext, validate_ingestion):
    batch_id = validate_ingestion["batch_id"]
    with SessionLocal() as db:
        svc = FeaturePipelineService(db)
        svc.run_single(batch_id=batch_id, source="kyc")
    return {"batch_id": batch_id, "source": "kyc"}

@asset(name="transaction_features")
def transaction_features(context: AssetExecutionContext, validate_ingestion):
    batch_id = validate_ingestion["batch_id"]
    with SessionLocal() as db:
        svc = FeaturePipelineService(db)
        svc.run_single(batch_id=batch_id, source="transaction")
    return {"batch_id": batch_id, "source": "transaction"}

@asset(name="network_features")
def network_features(context: AssetExecutionContext, validate_ingestion):
    batch_id = validate_ingestion["batch_id"]
    with SessionLocal() as db:
        svc = FeaturePipelineService(db)
        svc.run_single(batch_id=batch_id, source="network")
    return {"batch_id": batch_id, "source": "network"}

@asset(name="features_all")
def features_all(context: AssetExecutionContext, kyc_features, transaction_features, network_features):
    # Convergence point
    return {"batch_id": kyc_features["batch_id"]}

@asset(name="validate_features")
def validate_features(context: AssetExecutionContext, features_all):
    batch_id = features_all["batch_id"]
    with SessionLocal() as db:
        svc = FeatureValidationService(db)
        report = svc.generate_validation_report(batch_id=batch_id)
        
    context.log.info(f"Feature Validity: {report.get('completion_rate')}%")
    return report

# ==============================================================================
# SECTION 3: SCORING
# ==============================================================================

def _score_to_risk_bucket(score: float) -> str:
    if score < 500: return 'high'
    if score < 700: return 'medium'
    return 'low'

@asset(
    name="score_batch",
    description="Scores batch using active Scorecard",
    config_schema={"batch_id": str}
)
def score_batch(context: AssetExecutionContext, validate_features):
    batch_id = context.op_config["batch_id"]
    
    with SessionLocal() as db:
        # Load Scorecard (ensure initial exists)
        svc = ScorecardVersionService(db)
        svc.ensure_initial_version()
        
        scorecard_config = svc.get_active_scorecard()
        engine = ScorecardEngine(config=scorecard_config)
        version = scorecard_config.get('version', '1.0')
        
        parties = db.query(Party).filter(Party.batch_id == batch_id).all()
        
        scored = 0
        failures = 0
        
        for party in parties:
            try:
                # Fetch Features
                # Optimal: Batch fetch. For demo: Loop is okay.
                feats = db.query(Feature).filter(Feature.party_id == party.id, Feature.valid_to == None).all()
                feat_dict = {f.feature_name: f.feature_value for f in feats}
                
                # Compute
                result = engine.compute_scorecard_score(feat_dict)
                score = result['score']
                
                # Record
                req = ScoreRequest(
                    id=f"req_{party.id}_{batch_id}_{datetime.utcnow().timestamp()}",
                    party_id=party.id,
                    model_version=f"scorecard_v{version}",
                    model_type="scorecard",
                    scorecard_version_id=scorecard_config.get('id'),
                    final_score=score,
                    raw_score=float(result['raw_score']),
                    score_band=_score_to_risk_bucket(score),
                    features_snapshot=feat_dict,
                    request_timestamp=datetime.utcnow()
                )
                db.add(req)
                scored += 1
            except Exception as e:
                failures += 1
                context.log.debug(f"Failed party {party.id}: {e}")
                
        # Status Update
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if batch:
            batch.status = 'scored'
            batch.scored_at = datetime.utcnow()
            db.add(batch)
            
        db.commit()
        
    context.log.info(f"Scored {scored} parties. Failures: {failures}")
    return {"batch_id": batch_id, "scored": scored}

# ==============================================================================
# SECTION 4: OUTCOMES / LABELS
# ==============================================================================

@asset(
    name="generate_scorecard_labels",
    description="Generates synthetic labels based on scorecard thresholds",
    config_schema={"batch_id": str},
    ins={"score_batch": AssetIn(key=AssetKey("score_batch"))}
)
def generate_scorecard_labels(context: AssetExecutionContext, score_batch):
    batch_id = context.op_config["batch_id"]
    
    with SessionLocal() as db:
        # Get data for labeling service
        # (Simplified: Service queries DB itself)
        # Note: We pass empty lists because service fetches if not provided? 
        # Actually LabelGenerationService needs arguments. Let's provide them via DB fetch.
        
        # We need features and party IDs.
        # This duplicates logic in score_batch but required for label service API.
        # Or we can update LabelGenerationService to fetch?
        # Let's do manual fetch here to fit API.
        
        parties = db.query(Party).filter(Party.batch_id == batch_id).all()
        features_list = []
        party_ids = []
        for p in parties:
            feats = db.query(Feature).filter(Feature.party_id == p.id, Feature.valid_to == None).all()
            features_list.append({f.feature_name: f.feature_value for f in feats})
            party_ids.append(p.id)
            
        svc = LabelGenerationService(db, scorecard_version='1.0')
        result = svc.generate_labels_from_scorecard(
            features_list=features_list,
            party_ids=party_ids, 
            target_default_rate=0.05,
            batch_id=batch_id
        )
        
        # Status
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if batch:
            batch.status = 'outcomes_generated'
            batch.outcomes_generated_at = datetime.utcnow()
            batch.label_count = result.get('labels_created', 0)
            batch.default_rate = result.get('actual_default_rate', 0.0)
            db.add(batch)
        db.commit()
        
    context.log.info(f"Generated {result['labels_created']} labels.")
    return {"batch_id": batch_id, "source": "synthetic"}

@asset(
    name="ingest_observed_labels",
    description="Ingests observed labels from file",
    config_schema={"batch_id": str}
)
def ingest_observed_labels(context: AssetExecutionContext):
    batch_id = context.op_config["batch_id"]
    filename = f"{batch_id}_labels.json"
    path = get_data_path(filename)
    
    count = 0
    if path.exists():
        with open(path, 'r') as f:
            data = json.load(f)
            # Parse wrapper
            if isinstance(data, dict) and "profiles" in data:
                items = data["profiles"]
            elif isinstance(data, list):
                items = data
            else:
                items = []
                
            with SessionLocal() as db:
                # Pre-fetch parties for efficiency or lookup per item
                # Given small batch size, lookup per item is cleaner for this fix
                count = 0
                for item in items:
                    ext_id = item.get('party_id')
                    if not ext_id:
                        continue
                        
                    party = db.query(Party).filter(Party.external_id == ext_id).first()
                    if not party:
                        context.log.warning(f"Label found for unknown party {ext_id}, skipping.")
                        continue
                        
                    # Check for existing label to avoid duplicates/errors
                    existing = db.query(GroundTruthLabel).filter(GroundTruthLabel.party_id == party.id).first()
                    
                    if existing:
                        existing.will_default = item.get('will_default', item.get('default_outcome'))
                        existing.label_source = 'observed'
                        existing.dataset_batch = batch_id
                    else:
                        db.add(GroundTruthLabel(
                            party_id=party.id,  # Use Internal Integer ID
                            will_default=item.get('will_default', item.get('default_outcome')), 
                            label_source='observed',
                            dataset_batch=batch_id,
                            created_at=datetime.utcnow()
                        ))
                    count += 1
                db.commit()
                
    context.log.info(f"Ingested {count} observed labels")
    return {"batch_id": batch_id, "source": "observed", "count": count}

# ==============================================================================
# SECTION 5: TRAINING & REFINEMENT
# ==============================================================================

@asset(
    name="validate_labels",
    deps=["generate_scorecard_labels", "ingest_observed_labels"],
    config_schema={"batch_id": str} 
)
def validate_labels(context: AssetExecutionContext):
    batch_id = context.op_config["batch_id"]
    # Check if we have labels
    with SessionLocal() as db:
        count = db.query(GroundTruthLabel).join(Party).filter(Party.batch_id == batch_id).count()
        if count == 0:
            context.log.warning("No labels found for training!")
            # raise ValueError("No labels found") # Strict? Or warn?
            
    return batch_id

@asset(name="validate_feature_label_alignment")
def validate_feature_label_alignment(context: AssetExecutionContext, validate_labels):
    batch_id = validate_labels
    with SessionLocal() as db:
        validator = FeatureLabelValidator(db)
        report = validator.validate_alignment(batch_id)
        if not report['summary'].passed:
             raise ValueError(f"Feature Alignment Failed: {report['summary']}")
    return batch_id

@asset(name="build_training_matrix")
def build_training_matrix(context: AssetExecutionContext, validate_feature_label_alignment):
    batch_id = validate_feature_label_alignment
    builder = FeatureMatrixBuilder()
    return builder.build_and_split(batch_id=batch_id)

@asset(name="train_model_asset")
def train_model_asset(context: AssetExecutionContext, build_training_matrix):
    datasets = build_training_matrix
    svc = ModelTrainingService()
    model, metadata = svc.train_logistic_regression(
        datasets["X_train"], datasets["y_train"]
    )
    
    # Evaluate
    metrics = svc.evaluate_model(model, datasets["X_test"], datasets["y_test"])
    
    return {
        "model": model, 
        "metrics": metrics,
        "batch_id": datasets["metadata"].batch_id or "unknown",
        "feature_names": list(datasets["X_train"].columns)
    }

def _extract_ml_weights(model, feature_names):
    if not hasattr(model, 'coef_'): return {}
    coefs = model.coef_.flatten()
    max_abs = max(abs(coefs)) if len(coefs) > 0 else 1
    scale = 25 / max_abs if max_abs > 0 else 1
    
    weights = {}
    for name, c in zip(feature_names, coefs):
        w = int(round(c * scale))
        if w != 0: weights[name] = w
    return weights

@asset(name="refine_scorecard")
def refine_scorecard(context: AssetExecutionContext, train_model_asset):
    model = train_model_asset["model"]
    metrics = train_model_asset["metrics"]
    batch_id = train_model_asset["batch_id"]
    feature_names = train_model_asset["feature_names"]
    
    weights = _extract_ml_weights(model, feature_names)
    
    with SessionLocal() as db:
        svc = ScorecardVersionService(db)
        svc.ensure_initial_version()
        new_ver = svc.create_version_from_ml(
            weights=weights,
            ml_auc=metrics.get('roc_auc', 0),
            ml_f1=metrics.get('f1', 0),
            ml_model_id=batch_id,
            notes=f"Refined from batch {batch_id}"
        )
        
        status = new_ver.status if new_ver else "unchanged"
        context.log.info(f"Refinement result: {status}")
        
    return status

@asset(name="evaluate_model")
def evaluate_model(context: AssetExecutionContext, refine_scorecard):
    context.log.info(f"Pipeline Complete. Scorecard Status: {refine_scorecard}")
    return refine_scorecard

# ==============================================================================
# DEFINITIONS
# ==============================================================================

# Job: Score Only
score_batch_job = define_asset_job(
    name="score_batch_job",
    selection=[
        "ingest_synthetic_batch", "validate_ingestion",
        "kyc_features", "transaction_features", "network_features",
        "features_all", "validate_features", "score_batch"
    ]
)

# Job: Full Loop
unified_training_job = define_asset_job(
    name="unified_training_job",
    selection=AssetSelection.all()
)

defs = Definitions(
    assets=[
        ingest_synthetic_batch, validate_ingestion,
        kyc_features, transaction_features, network_features, features_all, validate_features,
        score_batch,
        generate_scorecard_labels, ingest_observed_labels,
        validate_labels, validate_feature_label_alignment,
        build_training_matrix, train_model_asset, refine_scorecard, evaluate_model
    ],
    jobs=[score_batch_job, unified_training_job]
)
