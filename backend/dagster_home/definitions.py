"""Dagster definitions for KYCC data orchestration and ML pipeline."""

import sys
sys.path.insert(0, "/workspace")  # Ensure live-mounted code takes precedence

from dagster import (
	Definitions,
	job,
	op,
	OpExecutionContext,
	asset,
	AssetExecutionContext,
	StaticPartitionsDefinition,
	ScheduleDefinition,
	define_asset_job,
	SensorDefinition,
	RunRequest,
)

from app.services.feature_matrix_builder import FeatureMatrixBuilder
from dagster_home.sensors import iterative_learning_sensor
from app.services.model_training_service import ModelTrainingService
from app.services.feature_pipeline_service import FeaturePipelineService
from app.services.scoring_service import ScoringService
from app.services.model_registry_service import ModelRegistryService
from app.services.validation_service import TemporalValidationService
from app.models.models import Batch, GroundTruthLabel, Party
from app.validators.label_validator import LabelValidator
from app.validators.feature_label_validator import FeatureLabelValidator
from app.db.database import SessionLocal
import os
import json
import pathlib
from pathlib import Path
from datetime import datetime
from datetime import datetime
# from dagster_home.assets.training import train_ml_model # DELETED monoloth


# Resources
def db_session_resource():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


# Ingestion (Dynamic config based)
# Removed StaticPartitionsDefinition to support infinite iterative batches via config



# Data generation assets (file-based)
# Data generation assets (file-based) - REMOVED (Now handled dynamically via config path)



@asset(
    config_schema={"batch_id": str},
    name="ingest_synthetic_batch",
    description="Ingests customer profiles WITHOUT labels"
)
def ingest_synthetic_batch(context) -> str:
    """Ingest synthetic profiles into Party/Transaction/Relationship for the given batch_id."""
    print(f"DEBUG: Entering ingest_synthetic_batch asset for {context.op_config['batch_id']}")
    batch_id = context.op_config["batch_id"]
    path = os.path.join(os.getcwd(), "data", f"{batch_id}_profiles.json")
    
    if not os.path.exists(path):
        raise FileNotFoundError(f"Profiles file not found: {path}")

    # Verify NO labels present (Security/Correctness Check)
    with open(path, 'r') as f:
        data = json.load(f)
        # Check first 5 items to be safe, or scan all if datasets are small
        # Assuming data structure is payload dict
        parties = data.get("parties", []) if isinstance(data, dict) else data
        
        for p in parties[:10]: # Check sample
            if "will_default" in p:
                raise ValueError(f"ILLEGAL: Profiles file {path} contains labels!")
    
    # Lazy import to avoid circulars
    from app.services.synthetic_seed_service import ingest_seed_file
    with SessionLocal() as db:
        # Note: ingest_seed_file needs to be updated to handle the raw data if it expects specific format
        # or we assume the file format matches what ingest_seed_file expects
        ingest_seed_file(db, path, batch_id=batch_id)
        from app.models.models import Party
        count = db.query(Party).count()
        print(f"DEBUG: Post-ingest party count: {count}")
        if count == 0:
             raise Exception("DEBUG: Ingestion reported success but count is 0!")
        
    context.log.info(f"Ingested batch {batch_id} from {path}.")
    return batch_id


@asset(name="validate_ingestion")
def validate_ingestion(context: AssetExecutionContext, ingest_synthetic_batch):
	"""Validate ingestion: check row counts for Party/Transaction/Relationship."""
	batch_id = ingest_synthetic_batch # It's a string now
	from app.db import crud
	with SessionLocal() as db:
		party_count = crud.count_parties(db, batch_id=batch_id) if hasattr(crud, "count_parties") else None
		txn_count = crud.count_transactions(db, batch_id=batch_id) if hasattr(crud, "count_transactions") else None
		rel_count = crud.count_relationships(db, batch_id=batch_id) if hasattr(crud, "count_relationships") else None
	context.log.info(f"Batch {batch_id} counts -> parties={party_count}, txns={txn_count}, rels={rel_count}")
	return {"batch_id": batch_id, "party_count": party_count, "txn_count": txn_count, "rel_count": rel_count}


