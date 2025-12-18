# Scorecard Refinement

Scorecard refinement converts ML model coefficients into updated scorecard weights.

## Overview

| Property | Value |
|----------|-------|
| Location | `backend/app/services/scorecard_version_service.py` |
| Input | Trained model coefficients |
| Output | New scorecard version (draft) |
| Deployment | Manual activation required |

---

## Refinement Process

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Scorecard Refinement                             │
│                                                                     │
│   1. Load Model Coefficients                                        │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  kyc_verified: -1.23                                        │  │
│   │  company_age_years: -0.45                                   │  │
│   │  transaction_regularity_score: -0.89                        │  │
│   │  ...                                                        │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   2. Convert to Positive Weights                                    │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  ML predicts default (1 = bad)                              │  │
│   │  Scorecard wants credit score (higher = better)             │  │
│   │  So: weight = -coefficient (flip sign)                      │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   3. Normalize Weights                                              │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Scale to sum to 100 (or match base scorecard)              │  │
│   │  Preserve relative importance                               │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   4. Blend with Base Weights (optional)                             │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  new_weight = (1-alpha)*base + alpha*ml                     │  │
│   │  alpha = 0.3 (conservative) to 0.7 (aggressive)             │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   5. Create Draft Version                                           │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Store as new scorecard version                             │  │
│   │  Status: draft (not active)                                 │  │
│   │  Requires manual activation                                 │  │
│   └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ScorecardVersionService

### Implementation

```python
class ScorecardVersionService:
    """Manage scorecard versions and refinement."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def refine_from_model(
        self,
        model_id: str,
        base_version: str = "v1",
        blend_factor: float = 0.5
    ) -> dict:
        """
        Create new scorecard version from ML model.
        
        Args:
            model_id: Trained model ID
            base_version: Base scorecard to refine
            blend_factor: Weight for ML vs base (0-1)
            
        Returns:
            New scorecard version info
        """
        # Load model
        model_registry = self.db.query(ModelRegistry).filter(
            ModelRegistry.model_id == model_id
        ).first()
        
        if not model_registry:
            raise ValueError(f"Model {model_id} not found")
        
        coefficients = model_registry.feature_importance
        
        # Load base scorecard
        base_config = self.get_version(base_version)
        
        # Convert coefficients to weights
        ml_weights = self._coefficients_to_weights(coefficients)
        
        # Blend with base weights
        blended_weights = self._blend_weights(
            base_config['features'],
            ml_weights,
            blend_factor
        )
        
        # Create new version
        new_version = self._create_version(
            blended_weights,
            base_version,
            model_id
        )
        
        return new_version
```

---

## Coefficient Conversion

```python
def _coefficients_to_weights(self, coefficients: dict) -> dict:
    """
    Convert ML coefficients to scorecard weights.
    
    ML coefficients are for predicting default (bad).
    Scorecard weights should reward good behavior.
    """
    weights = {}
    
    for feature, coef in coefficients.items():
        # Flip sign: negative coef = reduces default = higher score
        raw_weight = -coef
        
        # Ensure non-negative (clip at 0)
        weights[feature] = max(0, raw_weight)
    
    # Normalize to sum to 100
    total = sum(weights.values())
    if total > 0:
        weights = {k: (v / total) * 100 for k, v in weights.items()}
    
    return weights
```

---

## Weight Blending

```python
def _blend_weights(
    self,
    base_features: dict,
    ml_weights: dict,
    blend_factor: float
) -> dict:
    """
    Blend base and ML weights.
    
    blend_factor = 0: Use only base weights
    blend_factor = 1: Use only ML weights
    blend_factor = 0.5: Equal blend
    """
    blended = {}
    
    for feature, base_config in base_features.items():
        base_weight = base_config['weight']
        ml_weight = ml_weights.get(feature, base_weight)
        
        blended_weight = (1 - blend_factor) * base_weight + blend_factor * ml_weight
        
        blended[feature] = {
            'weight': blended_weight,
            'multiplier': base_config.get('multiplier', 1.0),
            'max_value': base_config.get('max_value', float('inf'))
        }
    
    return blended
```

---

## Version Creation

