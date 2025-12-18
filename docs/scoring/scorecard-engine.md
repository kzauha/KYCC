# Scorecard Engine

The Scorecard Engine computes credit scores using a weighted feature scoring model.

## Overview

| Property | Value |
|----------|-------|
| Location | `backend/app/scorecard/scorecard_engine.py` |
| Score Range | 300-900 |
| Default Version | v1 |
| Calculation | Weighted sum of normalized features |

---

## Core Philosophy

**"The Scorecard is King, AI is the Advisor"**

The scorecard provides transparent, explainable credit decisions:

1. **Transparency**: Every score component is traceable
2. **Auditability**: Decision rules are documented
3. **Stability**: Scores change predictably with inputs
4. **ML Refinement**: AI improves weights, not replaces logic

---

## Score Calculation

### Formula

```
Raw Score = Sum(feature_value * weight * multiplier)
Normalized Score = 300 + (Raw Score / Max Possible Score) * 600
Final Score = min(900, max(300, Normalized Score))
```

### Process Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Scorecard Engine                                 │
│                                                                     │
│   Input: Feature Dictionary                                         │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  {                                                          │  │
│   │    "kyc_verified": 1.0,                                     │  │
│   │    "company_age_years": 5.0,                                │  │
│   │    "transaction_count_6m": 45.0,                            │  │
│   │    ...                                                      │  │
│   │  }                                                          │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Scorecard Configuration                                    │  │
│   │  ┌───────────────────────────────────────────────────────┐ │  │
│   │  │ Feature: kyc_verified                                 │ │  │
│   │  │   weight: 15, multiplier: 1.0, max_raw: 15           │ │  │
│   │  └───────────────────────────────────────────────────────┘ │  │
│   │  ┌───────────────────────────────────────────────────────┐ │  │
│   │  │ Feature: company_age_years                            │ │  │
│   │  │   weight: 10, multiplier: 2.0, max_raw: 20           │ │  │
│   │  └───────────────────────────────────────────────────────┘ │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Weighted Sum Calculation                                   │  │
│   │                                                             │  │
│   │  kyc_verified: 1.0 * 15 * 1.0 = 15                         │  │
│   │  company_age_years: min(5.0, 10) * 10 * 2.0 = 100          │  │
│   │  ...                                                        │  │
│   │  Raw Score: 185                                             │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                          │                                          │
│                          ▼                                          │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  Normalization                                              │  │
│   │                                                             │  │
│   │  Max Possible: 300                                          │  │
│   │  Normalized: 300 + (185/300) * 600 = 670                   │  │
│   │  Final Score: 670                                           │  │
│   └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation

```python
def compute_scorecard_score(
    features: dict,
    scorecard_config: dict = None,
    version: str = "v1"
) -> dict:
    """
    Compute credit score from features.
    
    Args:
        features: Dictionary of feature_name -> feature_value
        scorecard_config: Optional custom scorecard configuration
        version: Scorecard version to use
        
    Returns:
        dict with total_score, band, components, version
    """
    config = scorecard_config or get_scorecard_config(version)
    
    raw_score = 0.0
    max_possible = 0.0
    components = []
    
    for feature_name, feature_config in config['features'].items():
        weight = feature_config['weight']
        multiplier = feature_config.get('multiplier', 1.0)
        max_value = feature_config.get('max_value', float('inf'))
        
        # Get feature value (default to 0)
        value = features.get(feature_name, 0.0)
        
        # Cap at max value
        capped_value = min(value, max_value)
        
        # Calculate contribution
        contribution = capped_value * weight * multiplier
        max_contribution = max_value * weight * multiplier
        
        raw_score += contribution
        max_possible += max_contribution
        
        components.append({
            'feature': feature_name,
            'value': value,
            'weight': weight,
            'contribution': contribution,
            'max_contribution': max_contribution
        })
    
    # Normalize to 300-900 range
    if max_possible > 0:
        normalized = 300 + (raw_score / max_possible) * 600
    else:
        normalized = 300
    
    final_score = min(900, max(300, int(normalized)))
    
    return {
        'total_score': final_score,
        'band': get_score_band(final_score),
        'components': components,
        'raw_score': raw_score,
        'max_possible': max_possible,
        'version': version
    }
```