# Feature extraction orchestration
@asset(name="kyc_features")
def kyc_features(context: AssetExecutionContext, validate_ingestion):
	batch_id = validate_ingestion["batch_id"]
	with SessionLocal() as db:
		svc = FeaturePipelineService(db)
		res = svc.run_single(batch_id=batch_id, source="kyc") if hasattr(svc, "run_single") else svc.run(batch_id=batch_id)
	context.log.info(f"KYC features ready for {batch_id}")
	return {"batch_id": batch_id, "source": "kyc"}


@asset(name="transaction_features")
def transaction_features(context: AssetExecutionContext, validate_ingestion):
	batch_id = validate_ingestion["batch_id"]
	with SessionLocal() as db:
		svc = FeaturePipelineService(db)
		res = svc.run_single(batch_id=batch_id, source="transaction") if hasattr(svc, "run_single") else svc.run(batch_id=batch_id)
	context.log.info(f"Transaction features ready for {batch_id}")
	return {"batch_id": batch_id, "source": "transaction"}


@asset(name="network_features")
def network_features(context: AssetExecutionContext, validate_ingestion):
	batch_id = validate_ingestion["batch_id"]
	with SessionLocal() as db:
		svc = FeaturePipelineService(db)
		res = svc.run_single(batch_id=batch_id, source="network") if hasattr(svc, "run_single") else svc.run(batch_id=batch_id)
	context.log.info(f"Network features ready for {batch_id}")
	return {"batch_id": batch_id, "source": "network"}


@asset(name="features_all")
def features_all(context: AssetExecutionContext, kyc_features, transaction_features, network_features):
	"""Converge individual feature extractions; ensures all are present for batch."""
	batch_id = kyc_features["batch_id"]
	context.log.info(f"Features converged for {batch_id}")
	return {"batch_id": batch_id, "sources": ["kyc", "transaction", "network"]}


@asset(name="validate_features")
def validate_features(context: AssetExecutionContext, features_all):
	"""Validate features for a batch using FeatureValidationService."""
	batch_id = features_all["batch_id"]
	from app.services.feature_validation_service import FeatureValidationService
	with SessionLocal() as db:
		svc = FeatureValidationService(db)
		# Use existing batch validation method
		report = svc.generate_validation_report(batch_id=batch_id)
	
	context.log.info(f"Validation complete for {batch_id}: valid={report.get('valid_parties')}/{report.get('total_parties')}")
	
	if report.get('completion_rate', 0) < 80.0:
		context.log.warning(f"Low data quality: {report.get('completion_rate')}% valid")
		# We could raise an error here to stop the pipeline, but for now just warn
	
	return report


# Scoring
@asset(
    config_schema={"batch_id": str},
    name="score_batch",
    description="Scores a batch using the active scorecard version"
)
def score_batch(context: AssetExecutionContext, validate_features):
    """Compute credit scores for a batch using the active scorecard.
    
    The scorecard is ALWAYS used for scoring. ML refines the scorecard
    weights over time, but scoring always goes through ScorecardEngine.
    
    Args:
        context: Dagster execution context
        validate_features: Upstream dependency (ensures features are validated)
        
    Returns:
        Dict with batch_id, scorecard_version, and scoring summary
    """
    batch_id = context.op_config["batch_id"]
    
    from app.scorecard import ScorecardEngine, get_version_service
    from app.models.models import Party, Feature, ScoreRequest
    
    with SessionLocal() as db:
        try:
            # 1. Get active scorecard version from DB (or fallback)
            version_service = get_version_service(db)
            scorecard_config = version_service.get_active_scorecard()
            
            # Initialize engine with the loaded config
            engine = ScorecardEngine(config=scorecard_config)
            scorecard_version = scorecard_config.get('version', '1.0')
            
            context.log.info(f"Scoring batch {batch_id} with scorecard v{scorecard_version}")
            
            # 2. Get all parties in batch
            parties = db.query(Party).filter(Party.batch_id == batch_id).all()
            if not parties:
                raise ValueError(f"No parties found for batch {batch_id}")
            
            # 3. Score each party
            scored_count = 0
            failed_count = 0
            scores = []
            
            for party in parties:
                try:
                    # Get features for party
                    features = db.query(Feature).filter(
                        Feature.party_id == party.id,
                        Feature.valid_to == None
                    ).all()
                    
                    feature_dict = {f.feature_name: f.feature_value for f in features}
                    
                    # Compute score using scorecard
                    result = engine.compute_scorecard_score(feature_dict)
                    score = result['score']
                    
                    # Store score request for audit
                    score_request = ScoreRequest(
                        id=f"req_{party.id}_{batch_id}_{datetime.utcnow().timestamp()}", # Generate ID
                        party_id=party.id,
                        # batch_id removed - linked via party
                        model_version=f"scorecard_v{scorecard_version}",
                        model_type="scorecard",
                        scorecard_version_id=scorecard_config.get('id'),
                        raw_score=float(result['raw_score']),
                        final_score=score,
                        score_band=_score_to_risk_bucket(score),
                        features_snapshot=feature_dict,
                        request_timestamp=datetime.utcnow(),
                    )
                    db.add(score_request)
                    scores.append(score)
                    scored_count += 1
                    
                except Exception as e:
                    import traceback
                    context.log.warning(f"Failed to score party {party.id}: {e}\n{traceback.format_exc()}")
                    failed_count += 1
            
            db.commit()
            
            avg_score = sum(scores) / len(scores) if scores else 0
            context.log.info(
                f"Scored {scored_count} parties (avg score: {avg_score:.0f}), "
                f"{failed_count} failures"
            )
            
            return {
                "batch_id": batch_id,
                "scorecard_version": scorecard_version,
                "summary": {
                    "scored": scored_count,
                    "failed": failed_count,
                    "avg_score": avg_score
                }
            }
            
        except Exception as e:
            context.log.error(f"Scoring failed for batch {batch_id}: {e}")
            db.rollback()
            raise