```python
def _create_version(
    self,
    features: dict,
    base_version: str,
    model_id: str
) -> dict:
    """Create new scorecard version in database."""
    # Generate version ID
    version_id = f"ml_v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    
    # Create version record
    version = ScorecardVersion(
        version_id=version_id,
        base_version=base_version,
        model_id=model_id,
        features=features,
        status='draft',
        created_at=datetime.utcnow()
    )
    
    self.db.add(version)
    self.db.commit()
    
    return {
        'version_id': version_id,
        'base_version': base_version,
        'model_id': model_id,
        'status': 'draft',
        'features': features
    }
```

---

## Version Comparison

```python
def compare_versions(self, version_a: str, version_b: str) -> dict:
    """Compare two scorecard versions."""
    a = self.get_version(version_a)
    b = self.get_version(version_b)
    
    comparison = []
    
    for feature in a['features'].keys():
        weight_a = a['features'][feature]['weight']
        weight_b = b['features'].get(feature, {}).get('weight', 0)
        
        change = weight_b - weight_a
        pct_change = (change / weight_a * 100) if weight_a > 0 else 0
        
        comparison.append({
            'feature': feature,
            'weight_a': weight_a,
            'weight_b': weight_b,
            'change': change,
            'pct_change': pct_change
        })
    
    return {
        'version_a': version_a,
        'version_b': version_b,
        'features': comparison,
        'total_weight_change': sum(abs(c['change']) for c in comparison)
    }
```

---

## Version Activation

```python
def activate_version(self, version_id: str) -> dict:
    """
    Activate a scorecard version.
    
    Deactivates all other versions.
    """
    # Deactivate all versions
    self.db.query(ScorecardVersion).update({'status': 'inactive'})
    
    # Activate specified version
    version = self.db.query(ScorecardVersion).filter(
        ScorecardVersion.version_id == version_id
    ).first()
    
    if not version:
        raise ValueError(f"Version {version_id} not found")
    
    version.status = 'active'
    version.activated_at = datetime.utcnow()
    
    self.db.commit()
    
    return {
        'version_id': version_id,
        'status': 'active',
        'activated_at': version.activated_at.isoformat()
    }
```

---

## Usage

### API Endpoints

Refine scorecard:
```
POST /api/scoring/refine
```

```json
{
  "model_id": "model_BATCH_001_20240115_103045",
  "base_version": "v1",
  "blend_factor": 0.5
}
```

Compare versions:
```
GET /api/scoring/versions/compare?a=v1&b=ml_v20240115
```

Activate version:
```
POST /api/scoring/versions/{version_id}/activate
```

### Direct Usage

```python
from app.services.scorecard_version_service import ScorecardVersionService

service = ScorecardVersionService(db)

# Create refined version
result = service.refine_from_model(
    model_id="model_BATCH_001",
    base_version="v1",
    blend_factor=0.5
)

print(f"Created version: {result['version_id']}")

# Compare versions
comparison = service.compare_versions("v1", result['version_id'])

for feat in comparison['features']:
    print(f"{feat['feature']}: {feat['weight_a']:.2f} -> {feat['weight_b']:.2f} ({feat['pct_change']:+.1f}%)")

# After review, activate
service.activate_version(result['version_id'])
```

---

## Validation Checks

Before activating a new version:

```python
def validate_version(self, version_id: str) -> dict:
    """Validate scorecard version before activation."""
    version = self.get_version(version_id)
    
    issues = []
    
    # Check weight sum
    total_weight = sum(f['weight'] for f in version['features'].values())
    if not (95 <= total_weight <= 105):
        issues.append(f"Total weight {total_weight:.1f} not near 100")
    
    # Check for zero weights
    zero_weights = [f for f, c in version['features'].items() if c['weight'] == 0]
    if zero_weights:
        issues.append(f"Zero weights: {zero_weights}")
    
    # Compare to base
    comparison = self.compare_versions(version['base_version'], version_id)
    large_changes = [
        c for c in comparison['features']
        if abs(c['pct_change']) > 50
    ]
    if large_changes:
        issues.append(f"Large changes (>50%): {[c['feature'] for c in large_changes]}")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues
    }
```

---

## Best Practices

1. **Conservative Blending**: Start with blend_factor=0.3
2. **Validation**: Always validate before activating
3. **Comparison**: Review weight changes carefully
4. **Rollback**: Keep previous version available
5. **Monitoring**: Track score distribution after activation
6. **Documentation**: Record reason for version changes
