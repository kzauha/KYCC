# Ground Truth Labels

Ground truth labels capture actual credit outcomes for machine learning training.

## Overview

| Property | Value |
|----------|-------|
| Location | `backend/app/services/label_generation_service.py` |
| Table | ground_truth_labels |
| Label Types | default, non-default |
| Observation Window | Configurable (default: 180 days) |

---

## Label Definition

A ground truth label represents the actual credit outcome for a party:

| Label | Value | Description |
|-------|-------|-------------|
| default | 1 | Party defaulted on credit obligation |
| non-default | 0 | Party fulfilled credit obligation |

---

## Label Generation Process

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Label Generation Flow                             │
│                                                                     │
│   1. Select parties with credit history                             │
│      │                                                              │
│      ▼                                                              │
│   2. Determine observation date                                     │
│      (score date + observation window)                              │
│      │                                                              │
│      ▼                                                              │
│   3. Check for default events                                       │
│      - Payment delays > 90 days                                     │
│      - Account write-offs                                           │
│      - Collection referrals                                         │
│      │                                                              │
│      ▼                                                              │
│   4. Assign label                                                   │
│      default=1 if any default event                                 │
│      default=0 otherwise                                            │
│      │                                                              │
│      ▼                                                              │
│   5. Store in ground_truth_labels table                             │
│      with feature snapshot                                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## LabelGenerationService

### Implementation

```python
class LabelGenerationService:
    """Generate ground truth labels for ML training."""
    
    def __init__(self, db: Session):
        self.db = db
        self.feature_pipeline = FeaturePipelineService(db)
    
    def generate_labels(
        self,
        batch_id: str,
        outcome_type: str = "default",
        observation_window_days: int = 180
    ) -> dict:
        """
        Generate labels for parties in a batch.
        
        Args:
            batch_id: Batch identifier
            outcome_type: Type of outcome to label
            observation_window_days: Days after score to observe outcome
            
        Returns:
            dict with label counts and statistics
        """
        parties = self.db.query(Party).filter(
            Party.batch_id == batch_id
        ).all()
        
        labels_created = 0
        default_count = 0
        
        for party in parties:
            # Get score date
            score_request = self.db.query(ScoreRequest).filter(
                ScoreRequest.party_id == party.id
            ).order_by(ScoreRequest.created_at.desc()).first()
            
            if not score_request:
                continue
            
            # Calculate observation end date
            observation_date = score_request.created_at + timedelta(
                days=observation_window_days
            )
            
            # Check for default
            is_default = self._check_default(party.id, observation_date)
            
            # Extract features at score date
            features = self.feature_pipeline.extract_all_features(
                party.id,
                as_of_date=score_request.created_at
            )
            
            # Create label
            label = GroundTruthLabel(
                party_id=party.id,
                batch_id=batch_id,
                label_type=outcome_type,
                label_value=1 if is_default else 0,
                observation_date=observation_date,
                features_snapshot=self._flatten_features(features),
                score_at_label=score_request.total_score
            )
            
            self.db.add(label)
            labels_created += 1
            if is_default:
                default_count += 1
        
        self.db.commit()
        
        return {
            "batch_id": batch_id,
            "labels_created": labels_created,
            "default_count": default_count,
            "non_default_count": labels_created - default_count,
            "default_rate": default_count / labels_created if labels_created > 0 else 0
        }
```

---

## Default Detection

### Criteria

```python
def _check_default(self, party_id: int, observation_date: datetime) -> bool:
    """
    Check if party defaulted before observation date.
    
    Default criteria:
    - Payment delay > 90 days
    - Account write-off
    - Collection referral
    """
    # Check for payment delays
    late_payments = self.db.query(Transaction).filter(
        Transaction.party_id == party_id,
        Transaction.transaction_date <= observation_date,
        Transaction.days_past_due > 90
    ).count()
    
    if late_payments > 0:
        return True
    
    # Check for write-offs
    writeoffs = self.db.query(CreditEvent).filter(
        CreditEvent.party_id == party_id,
        CreditEvent.event_type == 'writeoff',
        CreditEvent.event_date <= observation_date
    ).count()
    
    if writeoffs > 0:
        return True
    
    return False
```

