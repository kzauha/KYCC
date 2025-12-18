# Service Layer Architecture

The service layer contains the core business logic of KYCC. Services orchestrate operations between the API layer and data access layer.

## Service Overview

| Service | File | Responsibility |
|---------|------|----------------|
| ScoringService | `scoring_service.py` | Score computation and model application |
| FeaturePipelineService | `feature_pipeline_service.py` | Feature extraction orchestration |
| ModelTrainingService | `model_training_service.py` | ML model training |
| LabelGenerationService | `label_generation_service.py` | Ground truth label creation |
| ScorecardVersionService | `scorecard_version_service.py` | Scorecard version management |
| AnalyticsService | `analytics_service.py` | Analytics and reporting |
| NetworkService | `network_service.py` | Network graph operations |
| FeatureValidationService | `feature_validation_service.py` | Feature quality validation |
| FeatureMatrixBuilder | `feature_matrix_builder.py` | Training data preparation |
| SyntheticSeedService | `synthetic_seed_service.py` | Synthetic data ingestion |

---

## ScoringService

The main orchestrator for credit score computation.

### Location
`backend/app/services/scoring_service.py`

### Responsibilities
- Coordinate feature extraction
- Fetch active scoring model
- Compute credit scores
- Apply decision rules
- Generate audit logs

### Key Methods

```python
class ScoringService:
    def compute_score(
        self, 
        party_id: int, 
        model_version: str = None,
        include_explanation: bool = True
    ) -> dict:
        """
        Compute credit score for a party.
        
        Steps:
        1. Ensure features exist
        2. Get active model
        3. Fetch features
        4. Apply feature scaling
        5. Compute score (scorecard or ML)
        6. Normalize to 300-900
        7. Assign score band
        8. Apply decision rules
        9. Generate explanation
        10. Log score request
        """
```

### Score Computation Flow

```
compute_score(party_id)
    │
    ├── _ensure_features_exist(party_id)
    │       └── FeaturePipelineService.extract_all_features()
    │
    ├── Get active model from ModelRegistry or ScorecardVersion
    │
    ├── _get_current_features(party_id, required_features)
    │
    ├── Apply scaler if ML model
    │
    ├── _compute_scorecard() or _compute_ml_model()
    │
    ├── _normalize_score() → 300-900 range
    │
    ├── _get_score_band() → excellent/good/fair/poor
    │
    ├── _compute_confidence()
    │
    ├── _apply_decision_rules()
    │
    ├── _generate_explanation()
    │
    └── Save ScoreRequest (audit log)
```

---

## FeaturePipelineService

Orchestrates feature extraction from multiple sources.

### Location
`backend/app/services/feature_pipeline_service.py`

### Responsibilities
- Coordinate all feature extractors
- Store extracted features
- Handle temporal versioning

### Key Methods

```python
class FeaturePipelineService:
    def __init__(self, db: Session):
        self.extractors = [
            KYCFeatureExtractor(),
            TransactionFeatureExtractor(),
            NetworkFeatureExtractor()
        ]
    
    def extract_all_features(self, party_id: int, as_of_date: datetime = None) -> dict:
        """Extract features from all sources for a party."""
    
    def extract_features(self, party_id: int, source_types: List[str] = None) -> dict:
        """Extract features, optionally filtering by source type."""
    
    def run(self, batch_id: str) -> dict:
        """Run feature extraction for all parties in a batch."""
    
    def run_single(self, batch_id: str, source: str) -> dict:
        """Run extraction for a specific source."""
```

### Source Type Mapping

| External Name | Internal Type | Extractor |
|---------------|---------------|-----------|
| `kyc` | `KYC` | KYCFeatureExtractor |
| `transaction` | `TRANSACTIONS` | TransactionFeatureExtractor |
| `network` | `RELATIONSHIPS` | NetworkFeatureExtractor |

---

## ModelTrainingService

Handles ML model training on labeled data.

### Location
`backend/app/services/model_training_service.py`

### Responsibilities
- Train logistic regression models
- Evaluate model performance
- Save models to registry
- Persist scalers

### Key Methods

