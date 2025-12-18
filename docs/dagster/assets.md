# Dagster Assets

Assets are the core building blocks of KYCC pipelines, representing data artifacts produced by computations.

## Asset Catalog

| Asset | Description | Dependencies |
|-------|-------------|--------------|
| ingest_synthetic_batch | Load synthetic profiles | None |
| extract_features | Extract all features | ingest_synthetic_batch |
| extract_kyc_features | Extract KYC features | ingest_synthetic_batch |
| extract_txn_features | Extract transaction features | ingest_synthetic_batch |
| extract_network_features | Extract network features | ingest_synthetic_batch |
| score_batch | Compute credit scores | extract_features |
| generate_scorecard_labels | Generate ML labels | score_batch |
| train_model_asset | Train ML model | generate_scorecard_labels |
| refine_scorecard | Refine scorecard weights | train_model_asset |

---

## Asset Definitions

### ingest_synthetic_batch

Loads synthetic profile data into the database.

```python
@asset(
    description="Ingest synthetic profiles from JSON file",
    group_name="data_ingestion"
)
def ingest_synthetic_batch(context) -> dict:
    """
    Load synthetic party profiles into the database.
    
    Config:
        batch_id: Unique identifier for this batch
        file_path: Path to synthetic_profiles.json
    
    Returns:
        dict with parties_created count
    """
    batch_id = context.op_config.get("batch_id", f"BATCH_{datetime.now():%Y%m%d}")
    file_path = context.op_config.get("file_path", "data/synthetic_profiles.json")
    
    db = context.resources.database
    
    with open(file_path) as f:
        profiles = json.load(f)
    
    parties_created = 0
    for profile in profiles:
        party = Party(
            party_name=profile["company_name"],
            party_type=profile["party_type"],
            kyc_verified=profile.get("kyc_verified", False),
            batch_id=batch_id,
            # ... other fields
        )
        db.add(party)
        parties_created += 1
    
    db.commit()
    
    context.log.info(f"Created {parties_created} parties in batch {batch_id}")
    
    return {
        "batch_id": batch_id,
        "parties_created": parties_created
    }
```

---

### extract_features

Extracts features from all sources for a batch.

```python
@asset(
    description="Extract features from all sources for batch parties",
    group_name="feature_extraction",
    deps=[ingest_synthetic_batch]
)
def extract_features(context, ingest_synthetic_batch: dict) -> dict:
    """
    Run feature extraction pipeline for all parties in batch.
    
    Returns:
        dict with features_extracted count
    """
    batch_id = ingest_synthetic_batch["batch_id"]
    db = context.resources.database
    
    pipeline = FeaturePipelineService(db)
    result = pipeline.run(batch_id)
    
    context.log.info(f"Extracted features for {result['processed_parties']} parties")
    
    return {
        "batch_id": batch_id,
        "features_extracted": result["processed_parties"] * 16  # ~16 features per party
    }
```

---

### extract_kyc_features

Extracts only KYC features.

```python
@asset(
    description="Extract KYC features only",
    group_name="feature_extraction",
    deps=[ingest_synthetic_batch]
)
def extract_kyc_features(context, ingest_synthetic_batch: dict) -> dict:
    """Extract KYC features for batch."""
    batch_id = ingest_synthetic_batch["batch_id"]
    db = context.resources.database
    
    pipeline = FeaturePipelineService(db)
    result = pipeline.run_single(batch_id, source="kyc")
    
    return {
        "batch_id": batch_id,
        "source": "KYC",
        "features_extracted": result["features_count"]
    }
```

---

### score_batch

Computes credit scores for all parties in a batch.

```python
@asset(
    description="Score all parties in batch",
    group_name="scoring",
    deps=[extract_features]
)
def score_batch(context, extract_features: dict) -> dict:
    """
    Compute credit scores for batch.
    
    Config:
        scorecard_version: Version of scorecard to use
    
    Returns:
        dict with scoring statistics
    """
    batch_id = extract_features["batch_id"]
    version = context.op_config.get("scorecard_version", "v1")
    
    db = context.resources.database
    scoring_service = ScoringService(db)
    
    result = scoring_service.score_batch(batch_id, scorecard_version=version)
    
    context.log.info(f"Scored {result['scored_count']} parties")
    
    # Calculate statistics
    scores = [r["total_score"] for r in result["results"] if r.get("total_score")]
    
    return {
        "batch_id": batch_id,
        "scored_count": result["scored_count"],
        "error_count": result["error_count"],
        "avg_score": statistics.mean(scores) if scores else 0,
        "score_distribution": _calculate_distribution(scores)
    }
```

---

### generate_scorecard_labels

Generates ground truth labels for ML training.

