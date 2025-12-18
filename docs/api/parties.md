# Parties API

The parties API manages supply chain participants in the credit scoring system.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/parties | List all parties |
| GET | /api/parties/{id} | Get party details |
| POST | /api/parties | Create a party |
| PUT | /api/parties/{id} | Update a party |
| DELETE | /api/parties/{id} | Delete a party |

---

## Party Schema

```json
{
  "id": 123,
  "party_name": "Acme Corporation",
  "party_type": "supplier",
  "kyc_verified": true,
  "contact_person": "John Smith",
  "email": "john@acme.com",
  "phone": "+1-555-0123",
  "address": "123 Main St, City, State 12345",
  "tax_id": "12-3456789",
  "batch_id": "BATCH_001",
  "created_at": "2024-01-15T10:30:45Z",
  "updated_at": "2024-01-15T10:30:45Z"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| party_name | string | Yes | Company or individual name |
| party_type | string | Yes | Role in supply chain |
| kyc_verified | boolean | No | KYC verification status |
| contact_person | string | No | Primary contact name |
| email | string | No | Contact email |
| phone | string | No | Contact phone |
| address | string | No | Business address |
| tax_id | string | No | Tax identification number |
| batch_id | string | No | Import batch identifier |

### Party Types

| Type | Description |
|------|-------------|
| manufacturer | Produces goods |
| distributor | Distributes goods |
| supplier | Supplies materials |
| retailer | Sells to consumers |
| customer | End customer |

---

## GET /api/parties

List all parties with filtering and pagination.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| party_type | string | query | Filter by party type |
| batch_id | string | query | Filter by batch |
| kyc_verified | boolean | query | Filter by KYC status |
| search | string | query | Search in party_name |
| page | integer | query | Page number (default: 1) |
| per_page | integer | query | Items per page (default: 20) |

### Response

```json
{
  "parties": [
    {
      "id": 123,
      "party_name": "Acme Corporation",
      "party_type": "supplier",
      "kyc_verified": true,
      "batch_id": "BATCH_001",
      "latest_score": 720
    },
    {
      "id": 124,
      "party_name": "Beta Industries",
      "party_type": "manufacturer",
      "kyc_verified": true,
      "batch_id": "BATCH_001",
      "latest_score": 680
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

### Example

```bash
curl "http://localhost:8000/api/parties?party_type=supplier&kyc_verified=true"
```

---

## GET /api/parties/{id}

Get detailed information about a party.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| id | integer | path | Party ID |
| include_features | boolean | query | Include extracted features |
| include_scores | boolean | query | Include score history |
| include_relationships | boolean | query | Include relationships |

### Response

```json
{
  "id": 123,
  "party_name": "Acme Corporation",
  "party_type": "supplier",
  "kyc_verified": true,
  "contact_person": "John Smith",
  "email": "john@acme.com",
  "phone": "+1-555-0123",
  "address": "123 Main St, City, State 12345",
  "tax_id": "12-3456789",
  "batch_id": "BATCH_001",
  "created_at": "2024-01-15T10:30:45Z",
  "updated_at": "2024-01-15T10:30:45Z",
  "features": {
    "kyc_verified": 1.0,
    "company_age_years": 5.2,
    "transaction_count_6m": 45,
    "avg_transaction_amount": 5250.50,
    "network_size": 12
  },
  "latest_score": {
    "total_score": 720,
    "band": "good",
    "computed_at": "2024-01-15T10:30:45Z"
  },
  "relationships": {
    "suppliers": [
      {"id": 200, "party_name": "Raw Materials Inc"}
    ],
    "customers": [
      {"id": 300, "party_name": "Retail Chain Co"}
    ]
  }
}
```

### Example

```bash
curl "http://localhost:8000/api/parties/123?include_features=true&include_scores=true"
```

---

## POST /api/parties

Create a new party.

### Request

```json
{
  "party_name": "New Company Inc",
  "party_type": "distributor",
  "kyc_verified": false,
  "contact_person": "Jane Doe",
  "email": "jane@newcompany.com",
  "phone": "+1-555-9876",
  "address": "456 Business Ave, City, State 54321",
  "tax_id": "98-7654321",
  "batch_id": "MANUAL_001"
}
```

### Response

```json
{
  "id": 125,
  "party_name": "New Company Inc",
  "party_type": "distributor",
  "kyc_verified": false,
  "created_at": "2024-01-15T11:00:00Z",
  "message": "Party created successfully"
}
```

### Example

```bash
curl -X POST http://localhost:8000/api/parties \
  -H "Content-Type: application/json" \
  -d '{
    "party_name": "New Company Inc",
    "party_type": "distributor",
    "contact_person": "Jane Doe",
    "email": "jane@newcompany.com"
  }'
```

---

## PUT /api/parties/{id}

Update an existing party.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| id | integer | path | Party ID |

### Request

```json
{
  "kyc_verified": true,
  "email": "updated@company.com",
  "phone": "+1-555-1111"
}
```

### Response

```json
{
  "id": 123,
  "party_name": "Acme Corporation",
  "kyc_verified": true,
  "email": "updated@company.com",
  "phone": "+1-555-1111",
  "updated_at": "2024-01-15T12:00:00Z",
  "message": "Party updated successfully"
}
```

### Example

```bash
curl -X PUT http://localhost:8000/api/parties/123 \
  -H "Content-Type: application/json" \
  -d '{"kyc_verified": true}'
```

---

## DELETE /api/parties/{id}

Delete a party.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| id | integer | path | Party ID |
| cascade | boolean | query | Delete related records |

### Response

```json
{
  "id": 123,
  "message": "Party deleted successfully",
  "related_deleted": {
    "features": 16,
    "scores": 5,
    "relationships": 3
  }
}
```

### Example

```bash
curl -X DELETE "http://localhost:8000/api/parties/123?cascade=true"
```

---

## Batch Operations

### POST /api/parties/bulk

Create multiple parties:

```json
{
  "parties": [
    {"party_name": "Company A", "party_type": "supplier"},
    {"party_name": "Company B", "party_type": "manufacturer"}
  ],
  "batch_id": "BULK_001"
}
```

Response:

```json
{
  "created": 2,
  "batch_id": "BULK_001",
  "party_ids": [126, 127]
}
```

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

### Validation Error

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid party data",
    "details": {
      "party_type": "Invalid party type. Must be one of: manufacturer, distributor, supplier, retailer, customer"
    }
  }
}
```

### Duplicate Party

```json
{
  "status": "error",
  "error": {
    "code": "DUPLICATE_PARTY",
    "message": "Party with name 'Acme Corporation' already exists in batch BATCH_001"
  }
}
```
