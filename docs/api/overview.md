# API Overview

## Base URL

**Local Development**: `http://localhost:8000`

**API Documentation**:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Routers

KYCC exposes 23 endpoints across 5 routers:

| Router | Base Path | Purpose | Endpoints |
|--------|-----------|---------|-----------|
| Parties | `/api/parties` | Party CRUD operations | 7 |
| Relationships | `/api/relationships` | Relationship management | 3 |
| Scoring | `/api/scoring` | Credit score computation | 5 |
| Scoring V2 | `/api/v2/scoring` | Enhanced scoring with caching | 3 |
| Synthetic | `/api/synthetic` | Test data generation | 5 |

## Authentication

Currently no authentication required (development mode). Production should implement:
- OAuth2 with JWT tokens
- API key-based authentication
- Rate limiting per client

## Request/Response Format

All requests and responses use `Content-Type: application/json`.

### Success Response
```json
{
  "id": 1,
  "party_name": "ACME Corp",
  "status": "success"
}
```

### Error Response
```json
{
  "detail": "Party not found",
  "status_code": 404
}
```

## Common HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful GET/PUT request |
| 201 | Created | Successful POST (resource created) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input data |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 500 | Internal Server Error | Server-side error |

## Pagination

List endpoints support pagination:

```http
GET /api/parties?skip=0&limit=10
```

**Parameters**:
- `skip` (int): Number of records to skip (default: 0)
- `limit` (int): Maximum records to return (default: 100, max: 1000)

## Filtering

Some endpoints support query parameters:

```http
GET /api/parties?party_type=supplier&kyc_verified__gte=80
```

## Rate Limiting

Not currently implemented. Recommended for production:
- 100 requests per minute per IP
- 1000 requests per hour per API key

## CORS Configuration

CORS is enabled for local development:
- Allowed origins: `http://localhost:5173`, `http://localhost:3000`
- Allowed methods: GET, POST, PUT, DELETE, PATCH
- Allowed headers: `*`

## Endpoints by Category

### Party Management
- [Parties API](parties.md) - CRUD for supply chain companies

### Credit Scoring
- [Scoring API](scoring.md) - Compute credit scores

### Testing & Development
- Synthetic API - Generate test data (see Swagger UI at `/docs`)
- Health Check - System health monitoring (see `/health` endpoint)

## API Versioning

Current version: `v1` (implicit)

Future versions will use explicit URL versioning:
- `/api/v1/parties`
- `/api/v2/parties`

## WebSockets

Not currently implemented. Planned for:
- Real-time score updates
- Live transaction monitoring
- Network graph streaming

## GraphQL

Not currently implemented. REST API is preferred for now.

## SDKs & Client Libraries

### Python
```python
import requests

response = requests.get("http://localhost:8000/api/parties/1")
party = response.json()
```

### JavaScript
```javascript
const response = await fetch('http://localhost:8000/api/parties/1');
const party = await response.json();
```

### cURL
```bash
curl -X GET "http://localhost:8000/api/parties/1" \
  -H "Content-Type: application/json"
```

## API Testing

Use the interactive Swagger UI at `/docs` to:
- Explore endpoints
- Test requests
- View response schemas
- Generate code snippets

## Next Steps

- [Parties API Reference](parties.md)
- [Scoring API Reference](scoring.md)
- [Interactive API Documentation](http://localhost:8000/docs) - Swagger UI
