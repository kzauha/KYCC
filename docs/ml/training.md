# Model Training

The model training service trains machine learning models on labeled credit data.

## Overview

| Property | Value |
|----------|-------|
| Location | `backend/app/services/model_training_service.py` |
| Algorithm | Logistic Regression |
| Library | scikit-learn |
| Serialization | joblib |

---

## Model Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Model Training Pipeline                          │
│                                                                     │
│   Input: Labeled Data                                               │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Features (X)          Labels (y)                           │  │
│   │  ┌─────────────────┐   ┌─────────┐                         │  │
│   │  │ kyc_verified    │   │ 0       │                         │  │
│   │  │ company_age     │   │ 1       │                         │  │
│   │  │ txn_count       │   │ 0       │                         │  │
│   │  │ ...             │   │ ...     │                         │  │
│   │  └─────────────────┘   └─────────┘                         │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   Preprocessing                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  - Handle missing values (fill with 0)                      │  │
│   │  - Standardize features (StandardScaler)                    │  │
│   │  - Train/test split (80/20)                                 │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   Training                                                          │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  LogisticRegression(                                        │  │
│   │    penalty='l2',                                            │  │
│   │    C=1.0,                                                   │  │
│   │    max_iter=1000                                            │  │
│   │  )                                                          │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   Evaluation                                                        │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  - AUC-ROC                                                  │  │
│   │  - Accuracy                                                 │  │
│   │  - Precision/Recall                                         │  │
│   │  - Feature importance (coefficients)                        │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   Output: Model + Metrics                                           │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  - Serialized model (joblib)                                │  │
│   │  - Performance metrics                                      │  │
│   │  - Feature coefficients                                     │  │
│   └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ModelTrainingService

### Implementation

```python
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, classification_report
import joblib
import numpy as np

class ModelTrainingService:
    """Train ML models for credit scoring."""
    
    def __init__(self, db: Session):
        self.db = db
        self.feature_columns = [
            'kyc_verified',
            'company_age_years',
            'party_type_score',
            'contact_completeness',
            'has_tax_id',
            'transaction_count_6m',
            'avg_transaction_amount',
            'total_transaction_volume_6m',
            'transaction_regularity_score',
            'recent_activity_flag',
            'direct_counterparty_count',
            'network_depth_downstream',
            'network_size',
            'supplier_count',
            'customer_count',
            'network_balance_ratio'
        ]
    
    def train_model(
        self,
        batch_id: str,
        model_type: str = "logistic_regression",
        test_size: float = 0.2
    ) -> dict:
        """
        Train model on labeled data.
        
        Args:
            batch_id: Batch with ground truth labels
            model_type: Type of model to train
            test_size: Fraction for test set
            
        Returns:
            dict with model_id, metrics, feature_importance
        """
        # Load labeled data
        labels = self.db.query(GroundTruthLabel).filter(
            GroundTruthLabel.batch_id == batch_id
        ).all()
        
        if len(labels) < 100:
            raise ValueError(f"Insufficient samples: {len(labels)} < 100")
        
        # Prepare features and labels
        X, y = self._prepare_data(labels)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Standardize features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train model
        model = LogisticRegression(
            penalty='l2',
            C=1.0,
            max_iter=1000,
            random_state=42
        )
        model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)[:, 1]
        
        metrics = {
            'auc_roc': roc_auc_score(y_test, y_prob),
            'accuracy': accuracy_score(y_test, y_pred),
            'samples_train': len(X_train),
            'samples_test': len(X_test),
            'default_rate_train': y_train.mean(),
            'default_rate_test': y_test.mean()
        }
        
        # Quality gate
        if metrics['auc_roc'] < 0.60:
            raise QualityGateError(
                f"AUC-ROC {metrics['auc_roc']:.3f} below threshold 0.60"
            )
        
        # Extract feature importance
        feature_importance = dict(zip(
            self.feature_columns,
            model.coef_[0].tolist()
        ))
        
        # Save model
        model_id = self._save_model(
            model, scaler, batch_id, metrics, feature_importance
        )
        
        return {
            'model_id': model_id,
            'metrics': metrics,
            'feature_importance': feature_importance
        }
```

---

## Data Preparation

```python
def _prepare_data(self, labels: list) -> tuple:
    """Prepare feature matrix and label vector."""
    X = []
    y = []
    
    for label in labels:
        features = label.features_snapshot
        
        # Extract features in consistent order
        row = []
        for col in self.feature_columns:
            value = features.get(col, 0.0)
            row.append(float(value) if value is not None else 0.0)
        
        X.append(row)
        y.append(label.label_value)
    
    return np.array(X), np.array(y)
```