def _score_to_risk_bucket(score: float) -> str:
    """Convert numeric score to risk bucket.
    
    Args:
        score: Credit score (300-900 range)
        
    Returns:
        Risk bucket: 'high', 'medium', or 'low'
    """
    if score < 500:
        return 'high'
    elif score < 700:
        return 'medium'
    else:
        return 'low'


@op(config_schema={"batch_id": str})
def build_matrix_op(context: OpExecutionContext):
	"""Build feature matrix and split train/test for a batch."""
	batch_id = context.op_config["batch_id"]
	builder = FeatureMatrixBuilder()
	X, y, metadata = builder.build_matrix(batch_id)
	X_train, X_test, y_train, y_test = builder.split_train_test(X, y, test_size=0.2, random_state=42)

	context.log.info(
		f"Built matrix for batch {batch_id}: train={len(X_train)}, test={len(X_test)}, labels={metadata.label_distribution}"
	)

	return {
		"X_train": X_train,
		"X_test": X_test,
		"y_train": y_train,
		"y_test": y_test,
		"metadata": metadata,
	}


@op
def train_and_evaluate_op(context: OpExecutionContext, datasets: dict):
	"""Train logistic regression and evaluate on test split."""
	svc = ModelTrainingService()
	model, train_metadata = svc.train_logistic_regression(
		datasets["X_train"], datasets["y_train"], hyperparams={"max_iter": 200}
	)
	metrics = svc.evaluate_model(model, datasets["X_test"], datasets["y_test"])

	context.log.info(f"Eval metrics: roc_auc={metrics.get('roc_auc'):.4f}, f1={metrics.get('f1'):.4f}")

	return {
		"model": model,
		"metrics": metrics,
		"train_metadata": train_metadata,
		"dataset_metadata": datasets.get("metadata"),
	}


@job
def training_pipeline():
	"""End-to-end training: build matrix -> train -> evaluate."""
	datasets = build_matrix_op()
	train_and_evaluate_op(datasets)


# Sensors
def synthetic_file_sensor(context):
	path = Path(os.getcwd()) / "data" / "synthetic_profiles.json"
	if not path.exists():
		context.update_cursor("missing")
		return
	run_key = f"synthetic-{int(path.stat().st_mtime)}"
	context.update_cursor(run_key)
	yield RunRequest(run_key=run_key, job_name="full_pipeline_job", partition_key="BATCH_001")


def labeled_file_sensor(context):
	path = Path(os.getcwd()) / "data" / "labeled_profiles.json"
	if not path.exists():
		context.update_cursor("missing")
		return
	run_key = f"labeled-{int(path.stat().st_mtime)}"
	context.update_cursor(run_key)
	yield RunRequest(run_key=run_key, job_name="full_pipeline_job")