---

## Synthetic Label Generation

For synthetic data without real outcomes:

```python
def generate_synthetic_labels(
    self,
    batch_id: str,
    default_rate: float = 0.15
) -> dict:
    """
    Generate synthetic labels based on score.
    
    Higher scores have lower default probability.
    """
    parties = self.db.query(Party).filter(
        Party.batch_id == batch_id
    ).all()
    
    for party in parties:
        score_request = self.db.query(ScoreRequest).filter(
            ScoreRequest.party_id == party.id
        ).first()
        
        if not score_request:
            continue
        
        # Default probability inversely related to score
        # Score 300 -> ~30% default, Score 900 -> ~5% default
        base_prob = 0.35 - (score_request.total_score - 300) / 600 * 0.30
        adjusted_prob = base_prob * (default_rate / 0.15)  # Adjust to target rate
        
        is_default = random.random() < adjusted_prob
        
        features = self.feature_pipeline.extract_all_features(party.id)
        
        label = GroundTruthLabel(
            party_id=party.id,
            batch_id=batch_id,
            label_type="synthetic_default",
            label_value=1 if is_default else 0,
            features_snapshot=self._flatten_features(features),
            score_at_label=score_request.total_score
        )
        
        self.db.add(label)
    
    self.db.commit()
```

---

## Feature Snapshot

Features are captured at label time to prevent data leakage:

```python
def _flatten_features(self, feature_result: dict) -> dict:
    """Flatten features for storage."""
    return {
        f['feature_name']: f['feature_value']
        for f in feature_result['features_list']
    }
```

This ensures:
- Training uses only features available at decision time
- No future information leaks into training
- Reproducible model training

---

## Label Schema

```sql
CREATE TABLE ground_truth_labels (
    id SERIAL PRIMARY KEY,
    party_id INTEGER REFERENCES parties(id),
    batch_id VARCHAR(100),
    label_type VARCHAR(50),
    label_value INTEGER,
    observation_date TIMESTAMP,
    features_snapshot JSONB,
    score_at_label INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Usage

### API Endpoint

```
POST /api/pipeline/trigger/generate_labels
```

```json
{
  "batch_id": "BATCH_001",
  "observation_window_days": 180
}
```

### Direct Usage

```python
from app.services.label_generation_service import LabelGenerationService

service = LabelGenerationService(db)

result = service.generate_labels(
    batch_id="BATCH_001",
    observation_window_days=180
)

print(f"Labels created: {result['labels_created']}")
print(f"Default rate: {result['default_rate']:.1%}")
```

---

## Label Quality Checks

### Balance Check

```python
def check_label_balance(batch_id: str, db: Session) -> dict:
    """Check if labels are reasonably balanced."""
    labels = db.query(GroundTruthLabel).filter(
        GroundTruthLabel.batch_id == batch_id
    ).all()
    
    total = len(labels)
    defaults = sum(1 for l in labels if l.label_value == 1)
    default_rate = defaults / total if total > 0 else 0
    
    return {
        "total": total,
        "defaults": defaults,
        "non_defaults": total - defaults,
        "default_rate": default_rate,
        "is_balanced": 0.05 <= default_rate <= 0.50
    }
```

### Minimum Sample Check

```python
MIN_SAMPLES = 100

def check_sufficient_samples(batch_id: str, db: Session) -> bool:
    """Check if batch has enough labeled samples."""
    count = db.query(GroundTruthLabel).filter(
        GroundTruthLabel.batch_id == batch_id
    ).count()
    
    return count >= MIN_SAMPLES
```

---

## Best Practices

1. **Observation Window**: Use consistent window (typically 180 days)
2. **Feature Snapshot**: Always capture features at label time
3. **Balance**: Target 10-30% default rate for best model performance
4. **Sample Size**: Minimum 100 samples, prefer 500+
5. **Temporal Separation**: Training data before validation data