---

## Model Persistence

### Saving Models

```python
def _save_model(
    self,
    model,
    scaler,
    batch_id: str,
    metrics: dict,
    feature_importance: dict
) -> str:
    """Save model to database and filesystem."""
    model_id = f"model_{batch_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    # Save to filesystem
    model_path = f"models/{model_id}.joblib"
    os.makedirs("models", exist_ok=True)
    joblib.dump({
        'model': model,
        'scaler': scaler,
        'feature_columns': self.feature_columns
    }, model_path)
    
    # Save to database
    registry_entry = ModelRegistry(
        model_id=model_id,
        batch_id=batch_id,
        model_type='logistic_regression',
        model_path=model_path,
        metrics=metrics,
        feature_importance=feature_importance,
        status='trained'
    )
    self.db.add(registry_entry)
    self.db.commit()
    
    return model_id
```

### Loading Models

```python
def load_model(self, model_id: str) -> dict:
    """Load model from filesystem."""
    registry = self.db.query(ModelRegistry).filter(
        ModelRegistry.model_id == model_id
    ).first()
    
    if not registry:
        raise ValueError(f"Model {model_id} not found")
    
    model_data = joblib.load(registry.model_path)
    
    return {
        'model': model_data['model'],
        'scaler': model_data['scaler'],
        'feature_columns': model_data['feature_columns'],
        'metrics': registry.metrics,
        'feature_importance': registry.feature_importance
    }
```

---

## Feature Importance

Model coefficients indicate feature importance:

```python
def get_feature_importance(model_id: str) -> dict:
    """Get sorted feature importance."""
    registry = db.query(ModelRegistry).filter(
        ModelRegistry.model_id == model_id
    ).first()
    
    importance = registry.feature_importance
    
    # Sort by absolute value
    sorted_features = sorted(
        importance.items(),
        key=lambda x: abs(x[1]),
        reverse=True
    )
    
    return {
        'features': [f[0] for f in sorted_features],
        'coefficients': [f[1] for f in sorted_features],
        'interpretation': [
            'increases default risk' if f[1] > 0 else 'decreases default risk'
            for f in sorted_features
        ]
    }
```

Example output:

```json
{
  "features": ["kyc_verified", "transaction_regularity_score", "recent_activity_flag"],
  "coefficients": [-1.23, -0.89, -0.76],
  "interpretation": ["decreases default risk", "decreases default risk", "decreases default risk"]
}
```

---

## Metrics

### AUC-ROC

Area Under the Receiver Operating Characteristic curve:

- **0.5**: Random guessing
- **0.6**: Minimum acceptable
- **0.7**: Good discrimination
- **0.8+**: Excellent discrimination

### Classification Report

```python
from sklearn.metrics import classification_report

report = classification_report(y_test, y_pred, target_names=['non-default', 'default'])
print(report)
```

Output:
```
              precision    recall  f1-score   support

 non-default       0.89      0.94      0.91       170
     default       0.72      0.58      0.64        30

    accuracy                           0.87       200
   macro avg       0.80      0.76      0.78       200
weighted avg       0.86      0.87      0.86       200
```

---

## Usage

### API Endpoint

```
POST /api/pipeline/trigger/train_model
```

```json
{
  "batch_id": "BATCH_001"
}
```

### Direct Usage

```python
from app.services.model_training_service import ModelTrainingService

service = ModelTrainingService(db)

result = service.train_model(batch_id="BATCH_001")

print(f"Model ID: {result['model_id']}")
print(f"AUC-ROC: {result['metrics']['auc_roc']:.3f}")
print(f"Top features: {list(result['feature_importance'].keys())[:3]}")
```

---

## Model Registry Schema

```sql
CREATE TABLE model_registry (
    id SERIAL PRIMARY KEY,
    model_id VARCHAR(100) UNIQUE,
    batch_id VARCHAR(100),
    model_type VARCHAR(50),
    model_path VARCHAR(255),
    metrics JSONB,
    feature_importance JSONB,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Best Practices

1. **Minimum Samples**: Require 100+ labeled samples
2. **Stratified Split**: Maintain class balance in train/test
3. **Feature Scaling**: Always standardize features
4. **Quality Gate**: Enforce minimum AUC-ROC
5. **Versioning**: Track all trained models
6. **Reproducibility**: Set random seeds