```python
class ModelTrainingService:
    def train_logistic_regression(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        hyperparams: Dict = None
    ) -> Tuple[LogisticRegression, Dict]:
        """Train logistic regression with balanced class weights."""
    
    def evaluate_model(
        self,
        model: LogisticRegression,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict:
        """Evaluate model with AUC, F1, precision, recall."""
    
    def save_to_registry(
        self,
        model: LogisticRegression,
        metrics: Dict,
        model_version: str,
        scaler: Any = None
    ) -> Dict:
        """Save model and metrics to ModelRegistry."""
```

### Default Hyperparameters

```python
{
    'C': 1.0,
    'penalty': 'l2',
    'max_iter': 1000,
    'solver': 'lbfgs',
    'class_weight': 'balanced'
}
```

---

## LabelGenerationService

Generates ground truth labels from scorecard scores.

### Location
`backend/app/services/label_generation_service.py`

### Responsibilities
- Compute scorecard scores for all parties
- Determine default threshold
- Create binary labels

### Key Methods

```python
class LabelGenerationService:
    def generate_labels_from_scorecard(
        self,
        features_list: List[Dict],
        party_ids: List[int],
        target_default_rate: float = 0.05,
        batch_id: str = None
    ) -> Dict:
        """
        Generate labels by thresholding scorecard scores.
        Bottom X% are labeled as defaults.
        """
    
    def determine_default_threshold(
        self,
        scores: List[float],
        target_default_rate: float = 0.05
    ) -> float:
        """Calculate score threshold for target default rate."""
```

### Label Generation Logic

1. Compute scorecard scores for all parties
2. Find the score at the target percentile (e.g., 5th percentile)
3. Parties below threshold: `will_default = 1`
4. Parties at or above threshold: `will_default = 0`

---

## ScorecardVersionService

Manages versioned scorecards in the database.

### Location
`backend/app/services/scorecard_version_service.py`

### Responsibilities
- Get active scorecard version
- Create new versions from ML refinement
- Enforce quality gates
- Retire old versions

### Key Methods

```python
class ScorecardVersionService:
    def get_active_scorecard(self) -> Dict:
        """Get currently active scorecard configuration."""
    
    def create_version_from_ml(
        self,
        weights: Dict[str, float],
        ml_auc: float,
        ml_f1: float,
        ml_model_id: str = None,
        notes: str = None
    ) -> Optional[ScorecardVersion]:
        """Create new version if it passes quality gates."""
    
    def ensure_initial_version(self):
        """Ensure initial expert scorecard exists."""
```

### Quality Gates

```python
MIN_AUC_THRESHOLD = 0.55       # Minimum AUC to accept
IMPROVEMENT_THRESHOLD = 0.005  # Must improve by 0.5%
```

If a model fails quality gates, it is saved with `status='failed'` for inspection.

---

## AnalyticsService

Provides analytics and reporting capabilities.

### Location
`backend/app/services/analytics_service.py`

### Key Methods

```python
class AnalyticsService:
    def get_scorecard_versions(self) -> List[Dict]:
        """Get all scorecard versions with metadata."""
    
    def get_weights_evolution(self, top_n: int = 5) -> Dict:
        """Get weight evolution for top features."""
    
    def get_score_impact(self, version_id: int, compare_to: int = None) -> Dict:
        """Compare score distributions between versions."""
```

---

## Service Dependencies

```
ScoringService
    ├── FeaturePipelineService
    │       ├── KYCFeatureExtractor
    │       ├── TransactionFeatureExtractor
    │       └── NetworkFeatureExtractor
    ├── ScorecardEngine
    └── RuleEvaluator

ModelTrainingService
    └── FeatureMatrixBuilder

LabelGenerationService
    └── ScorecardEngine

ScorecardVersionService
    └── (independent)

AnalyticsService
    └── (independent)
```

---

## Error Handling

Services follow consistent error handling:

```python
try:
    # Service operation
except ValueError as e:
    # Invalid input
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    # Log error
    logger.error(f"Service error: {e}")
    raise
```

All services receive database sessions through dependency injection rather than creating their own sessions.