@asset(
    config_schema={"batch_id": str},
    name="generate_scorecard_labels",
    description="Generates ground truth labels using expert scorecard rules"
)
def generate_scorecard_labels(context) -> str:
    """Generate labels by thresholding scorecard scores.
    
    Uses the expert-defined scorecard to:
    1. Compute credit scores for all parties in batch
    2. Threshold bottom 5% as defaults (will_default=1)
    3. Store labels in GroundTruthLabel table
    """
    batch_id = context.op_config["batch_id"]
    
    from app.services.label_generation_service import LabelGenerationService
    from app.models.models import Party, Feature
    
    with SessionLocal() as db:
        # Get all parties in batch
        parties = db.query(Party).filter(Party.batch_id == batch_id).all()
        if not parties:
            raise ValueError(f"No parties found for batch {batch_id}")
        
        # Build feature dictionaries for each party
        features_list = []
        party_ids = []
        
        for party in parties:
            # Get features from feature store
            features = db.query(Feature).filter(
                Feature.party_id == party.id,
                Feature.valid_to == None  # Current features only
            ).all()
            
            feature_dict = {f.feature_name: f.feature_value for f in features}
            features_list.append(feature_dict)
            party_ids.append(party.id)
        
        # Generate labels using scorecard
        label_svc = LabelGenerationService(db, scorecard_version='1.0')
        result = label_svc.generate_labels_from_scorecard(
            features_list=features_list,
            party_ids=party_ids,
            target_default_rate=0.05,  # Bottom 5% = defaults
            batch_id=batch_id,
        )
        
        context.log.info(
            f"Generated {result['labels_created']} labels for batch {batch_id}. "
            f"Defaults: {result['defaults_count']} ({result['actual_default_rate']*100:.1f}%)"
        )
        
    return batch_id


@asset(
    config_schema={"batch_id": str},
    name="ingest_observed_labels",
    description="Loads observed outcome labels for training"
)
def ingest_observed_labels(context) -> str:
    """Verifies that observed labels exist in DB for the given batch.
    
    This is the entry point for the 'Observed' training pipeline.
    It expects that 'generate_outcome_labels.py' (or API) has already
    populated the ground_truth_labels table.
    """
    batch_id = context.op_config["batch_id"]
    
    with SessionLocal() as db:
        # Check if labels (observed) exist for this batch
        count = db.query(GroundTruthLabel).join(Party).filter(
            Party.batch_id == batch_id,
            GroundTruthLabel.label_source == 'observed'
        ).count()
        
        if count == 0:
            # Check if maybe they are in a file (User requested generic ingest)
            # Assuming file path convention data/{batch_id}_labels.json
            path = os.path.join(os.getcwd(), "data", f"{batch_id}_labels.json")
            if os.path.exists(path):
                context.log.info(f"Loading labels from file {path}")
                with open(path, 'r') as f:
                    labels_data = json.load(f)
                    for l in labels_data:
                        # Assuming structure matches
                        db.add(GroundTruthLabel(
                            party_id=l['party_id'],
                            will_default=l['default_outcome'],
                            label_source='observed',
                            created_at=datetime.utcnow() 
                        ))
                    db.commit()
                    count = len(labels_data)
            else:
                 raise ValueError(f"No observed labels found for batch {batch_id} (DB or File)")
        
        context.log.info(f"Found {count} observed labels for batch {batch_id}")

    return batch_id





# ==========================================
# Unified Training Pipeline
# ==========================================

# 1. Validation Asset (Merge Point Logic)
@asset(
    name="validate_labels",
    # We use deps to force ordering if they are in the same run, 
    # but we don't strictly require data passing via inputs to handle the "OR" case.
    deps=["generate_scorecard_labels", "ingest_observed_labels"], 
    config_schema={"batch_id": str},
    description="Validates detected labels (Merge Point)"
)
def validate_labels_asset(context):
    """
    Unified validation asset.
    Detects if the batch is Synthetic or Observed based on available data/config,
    and runs the appropriate validation logic.
    """
    batch_id = context.op_config["batch_id"]
    from app.models.models import Party, GroundTruthLabel
    import pandas as pd
    from app.validators.label_validator import LabelValidator
    
    with SessionLocal() as db:
        # Determine Source from DB labels
        # We query one label to check 'label_source'
        sample_label = db.query(GroundTruthLabel).join(Party).filter(
            Party.batch_id == batch_id
        ).first()
        
        if not sample_label:
            # Maybe the upstream failed? Or user gave wrong batch_id?
            # Or wait.. context.op_config["batch_id"] matching is required.
            raise ValueError(f"No labels found for batch {batch_id}. Upstream may have failed.")
            
        source = sample_label.label_source # 'scorecard' (synthetic) or 'observed'
        
        # Validation Logic (Conceptual separation per user request)
        if source == 'scorecard':
             # Synthetic logic: Might be stricter about distribution? Default 5%?
             context.log.info(f"Detected SYNTHETIC batch {batch_id}. Running synthetic validation rules.")
             # Add specific synthetic checks here if needed
        else:
             # Observed logic: Real world data.
             context.log.info(f"Detected OBSERVED batch {batch_id}. Running observed validation rules.")
             
        # Common Validation Part
        labels = db.query(GroundTruthLabel).join(Party).filter(Party.batch_id == batch_id).all()
        labels_df = pd.DataFrame([{'party_id': l.party_id, 'will_default': l.will_default} for l in labels])
        
        validator = LabelValidator(db)
        report = validator.validate_batch(labels_df)
        
        if not report['summary'].passed:
             raise ValueError(f"Validation Failed for {source} batch")
             
        context.log.info(f"Validation Passed: {len(labels)} labels")
        
    return batch_id