```python
@asset(
    description="Generate ground truth labels for ML training",
    group_name="ml_pipeline",
    deps=[score_batch]
)
def generate_scorecard_labels(context, score_batch: dict) -> dict:
    """
    Generate labels based on credit outcomes.
    
    Config:
        observation_window_days: Days to observe outcome
        default_rate: Target default rate for synthetic
    
    Returns:
        dict with label statistics
    """
    batch_id = score_batch["batch_id"]
    window = context.op_config.get("observation_window_days", 180)
    
    db = context.resources.database
    label_service = LabelGenerationService(db)
    
    # Check if real outcomes available, else generate synthetic
    real_labels = label_service.check_real_outcomes(batch_id)
    
    if real_labels:
        result = label_service.generate_labels(batch_id, observation_window_days=window)
    else:
        default_rate = context.op_config.get("default_rate", 0.15)
        result = label_service.generate_synthetic_labels(batch_id, default_rate)
    
    context.log.info(f"Generated {result['labels_created']} labels")
    
    return {
        "batch_id": batch_id,
        "labels_created": result["labels_created"],
        "default_rate": result["default_rate"],
        "label_type": "real" if real_labels else "synthetic"
    }
```

---

### train_model_asset

Trains ML model on labeled data.

```python
@asset(
    description="Train ML model on labeled data",
    group_name="ml_pipeline",
    deps=[generate_scorecard_labels]
)
def train_model_asset(context, generate_scorecard_labels: dict) -> dict:
    """
    Train logistic regression model.
    
    Config:
        test_size: Fraction for test set
        min_samples: Minimum required samples
    
    Returns:
        dict with model info and metrics
    """
    batch_id = generate_scorecard_labels["batch_id"]
    test_size = context.op_config.get("test_size", 0.2)
    min_samples = context.op_config.get("min_samples", 100)
    
    # Check sample count
    labels_count = generate_scorecard_labels["labels_created"]
    if labels_count < min_samples:
        context.log.warning(f"Insufficient samples: {labels_count} < {min_samples}")
        return {
            "batch_id": batch_id,
            "status": "skipped",
            "reason": f"Insufficient samples: {labels_count} < {min_samples}"
        }
    
    db = context.resources.database
    training_service = ModelTrainingService(db)
    
    result = training_service.train_model(batch_id, test_size=test_size)
    
    context.log.info(f"Model trained: AUC-ROC = {result['metrics']['auc_roc']:.3f}")
    
    return {
        "batch_id": batch_id,
        "model_id": result["model_id"],
        "metrics": result["metrics"],
        "feature_importance": result["feature_importance"],
        "status": "trained"
    }
```

---

### refine_scorecard

Refines scorecard weights from ML model.

```python
@asset(
    description="Refine scorecard weights from ML model",
    group_name="ml_pipeline",
    deps=[train_model_asset]
)
def refine_scorecard(context, train_model_asset: dict) -> dict:
    """
    Create refined scorecard version from ML model.
    
    Config:
        blend_factor: Weight for ML vs base (0-1)
        base_version: Base scorecard version
    
    Returns:
        dict with new version info
    """
    if train_model_asset.get("status") != "trained":
        return {
            "status": "skipped",
            "reason": train_model_asset.get("reason", "Model not trained")
        }
    
    model_id = train_model_asset["model_id"]
    blend_factor = context.op_config.get("blend_factor", 0.5)
    base_version = context.op_config.get("base_version", "v1")
    
    db = context.resources.database
    version_service = ScorecardVersionService(db)
    
    result = version_service.refine_from_model(
        model_id=model_id,
        base_version=base_version,
        blend_factor=blend_factor
    )
    
    context.log.info(f"Created scorecard version: {result['version_id']}")
    
    return {
        "version_id": result["version_id"],
        "model_id": model_id,
        "base_version": base_version,
        "blend_factor": blend_factor,
        "status": "draft"
    }
```

---

## Asset Groups

Assets are organized into groups:

| Group | Assets | Purpose |
|-------|--------|---------|
| data_ingestion | ingest_synthetic_batch | Load data |
| feature_extraction | extract_* | Extract features |
| scoring | score_batch | Compute scores |
| ml_pipeline | generate_labels, train_model, refine_scorecard | ML workflow |

---

## Asset Metadata

Assets emit metadata for tracking:

```python
@asset
def score_batch(context, extract_features):
    # ... scoring logic ...
    
    context.add_output_metadata({
        "batch_id": batch_id,
        "parties_scored": MetadataValue.int(scored_count),
        "avg_score": MetadataValue.float(avg_score),
        "band_distribution": MetadataValue.json(distribution)
    })
    
    return result
```

---

## Testing Assets

```python
def test_ingest_synthetic_batch():
    """Test synthetic data ingestion."""
    from dagster import build_op_context
    
    context = build_op_context(
        config={"batch_id": "TEST_001", "file_path": "test_data.json"},
        resources={"database": mock_database}
    )
    
    result = ingest_synthetic_batch(context)
    
    assert result["parties_created"] > 0
    assert result["batch_id"] == "TEST_001"
```