---

## Scorecard Configuration

### Structure

```python
SCORECARD_CONFIG = {
    "version": "v1",
    "features": {
        "kyc_verified": {
            "weight": 15,
            "multiplier": 1.0,
            "max_value": 1
        },
        "company_age_years": {
            "weight": 10,
            "multiplier": 2.0,
            "max_value": 10
        },
        "transaction_count_6m": {
            "weight": 10,
            "multiplier": 0.5,
            "max_value": 100
        },
        # ... more features
    }
}
```

### Feature Configuration Properties

| Property | Type | Description |
|----------|------|-------------|
| weight | float | Base importance of the feature |
| multiplier | float | Scaling factor for feature value |
| max_value | float | Cap for feature value (prevents outliers) |

---

## Default Feature Weights

### KYC Features

| Feature | Weight | Multiplier | Max Value |
|---------|--------|------------|-----------|
| kyc_verified | 15 | 1.0 | 1 |
| company_age_years | 10 | 2.0 | 10 |
| party_type_score | 5 | 1.0 | 10 |
| contact_completeness | 5 | 0.1 | 100 |
| has_tax_id | 10 | 1.0 | 1 |

### Transaction Features

| Feature | Weight | Multiplier | Max Value |
|---------|--------|------------|-----------|
| transaction_count_6m | 10 | 0.5 | 100 |
| avg_transaction_amount | 5 | 0.001 | 50000 |
| total_transaction_volume_6m | 5 | 0.00001 | 1000000 |
| transaction_regularity_score | 10 | 0.1 | 100 |
| recent_activity_flag | 15 | 1.0 | 1 |

### Network Features

| Feature | Weight | Multiplier | Max Value |
|---------|--------|------------|-----------|
| direct_counterparty_count | 5 | 0.5 | 20 |
| network_depth_downstream | 3 | 1.0 | 5 |
| network_size | 5 | 0.2 | 50 |
| supplier_count | 5 | 0.5 | 10 |
| customer_count | 5 | 0.5 | 10 |
| network_balance_ratio | 7 | 10.0 | 1 |

---

## Usage

### Basic Usage

```python
from app.scorecard.scorecard_engine import compute_scorecard_score

features = {
    "kyc_verified": 1.0,
    "company_age_years": 5.0,
    "transaction_count_6m": 45.0,
    "avg_transaction_amount": 5000.0,
    "transaction_regularity_score": 75.0,
    "recent_activity_flag": 1.0,
    "direct_counterparty_count": 8.0,
    "network_size": 15.0
}

result = compute_scorecard_score(features)

print(f"Score: {result['total_score']}")
print(f"Band: {result['band']}")
```

Output:
```
Score: 720
Band: good
```

### With Custom Config

```python
custom_config = {
    "version": "custom_v1",
    "features": {
        "kyc_verified": {"weight": 20, "multiplier": 1.0, "max_value": 1},
        "company_age_years": {"weight": 15, "multiplier": 1.5, "max_value": 15}
    }
}

result = compute_scorecard_score(features, scorecard_config=custom_config)
```

### With Specific Version

```python
# Use ML-refined scorecard version
result = compute_scorecard_score(features, version="ml_v2")
```

---

## Score Explanation

The engine provides detailed explanations:

```python
result = compute_scorecard_score(features)

for component in result['components']:
    print(f"{component['feature']}:")
    print(f"  Value: {component['value']}")
    print(f"  Weight: {component['weight']}")
    print(f"  Contribution: {component['contribution']:.2f}")
    print(f"  Max Possible: {component['max_contribution']:.2f}")
    print()
```

Output:
```
kyc_verified:
  Value: 1.0
  Weight: 15
  Contribution: 15.00
  Max Possible: 15.00

company_age_years:
  Value: 5.0
  Weight: 10
  Contribution: 100.00
  Max Possible: 200.00
```

---

## Missing Features

When features are missing:

1. Default value of 0 is used
2. Contribution to score is 0
3. Max possible score is still calculated
4. Result includes flag for missing features

```python
# Features with missing values
features = {
    "kyc_verified": 1.0
    # Other features missing
}

result = compute_scorecard_score(features)
# Score will be low due to missing features
```