# 2. Alignment Asset (Linear chain continues)
@asset(
    name="validate_feature_label_alignment",
    description="Validates feature-label alignment before training"
)
def validate_feature_label_alignment_asset(context, validate_labels):
    """Ensure features and labels are aligned for training."""
    batch_id = validate_labels # Passed from detected validation
    
    from app.validators.feature_label_validator import FeatureLabelValidator
    with SessionLocal() as db:
        validator = FeatureLabelValidator(db)
        report = validator.validate_alignment(batch_id)
        if not report['summary'].passed:
             raise ValueError("Feature alignment failed")
        context.log.info(f"Alignment passed for {batch_id}")
    return batch_id

# 3. Build Matrix
@asset(name="build_training_matrix")
def build_training_matrix(context, validate_feature_label_alignment):
    batch_id = validate_feature_label_alignment
    context.log.info(f"Building matrix for {batch_id}")
    builder = FeatureMatrixBuilder()
    return builder.build_and_split(batch_id=batch_id)

# 4. Train Model
@asset(name="train_model_asset")
def train_model_asset(context, build_training_matrix):
    svc = ModelTrainingService()
    model, metadata = svc.train_logistic_regression(
        build_training_matrix["X_train"], 
        build_training_matrix["y_train"], 
        hyperparams={"max_iter": 200}
    )
    return {
        "model": model,
        "metrics": svc.evaluate_model(model, build_training_matrix["X_test"], build_training_matrix["y_test"]), 
        "train_metadata": metadata,
        "batch_id": build_training_matrix["metadata"].batch_id,
        "feature_names": list(build_training_matrix["X_train"].columns),
        "X_test": build_training_matrix["X_test"],
        "y_test": build_training_matrix["y_test"]
    }

# 5. Evaluate Model (Independent Asset)
@asset(name="evaluate_model_asset")
def evaluate_model_asset(context, train_model_asset):
    model = train_model_asset["model"]
    metrics = ModelTrainingService().evaluate_model(
        model, train_model_asset["X_test"], train_model_asset["y_test"]
    )
    context.log.info(f"Evaluation: AUC={metrics.get('roc_auc'):.4f}")
    return {**train_model_asset, "evaluation_metrics": metrics}

# 6. Refine Scorecard
@asset(name="refine_scorecard")
def refine_scorecard(context, evaluate_model_asset):
    model = evaluate_model_asset["model"]
    metrics = evaluate_model_asset["evaluation_metrics"]
    batch_id = evaluate_model_asset["batch_id"]
    feature_names = evaluate_model_asset["feature_names"]
    
    ml_auc = metrics.get('roc_auc', 0)
    ml_f1 = metrics.get('f1', 0)
    
    from app.services.scorecard_version_service import ScorecardVersionService
    
    with SessionLocal() as db:
        svc = ScorecardVersionService(db)
        svc.ensure_initial_version()
        ml_weights = _extract_ml_weights(model, feature_names)
        
        new_version = svc.create_version_from_ml(
            weights=ml_weights,
            ml_auc=ml_auc,
            ml_f1=ml_f1,
            ml_model_id=batch_id,
            notes=f"Trained on batch {batch_id}"
        )
        if new_version:
             context.log.info(f"Scorecard Status: {new_version.status}, v{new_version.version}")
             return new_version.version
        return "unchanged"

