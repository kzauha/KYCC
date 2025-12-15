# Scoring API

Compute credit scores for parties using the KYCC scorecard model.

## Overview

The Scoring API provides endpoints to:
- Compute credit scores (300-900 range)
- View scoring history
- Extract features manually
- View feature details

## Endpoints

### Compute Credit Score

```http
POST /api/scoring/score/{party_id}
```

Compute a credit score for the specified party.

**Path Parameters**:
- `party_id` (int): The party ID to score

**Query Parameters**:
- `model_version` (string, optional): Specific model version to use (default: latest active)
- `include_explanation` (bool, optional): Include feature contributions (default: true)

**Response** (200 OK):
```json
{
  "party_id": 1,
  "party_name": "ACME Suppliers Inc",
  "score": 761,
  "score_band": "good",
  "confidence": 0.91,
  "decision": "APPROVE",
  "decision_reasons": [
    "Rule 4: Approve if final_score > 750"
  ],
  "explanation": {
    "top_positive_factors": [
      {
        "feature": "transaction_count",
        "value": 15.0,
        "contribution": 0.1875,
        "weight": 0.25
      },
      {
        "feature": "transaction_regularity",
        "value": 0.96,
        "contribution": 0.144,
        "weight": 0.15
      },
      {
        "feature": "kyc_score",
        "value": 85.0,
        "contribution": 0.170,
        "weight": 0.20
      }
    ],
    "top_negative_factors": []
  },
  "features_used": 11,
  "features_total": 11,
  "computed_at": "2025-12-15T10:31:00Z",
  "model_version": "default_scorecard_v1",
  "processing_time_ms": 145
}
```

---

### Get Score History

```http
GET /api/scoring/score/{party_id}/history
```

Retrieve the scoring history for a party.

**Path Parameters**:
- `party_id` (int): The party ID

**Query Parameters**:
- `limit` (int, optional): Maximum records to return (default: 10)

**Response** (200 OK):
```json
{
  "party_id": 1,
  "party_name": "ACME Suppliers Inc",
  "scores": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "score": 761,
      "score_band": "good",
      "decision": "APPROVE",
      "confidence": 0.91,
      "computed_at": "2025-12-15T10:31:00Z",
      "model_version": "default_scorecard_v1"
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "score": 748,
      "score_band": "good",
      "decision": "MANUAL_REVIEW",
      "confidence": 0.87,
      "computed_at": "2025-12-08T14:20:00Z",
      "model_version": "default_scorecard_v1"
    }
  ],
  "total_scores": 2,
  "score_trend": "improving",
  "avg_score": 754.5
}
```

---

### Get Party Features

```http
GET /api/scoring/features/{party_id}
```

Retrieve all extracted features for a party.

**Path Parameters**:
- `party_id` (int): The party ID

**Query Parameters**:
- `source_type` (string, optional): Filter by source: `KYC`, `TRANSACTION`, `NETWORK`
- `current_only` (bool, optional): Only show current features (default: true)

**Response** (200 OK):
```json
{
  "party_id": 1,
  "party_name": "ACME Suppliers Inc",
  "features": [
    {
      "feature_name": "kyc_score",
      "feature_value": 85.0,
      "source_type": "KYC",
      "confidence_score": 1.0,
      "computed_at": "2025-12-15T10:30:00Z",
      "valid_from": "2025-12-15T10:30:00Z",
      "valid_to": null
    },
    {
      "feature_name": "transaction_count",
      "feature_value": 15.0,
      "source_type": "TRANSACTION",
      "confidence_score": 1.0,
      "computed_at": "2025-12-15T10:30:00Z",
      "valid_from": "2025-12-15T10:30:00Z",
      "valid_to": null
    },
    {
      "feature_name": "network_size",
      "feature_value": 2.0,
      "source_type": "NETWORK",
      "confidence_score": 1.0,
      "computed_at": "2025-12-15T10:30:00Z",
      "valid_from": "2025-12-15T10:30:00Z",
      "valid_to": null
    }
  ],
  "feature_count": 11,
  "last_computed": "2025-12-15T10:30:00Z"
}
```

---

### Compute Features Manually

