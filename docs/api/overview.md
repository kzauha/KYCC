# API Overview

KYCC exposes a REST API for credit scoring, pipeline management, and data operations.

## Base URL

- **Development**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs**: `http://localhost:8000/redoc` (ReDoc)

---

## Authentication

Currently, the API does not require authentication for development purposes.

For production deployment, implement:
- API key authentication
- OAuth 2.0 / JWT tokens
- Rate limiting

---

## API Structure

```
/api
├── /scoring          # Credit scoring endpoints
│   ├── POST /run
│   ├── GET /party/{id}
│   ├── GET /statistics
│   └── /versions
├── /pipeline         # Dagster pipeline endpoints
│   ├── POST /trigger/{pipeline}
│   ├── GET /status/{run_id}
│   └── GET /runs
├── /parties          # Party management
│   ├── GET /
│   ├── GET /{id}
│   ├── POST /
│   └── PUT /{id}
├── /relationships    # Relationship management
│   ├── GET /
│   ├── GET /{id}
│   └── POST /
└── /synthetic        # Synthetic data
    ├── POST /ingest
    └── GET /batches
```

---

## Response Format

### Success Response

```json
{
  "status": "success",
  "data": {
    // Response data
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45Z",
    "request_id": "req_abc123"
  }
}
```

### Error Response

```json
{
  "status": "error",
  "error": {
    "code": "PARTY_NOT_FOUND",
    "message": "Party with ID 123 not found",
    "details": {}
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45Z",
    "request_id": "req_abc123"
  }
}
```

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

## Common Headers

### Request Headers

```
Content-Type: application/json
Accept: application/json
```

### Response Headers

```
Content-Type: application/json
X-Request-ID: req_abc123
X-Response-Time: 45ms
```

---

## Pagination

List endpoints support pagination:

```
GET /api/parties?page=1&per_page=20
```

Response includes pagination metadata:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

---

## Filtering

List endpoints support filtering:

```
GET /api/parties?party_type=supplier&batch_id=BATCH_001
GET /api/scoring/statistics?band=excellent
```

---

## Quick Reference

### Score a Party

```bash
curl -X POST http://localhost:8000/api/scoring/run \
  -H "Content-Type: application/json" \
  -d '{"party_id": 123}'
```

### Trigger Pipeline

```bash
curl -X POST http://localhost:8000/api/pipeline/trigger/full_scoring_pipeline \
  -H "Content-Type: application/json" \
  -d '{"batch_id": "BATCH_001"}'
```

### Get Party Details

```bash
curl http://localhost:8000/api/parties/123
```

### Ingest Synthetic Data

```bash
curl -X POST http://localhost:8000/api/synthetic/ingest \
  -H "Content-Type: application/json" \
  -d '{"batch_id": "BATCH_001", "file_path": "data/synthetic_profiles.json"}'
```

---

## Rate Limiting

Production deployments should implement rate limiting:

| Endpoint Type | Limit |
|--------------|-------|
| Scoring | 100 requests/minute |
| Pipeline triggers | 10 requests/minute |
| Read operations | 1000 requests/minute |

---

## Versioning

Current API version: v1 (implicit in paths)

Future versions will use explicit versioning:
- `/api/v1/scoring`
- `/api/v2/scoring`