# 7. Logging Wrapper
@asset(name="evaluate_model")
def evaluate_model(context, refine_scorecard):
    # Dummy wrapper for logging end state
    context.log.info(f"Final pipeline state: {refine_scorecard}")
    return refine_scorecard

# -----------------
# Define ONE Unified Job
# -----------------
unified_training_job = define_asset_job(
    name="unified_training_job",
    selection=[
        "generate_scorecard_labels", # Potential entry
        "ingest_observed_labels",    # Potential entry
        "validate_labels",           # Merge Point
        "validate_feature_label_alignment",
        "build_training_matrix",
        "train_model_asset",
        "evaluate_model_asset",
        "refine_scorecard",
        "evaluate_model"
    ]
)

def _extract_ml_weights(model, feature_names: list) -> dict:
    """Extract feature weights from ML model coefficients.
    
    Converts logistic regression coefficients to scorecard-style
    integer weights (scaled to typical scorecard range).
    
    Args:
        model: Trained sklearn model
        feature_names: List of feature names
        
    Returns:
        Dict of feature_name -> weight (integer)
    """
    import numpy as np
    
    if not hasattr(model, 'coef_'):
        return {}
    
    coefficients = model.coef_.flatten()
    
    # Scale coefficients to scorecard range (roughly -50 to +50)
    # This preserves relative importance while making weights interpretable
    max_abs_coef = max(abs(coefficients)) if len(coefficients) > 0 else 1
    scale_factor = 25 / max_abs_coef if max_abs_coef > 0 else 1
    
    weights = {}
    for name, coef in zip(feature_names, coefficients):
        # Convert to integer weight, flip sign for credit scoring convention
        # (positive coefficient = lower risk = higher score)
        weight = int(round(coef * scale_factor))
        if weight != 0:  # Only include non-zero weights
            weights[name] = weight
    
    return weights


@asset(name="evaluate_model")
def evaluate_model(context: AssetExecutionContext, refine_scorecard):
    """Log final scorecard status after refinement attempt."""
    status = refine_scorecard.get("status", "unknown")
    
    if status == "activated":
        context.log.info(
            f"Scorecard updated to v{refine_scorecard.get('version')} "
            f"with AUC {refine_scorecard.get('ml_auc', 0):.4f}"
        )
    elif status == "failed":
        context.log.warning(
            f"Model failed quality gates: {refine_scorecard.get('reason')}"
        )
    else:
        context.log.info("Scorecard unchanged - current version still active")
    
    return refine_scorecard



# Unified Job
score_batch_job = define_asset_job(
    name="score_batch_job",
    selection=[
        "ingest_synthetic_batch",
        "validate_ingestion",
        "kyc_features", "transaction_features", "network_features",
        "features_all",
        "validate_features",
        "score_batch"
    ]
)

# Legacy training pipeline (for backwards compatibility)
training_pipeline = define_asset_job(
    name="training_pipeline",
    selection=[
        "generate_scorecard_labels",
        "validate_labels",
        "validate_feature_label_alignment",
        "build_training_matrix",
        "train_model_asset",
        "evaluate_model_asset",
        "refine_scorecard",
        "evaluate_model"
    ]
)

# Unified training job (accepts either synthetic or observed entry point)
unified_training_job = define_asset_job(
    name="unified_training_job",
    selection=[
        "generate_scorecard_labels",
        "ingest_observed_labels",
        "validate_labels",
        "validate_feature_label_alignment",
        "build_training_matrix",
        "train_model_asset",
        "evaluate_model_asset",
        "refine_scorecard",
        "evaluate_model"
    ]
)


defs = Definitions(
	assets=[
        # Data & Features
		ingest_synthetic_batch,
		validate_ingestion,
		kyc_features,
		transaction_features,
		network_features,
		features_all,
		validate_features,
        score_batch,

        # Training Pipeline (Consolidated)
        # 1. Entry Points
		generate_scorecard_labels,
        ingest_observed_labels,

        # 2. Unified Chain
        validate_labels_asset,
        validate_feature_label_alignment_asset,
        build_training_matrix,
        train_model_asset,
        evaluate_model_asset,
        refine_scorecard,
        evaluate_model
	],
	jobs=[
        training_pipeline, 
        score_batch_job, 
        unified_training_job
    ],
	schedules=[],
	sensors=[
        iterative_learning_sensor
	],
)
