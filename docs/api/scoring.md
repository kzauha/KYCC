# Scoring API

The scoring API computes and retrieves credit scores for parties.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/scoring/run | Compute score for a party |
| GET | /api/scoring/party/{id} | Get score for a party |
| GET | /api/scoring/batch/{batch_id} | Get scores for a batch |
| GET | /api/scoring/statistics | Get scoring statistics |
| GET | /api/scoring/versions | List scorecard versions |
| POST | /api/scoring/versions/{id}/activate | Activate a version |

---

## POST /api/scoring/run

Compute credit score for a party.

### Request

```json
{
  "party_id": 123,
  "scorecard_version": "v1",
  "source": "database"
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| party_id | integer | Yes | Party ID to score |
| scorecard_version | string | No | Scorecard version (default: active) |
| source | string | No | Data source: "database" or "synthetic" |

### Response

```json
{
  "party_id": 123,
  "total_score": 720,
  "band": "good",
  "scorecard_version": "v1",
  "components": [
    {
      "feature": "kyc_verified",
      "value": 1.0,
      "weight": 15,
      "contribution": 15.0,
      "max_contribution": 15.0
    },
    {
      "feature": "company_age_years",
      "value": 5.0,
      "weight": 10,
      "contribution": 100.0,
      "max_contribution": 200.0
    }
  ],
  "rules_applied": [],
  "explanation": "kyc_verified: 100% of maximum; company_age_years: 50% of maximum",
  "computed_at": "2024-01-15T10:30:45Z"
}
```

### Example

```bash
curl -X POST http://localhost:8000/api/scoring/run \
  -H "Content-Type: application/json" \
  -d '{"party_id": 123}'
```

---

## GET /api/scoring/party/{id}

Get the most recent score for a party.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| id | integer | path | Party ID |
| include_history | boolean | query | Include score history |

### Response

```json
{
  "party_id": 123,
  "current_score": {
    "total_score": 720,
    "band": "good",
    "scorecard_version": "v1",
    "computed_at": "2024-01-15T10:30:45Z"
  },
  "history": [
    {
      "total_score": 680,
      "band": "fair",
      "computed_at": "2024-01-01T08:00:00Z"
    }
  ]
}
```

### Example

```bash
curl http://localhost:8000/api/scoring/party/123?include_history=true
```

---

## GET /api/scoring/batch/{batch_id}

Get scores for all parties in a batch.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| batch_id | string | path | Batch identifier |
| band | string | query | Filter by band |
| min_score | integer | query | Minimum score filter |
| max_score | integer | query | Maximum score filter |

### Response

```json
{
  "batch_id": "BATCH_001",
  "total_parties": 100,
  "scored_parties": 98,
  "scores": [
    {
      "party_id": 123,
      "party_name": "Acme Corp",
      "total_score": 720,
      "band": "good"
    },
    {
      "party_id": 124,
      "party_name": "Beta Inc",
      "total_score": 650,
      "band": "fair"
    }
  ]
}
```

### Example

```bash
curl "http://localhost:8000/api/scoring/batch/BATCH_001?band=excellent"
```

---

## GET /api/scoring/statistics

Get aggregate scoring statistics.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| batch_id | string | query | Filter by batch |
| from_date | datetime | query | Start date |
| to_date | datetime | query | End date |

### Response

```json
{
  "total_scored": 1000,
  "band_distribution": {
    "excellent": {
      "count": 150,
      "percentage": 15.0
    },
    "good": {
      "count": 350,
      "percentage": 35.0
    },
    "fair": {
      "count": 300,
      "percentage": 30.0
    },
    "poor": {
      "count": 150,
      "percentage": 15.0
    },
    "very_poor": {
      "count": 50,
      "percentage": 5.0
    }
  },
  "score_statistics": {
    "mean": 652,
    "median": 665,
    "std_dev": 85,
    "min": 320,
    "max": 875
  },
  "period": {
    "from": "2024-01-01T00:00:00Z",
    "to": "2024-01-15T23:59:59Z"
  }
}
```

### Example

```bash
curl "http://localhost:8000/api/scoring/statistics?batch_id=BATCH_001"
```

---

## GET /api/scoring/versions

List all scorecard versions.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| include_inactive | boolean | query | Include inactive versions |

### Response

```json
{
  "versions": [
    {
      "version_id": "ml_v20240115",
      "status": "active",
      "base_version": "v1",
      "model_id": "model_BATCH_001",
      "created_at": "2024-01-15T10:30:45Z",
      "activated_at": "2024-01-15T14:00:00Z"
    },
    {
      "version_id": "v1",
      "status": "inactive",
      "base_version": null,
      "model_id": null,
      "created_at": "2024-01-01T00:00:00Z",
      "activated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "active_version": "ml_v20240115"
}
```

---

## POST /api/scoring/versions/{id}/activate

Activate a scorecard version.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| id | string | path | Version ID to activate |

### Response

```json
{
  "version_id": "v1",
  "status": "active",
  "activated_at": "2024-01-15T14:00:00Z",
  "previous_version": "ml_v20240115"
}
```

### Example

```bash
curl -X POST http://localhost:8000/api/scoring/versions/v1/activate
```

---

## Synthetic Scoring

Score synthetic profiles without storing in database:

### POST /api/scoring/synthetic

```json
{
  "profile": {
    "party_name": "Test Company",
    "party_type": "supplier",
    "kyc_verified": true,
    "company_age_years": 5,
    "transaction_count": 45,
    "avg_transaction_amount": 5000,
    "network_size": 10
  }
}
```

Response returns score without persisting data.

---

## Error Responses

### Party Not Found

```json
{
  "status": "error",
  "error": {
    "code": "PARTY_NOT_FOUND",
    "message": "Party with ID 999 not found"
  }
}
```

### Insufficient Features

```json
{
  "status": "error",
  "error": {
    "code": "INSUFFICIENT_FEATURES",
    "message": "Cannot compute score: missing required features",
    "details": {
      "missing_features": ["kyc_verified", "transaction_count_6m"]
    }
  }
}
```

### Invalid Version

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_VERSION",
    "message": "Scorecard version 'v99' not found"
  }
}
```
