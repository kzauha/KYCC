# Score Bands

Score bands categorize credit scores into risk levels for business decisions.

## Overview

| Band | Score Range | Risk Level |
|------|-------------|------------|
| excellent | 800-900 | Very Low |
| good | 700-799 | Low |
| fair | 600-699 | Medium |
| poor | 450-599 | High |
| very_poor | 300-449 | Very High |

---

## Band Assignment

### Implementation

```python
def get_score_band(score: int) -> str:
    """
    Map score to risk band.
    
    Args:
        score: Credit score (300-900)
        
    Returns:
        Band name
    """
    if score >= 800:
        return "excellent"
    elif score >= 700:
        return "good"
    elif score >= 600:
        return "fair"
    elif score >= 450:
        return "poor"
    else:
        return "very_poor"
```

### Band Descriptions

#### Excellent (800-900)

- **Risk Level**: Very Low
- **Characteristics**:
  - Strong KYC verification
  - Established business (5+ years)
  - High transaction volume and regularity
  - Diverse network of counterparties
- **Recommendation**: Standard terms, priority processing

#### Good (700-799)

- **Risk Level**: Low
- **Characteristics**:
  - KYC verified
  - Established business (2-5 years)
  - Regular transaction history
  - Active network connections
- **Recommendation**: Standard terms

#### Fair (600-699)

- **Risk Level**: Medium
- **Characteristics**:
  - May have some KYC gaps
  - Moderate business age (1-2 years)
  - Adequate transaction history
  - Some network connections
- **Recommendation**: Enhanced monitoring, shorter terms

#### Poor (450-599)

- **Risk Level**: High
- **Characteristics**:
  - KYC concerns
  - New or young business
  - Limited transaction history
  - Few network connections
- **Recommendation**: Collateral requirements, manual review

#### Very Poor (300-449)

- **Risk Level**: Very High
- **Characteristics**:
  - Major KYC issues
  - Very new or problematic business
  - Minimal or no transactions
  - Isolated from network
- **Recommendation**: Decline or heavy restrictions

---

## Band Distribution

Typical distribution in healthy portfolio:

```
┌──────────────────────────────────────────────────────────────────────┐
│                      Score Band Distribution                         │
│                                                                      │
│  excellent  ████████████                               15%           │
│  good       ████████████████████████████               35%           │
│  fair       ██████████████████████████                 30%           │
│  poor       ████████████                               15%           │
│  very_poor  ████                                        5%           │
│                                                                      │
│             0%   10%   20%   30%   40%   50%                        │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Band Statistics

### API Endpoint

```
GET /api/scoring/statistics
```

### Response

```json
{
  "total_scored": 1000,
  "band_distribution": {
    "excellent": {"count": 150, "percentage": 15.0},
    "good": {"count": 350, "percentage": 35.0},
    "fair": {"count": 300, "percentage": 30.0},
    "poor": {"count": 150, "percentage": 15.0},
    "very_poor": {"count": 50, "percentage": 5.0}
  },
  "average_score": 652,
  "median_score": 665,
  "score_range": {
    "min": 320,
    "max": 875
  }
}
```

---

## Band-Based Decisions

### Credit Limits

| Band | Suggested Limit |
|------|-----------------|
| excellent | Up to 100% of requested |
| good | Up to 80% of requested |
| fair | Up to 50% of requested |
| poor | Up to 25% or collateralized |
| very_poor | Decline or 100% collateral |

### Payment Terms

| Band | Suggested Terms |
|------|-----------------|
| excellent | Net 60 |
| good | Net 45 |
| fair | Net 30 |
| poor | Net 15 or prepay |
| very_poor | Prepay only |

### Review Requirements

| Band | Review Process |
|------|----------------|
| excellent | Auto-approve |
| good | Auto-approve with notification |
| fair | Supervisor review |
| poor | Committee review |
| very_poor | Executive review or decline |

---

## Usage in Code

### Basic Usage

```python
from app.scorecard.scorecard_engine import get_score_band

score = 720
band = get_score_band(score)

print(f"Score {score} is in band: {band}")
# Output: Score 720 is in band: good
```

### With Scoring Service

```python
result = scoring_service.compute_score(party_id=123)