```http
POST /api/scoring/compute-features/{party_id}
```

Manually trigger feature extraction for a party (bypasses cache).

**Path Parameters**:
- `party_id` (int): The party ID

**Response** (200 OK):
```json
{
  "party_id": 1,
  "features_extracted": 11,
  "sources": ["KYC", "TRANSACTION", "NETWORK"],
  "computation_time_ms": 87,
  "message": "Features extracted successfully"
}
```

---

## Score Bands

Credit scores are classified into bands:

| Band | Score Range | Description | Typical Decision |
|------|-------------|-------------|------------------|
| **Excellent** | 800-900 | Very low risk | Auto-approve |
| **Good** | 650-799 | Low risk | Approve with conditions |
| **Fair** | 550-649 | Medium risk | Manual review |
| **Poor** | 300-549 | High risk | Reject or require collateral |

## Decision Types

Possible decision values:

| Decision | Meaning | Next Steps |
|----------|---------|------------|
| `APPROVE` | Automatically approved | Proceed with transaction |
| `REJECT` | Automatically rejected | Do not proceed |
| `FLAG` | Flagged for attention | Review manually, may proceed with caution |
| `MANUAL_REVIEW` | Requires human review | Hold transaction pending review |

## Feature Sources

Features are extracted from three sources:

### KYC Features (4 features)
- `kyc_score`: KYC verification score (0-100)
- `company_age_days`: Days since party created
- `party_type_encoded`: Numeric encoding of party type
- `contact_completeness`: Percentage of contact fields filled

### Transaction Features (4 features)
- `transaction_count`: Total transaction count
- `avg_transaction_amount`: Mean transaction value
- `transaction_regularity`: Consistency of transactions (0-1)
- `days_since_last_transaction`: Recency of activity

### Network Features (3 features)
- `network_size`: Total parties in supply chain component
- `counterparty_count`: Direct suppliers + customers
- `network_depth`: Maximum hops in relationship graph

## Scoring Algorithm

1. **Feature Extraction**: Extract 11 features from 3 sources
2. **Normalization**: Scale all features to 0-1 range
3. **Weighted Sum**: Apply scorecard weights: `score = Σ(feature[i] × weight[i])`
4. **Scaling**: Map 0-1 score to 300-900 range: `final = 300 + (score × 600)`
5. **Banding**: Assign score band based on thresholds
6. **Rules**: Evaluate decision rules in priority order
7. **Audit**: Log complete scoring record

## Confidence Score

Confidence indicates data completeness:
- **1.0**: All features available
- **0.8-0.99**: Most features available
- **0.5-0.79**: Partial feature set
- **< 0.5**: Insufficient data (score may be unreliable)

## Caching

Features are cached for 5 minutes after extraction. To bypass cache:
- Use `POST /api/scoring/compute-features/{party_id}` first
- Or wait 5 minutes for TTL expiration

## Examples

### Compute Score with Explanation

```python
import requests

response = requests.post(
    "http://localhost:8000/api/scoring/score/1",
    params={"include_explanation": True}
)
result = response.json()

print(f"Score: {result['score']}")
print(f"Decision: {result['decision']}")
print(f"Top factors: {result['explanation']['top_positive_factors']}")
```

### Get Recent Score History

```python
response = requests.get(
    "http://localhost:8000/api/scoring/score/1/history",
    params={"limit": 5}
)
history = response.json()

for score in history['scores']:
    print(f"{score['computed_at']}: {score['score']} ({score['decision']})")
```

### Force Feature Recomputation

```python
# First, recompute features
requests.post("http://localhost:8000/api/scoring/compute-features/1")

# Then, get fresh score
response = requests.post("http://localhost:8000/api/scoring/score/1")
print(response.json()['score'])
```

## Error Handling

### Party Not Found (404)
```json
{
  "detail": "Party with id 999 not found"
}
```

### Insufficient Data (422)
```json
{
  "detail": "Cannot compute score: no transactions found for party",
  "party_id": 1,
  "missing_sources": ["TRANSACTION"]
}
```

### Model Not Found (500)
```json
{
  "detail": "No active scoring model found",
  "suggestion": "Check model_registry table"
}
```
