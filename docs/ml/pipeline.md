# ML Pipeline Overview

The machine learning pipeline refines scorecard weights based on actual credit outcomes.

## Philosophy

**"The Scorecard is King, AI is the Advisor"**

- The rule-based scorecard remains the primary decision engine
- ML provides data-driven weight optimization
- Human review required before deploying ML changes
- Full auditability maintained at all times

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ML Pipeline Flow                             │
│                                                                     │
│   1. Ground Truth Collection                                        │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Credit outcomes (default/non-default) collected            │  │
│   │  Minimum 100+ labeled samples required                      │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   2. Feature Assembly                                               │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Features extracted at outcome date                         │  │
│   │  Training dataset: (features, outcome)                      │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   3. Model Training                                                 │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Logistic Regression trained on labeled data                │  │
│   │  Model coefficients extracted                               │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   4. Quality Gate                                                   │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  AUC-ROC > 0.60 required                                    │  │
│   │  Model must improve over baseline                           │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   5. Scorecard Refinement                                           │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Model coefficients converted to scorecard weights          │  │
│   │  New scorecard version created (not auto-deployed)          │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   6. Human Review                                                   │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Compare old vs new weights                                 │  │
│   │  Activate new version after approval                        │  │
│   └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### Services

| Service | Location | Purpose |
|---------|----------|---------|
| LabelGenerationService | `services/label_generation_service.py` | Generate ground truth labels |
| ModelTrainingService | `services/model_training_service.py` | Train ML models |
| ScorecardVersionService | `services/scorecard_version_service.py` | Manage scorecard versions |

### Models (Database)

| Table | Purpose |
|-------|---------|
| GroundTruthLabel | Stores credit outcomes |
| ModelRegistry | Tracks trained models |
| ScorecardVersion | Stores scorecard configurations |

### Dagster Assets

| Asset | Purpose |
|-------|---------|
| generate_scorecard_labels | Generate labels for training |
| train_model_asset | Train and evaluate model |
| refine_scorecard | Create new scorecard version |

---

## Workflow

### Step 1: Label Generation

Ground truth labels are generated from credit outcomes:

```python
from app.services.label_generation_service import LabelGenerationService

label_service = LabelGenerationService(db)

# Generate labels for a batch
result = label_service.generate_labels(
    batch_id="BATCH_001",
    outcome_type="default",
    observation_window_days=180
)
```

### Step 2: Model Training

Train logistic regression on labeled data:

```python
from app.services.model_training_service import ModelTrainingService

training_service = ModelTrainingService(db)

result = training_service.train_model(
    batch_id="BATCH_001",
    model_type="logistic_regression"
)

# Result includes:
# - model_id
# - metrics (auc_roc, accuracy, etc.)
# - feature_importance
```

### Step 3: Quality Gate

Model must pass quality threshold:

```python
if result['metrics']['auc_roc'] < 0.60:
    raise QualityGateError("AUC-ROC below minimum threshold")
```

### Step 4: Scorecard Refinement

Convert model to scorecard weights:

```python
from app.services.scorecard_version_service import ScorecardVersionService

version_service = ScorecardVersionService(db)

new_version = version_service.refine_from_model(
    model_id=result['model_id'],
    base_version="v1"
)

# Creates new version with status='draft'
```

### Step 5: Human Review and Activation

```python
# Review weight changes
comparison = version_service.compare_versions("v1", "ml_v2")

# After approval, activate
version_service.activate_version("ml_v2")
```

---

## Quality Gates

### Model Quality

| Metric | Threshold | Description |
|--------|-----------|-------------|
| AUC-ROC | >= 0.60 | Minimum discrimination ability |
| Sample Size | >= 100 | Minimum labeled samples |
| Default Rate | 5-50% | Ensure balanced dataset |

### Scorecard Quality

| Check | Threshold | Description |
|-------|-----------|-------------|
| Weight Change | < 50% | No drastic weight changes |
| Score Correlation | > 0.8 | New scores correlate with old |
| Band Stability | < 10% | Band distribution change |

---

## Dagster Integration

The ML pipeline runs as Dagster assets:

```python
@asset
def generate_scorecard_labels(
    context: OpExecutionContext,
    score_batch: dict
) -> dict:
    """Generate labels for ML training."""
    # ...

@asset
def train_model_asset(
    context: OpExecutionContext,
    generate_scorecard_labels: dict
) -> dict:
    """Train ML model on labeled data."""
    # ...

@asset
def refine_scorecard(
    context: OpExecutionContext,
    train_model_asset: dict
) -> dict:
    """Refine scorecard from ML model."""
    # ...
```

---

## API Endpoints

### Trigger ML Pipeline

```
POST /api/pipeline/trigger/ml_training_pipeline
```

```json
{
  "batch_id": "BATCH_001"
}
```

### Get Model Status

```
GET /api/pipeline/models/{model_id}
```

### List Scorecard Versions

```
GET /api/scoring/versions
```

### Activate Scorecard Version

```
POST /api/scoring/versions/{version}/activate
```

---

## Monitoring

### Model Performance Tracking

```python
# Get model performance over time
metrics = db.query(ModelRegistry).filter(
    ModelRegistry.model_type == 'logistic_regression'
).order_by(ModelRegistry.created_at.desc()).all()

for model in metrics:
    print(f"Model {model.id}: AUC={model.metrics['auc_roc']:.3f}")
```

### Version Comparison

```python
# Compare scorecard versions
old = version_service.get_version("v1")
new = version_service.get_version("ml_v2")

for feature in old['features']:
    old_weight = old['features'][feature]['weight']
    new_weight = new['features'][feature]['weight']
    change = ((new_weight - old_weight) / old_weight) * 100
    print(f"{feature}: {old_weight} -> {new_weight} ({change:+.1f}%)")
```

---

## Best Practices

1. **Minimum Sample Size**: Wait for 100+ labeled outcomes before training
2. **Regular Retraining**: Retrain monthly or when performance degrades
3. **Version Control**: Never overwrite active scorecard directly
4. **Human Review**: Always review ML recommendations before deployment
5. **Rollback Plan**: Keep previous version ready for quick rollback
6. **Monitoring**: Track score distribution changes after new version