print(f"Score: {result['total_score']}")
print(f"Band: {result['band']}")

# Make decision based on band
if result['band'] in ['excellent', 'good']:
    approve_credit()
elif result['band'] == 'fair':
    request_review()
else:
    decline_or_restrict()
```

### Band Filtering

```python
# Get all parties in specific bands
from app.models.models import ScoreRequest

excellent_parties = db.query(ScoreRequest).filter(
    ScoreRequest.band == 'excellent'
).all()

high_risk_parties = db.query(ScoreRequest).filter(
    ScoreRequest.band.in_(['poor', 'very_poor'])
).all()
```

---

## Band Transitions

Track how scores change over time:

```python
def get_band_transitions(party_id: int, db: Session) -> list:
    """Get band transition history for a party."""
    scores = db.query(ScoreRequest).filter(
        ScoreRequest.party_id == party_id
    ).order_by(ScoreRequest.created_at).all()
    
    transitions = []
    for i in range(1, len(scores)):
        if scores[i].band != scores[i-1].band:
            transitions.append({
                'from_band': scores[i-1].band,
                'to_band': scores[i].band,
                'date': scores[i].created_at,
                'score_change': scores[i].total_score - scores[i-1].total_score
            })
    
    return transitions
```

---

## Customizing Bands

### Configuration

Bands can be customized via configuration:

```python
BAND_CONFIG = {
    "excellent": {"min": 800, "max": 900},
    "good": {"min": 700, "max": 799},
    "fair": {"min": 600, "max": 699},
    "poor": {"min": 450, "max": 599},
    "very_poor": {"min": 300, "max": 449}
}

def get_score_band_custom(score: int, config: dict = None) -> str:
    """Get band with custom configuration."""
    config = config or BAND_CONFIG
    
    for band_name, ranges in config.items():
        if ranges['min'] <= score <= ranges['max']:
            return band_name
    
    return "unknown"
```

### Adding Bands

For finer granularity:

```python
EXTENDED_BAND_CONFIG = {
    "excellent_plus": {"min": 850, "max": 900},
    "excellent": {"min": 800, "max": 849},
    "good_plus": {"min": 750, "max": 799},
    "good": {"min": 700, "max": 749},
    "fair_plus": {"min": 650, "max": 699},
    "fair": {"min": 600, "max": 649},
    "poor": {"min": 450, "max": 599},
    "very_poor": {"min": 300, "max": 449}
}
```

---

## Monitoring and Alerts

### Band Drift Detection

```python
def check_band_drift(batch_id: str, db: Session) -> dict:
    """Check for unusual band distributions in a batch."""
    expected = {"excellent": 0.15, "good": 0.35, "fair": 0.30, "poor": 0.15, "very_poor": 0.05}
    
    results = db.query(
        ScoreRequest.band,
        func.count(ScoreRequest.id)
    ).filter(
        ScoreRequest.batch_id == batch_id
    ).group_by(ScoreRequest.band).all()
    
    total = sum(count for _, count in results)
    actual = {band: count/total for band, count in results}
    
    drift = {}
    for band, expected_pct in expected.items():
        actual_pct = actual.get(band, 0)
        drift[band] = {
            'expected': expected_pct,
            'actual': actual_pct,
            'difference': actual_pct - expected_pct,
            'alert': abs(actual_pct - expected_pct) > 0.1
        }
    
    return drift
```

### Alert on High-Risk Concentration

```python
def alert_high_risk_concentration(batch_id: str, threshold: float = 0.25) -> bool:
    """Alert if too many scores are in poor/very_poor bands."""
    high_risk_count = db.query(ScoreRequest).filter(
        ScoreRequest.batch_id == batch_id,
        ScoreRequest.band.in_(['poor', 'very_poor'])
    ).count()
    
    total_count = db.query(ScoreRequest).filter(
        ScoreRequest.batch_id == batch_id
    ).count()
    
    if total_count > 0 and high_risk_count / total_count > threshold:
        send_alert(f"High risk concentration: {high_risk_count/total_count:.1%}")
        return True
    
    return False
```
