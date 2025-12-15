# Parties API

Manage supply chain parties (companies) including suppliers, manufacturers, distributors, and retailers.

## Endpoints

### Create Party

```http
POST /api/parties/
```

Create a new party in the system.

**Request Body**:
```json
{
  "party_name": "ACME Suppliers Inc",
  "party_type": "supplier",
  "kyc_verified": 85,
  "tax_id": "12-3456789",
  "address": "123 Main St, City, State 12345",
  "contact_person": "John Doe",
  "email": "john@acme.com",
  "phone": "+1-555-0100"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "party_name": "ACME Suppliers Inc",
  "party_type": "supplier",
  "kyc_verified": 85,
  "created_at": "2025-12-15T10:30:00Z",
  "updated_at": "2025-12-15T10:30:00Z"
}
```

---

### List Parties

```http
GET /api/parties?skip=0&limit=100&party_type=supplier
```

Retrieve a list of parties with optional filtering.

**Query Parameters**:
- `skip` (int): Records to skip for pagination (default: 0)
- `limit` (int): Maximum records to return (default: 100)
- `party_type` (string): Filter by type: `supplier`, `manufacturer`, `distributor`, `retailer`, `customer`

**Response** (200 OK):
```json
[
  {
    "id": 1,
    "party_name": "ACME Suppliers Inc",
    "party_type": "supplier",
    "kyc_verified": 85,
    "created_at": "2025-12-15T10:30:00Z"
  },
  {
    "id": 2,
    "party_name": "Global Manufacturing Co",
    "party_type": "manufacturer",
    "kyc_verified": 92,
    "created_at": "2025-12-14T08:15:00Z"
  }
]
```

---

### Get Party by ID

```http
GET /api/parties/{party_id}
```

Retrieve a single party by ID.

**Path Parameters**:
- `party_id` (int): The party ID

**Response** (200 OK):
```json
{
  "id": 1,
  "party_name": "ACME Suppliers Inc",
  "party_type": "supplier",
  "kyc_verified": 85,
  "tax_id": "12-3456789",
  "address": "123 Main St, City, State 12345",
  "contact_person": "John Doe",
  "email": "john@acme.com",
  "phone": "+1-555-0100",
  "created_at": "2025-12-15T10:30:00Z",
  "updated_at": "2025-12-15T10:30:00Z"
}
```

**Error** (404 Not Found):
```json
{
  "detail": "Party not found"
}
```

---

### Update Party

```http
PUT /api/parties/{party_id}
```

Update an existing party.

**Path Parameters**:
- `party_id` (int): The party ID

**Request Body**:
```json
{
  "party_name": "ACME Suppliers Inc (Updated)",
  "kyc_verified": 90,
  "email": "newemail@acme.com"
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "party_name": "ACME Suppliers Inc (Updated)",
  "kyc_verified": 90,
  "email": "newemail@acme.com",
  "updated_at": "2025-12-15T11:00:00Z"
}
```

---

### Delete Party

```http
DELETE /api/parties/{party_id}
```

Delete a party from the system.

**Path Parameters**:
- `party_id` (int): The party ID

**Response** (204 No Content)

---

### Get Party Network

```http
GET /api/parties/{party_id}/network
```

Retrieve the full supply chain network for a party (upstream and downstream).

**Path Parameters**:
- `party_id` (int): The party ID

**Response** (200 OK):
```json
{
  "party_id": 1,
  "party_name": "ACME Suppliers Inc",
  "upstream": [
    {
      "id": 5,
      "party_name": "Raw Materials Corp",
      "relationship_type": "supplies_to"
    }
  ],
  "downstream": [
    {
      "id": 2,
      "party_name": "Global Manufacturing Co",
      "relationship_type": "supplies_to"
    }
  ],
  "network_size": 3,
  "network_depth": 2
}
```

---

### Get Party Counterparties

```http
GET /api/parties/{party_id}/counterparties
```

Retrieve direct counterparties (suppliers and customers) for a party.

**Path Parameters**:
- `party_id` (int): The party ID

**Response** (200 OK):
```json
{
  "party_id": 1,
  "suppliers": [
    {
      "id": 5,
      "party_name": "Raw Materials Corp",
      "relationship_type": "supplies_to"
    }
  ],
  "customers": [
    {
      "id": 2,
      "party_name": "Global Manufacturing Co",
      "relationship_type": "supplies_to"
    }
  ],
  "total_suppliers": 1,
  "total_customers": 1
}
```

---

## Party Types

Valid `party_type` values:

| Type | Description |
|------|-------------|
| `supplier` | Provides raw materials or components |
| `manufacturer` | Produces finished goods |
| `distributor` | Handles wholesale distribution |
| `retailer` | Sells to end consumers |
| `customer` | End customer or buyer |

## KYC Score

`kyc_verified` is an integer between 0-100 representing:
- **0-39**: Poor compliance (high risk)
- **40-69**: Fair compliance (medium risk)
- **70-89**: Good compliance (low risk)
- **90-100**: Excellent compliance (very low risk)

## Validation Rules

- `party_name`: Required, 2-255 characters
- `party_type`: Required, must be one of valid types
- `kyc_verified`: Optional, 0-100 integer
- `email`: Optional, valid email format
- `tax_id`: Optional, string

## Examples

### Create a Supplier

```python
import requests

party = {
    "party_name": "Tech Components Ltd",
    "party_type": "supplier",
    "kyc_verified": 88,
    "email": "contact@techcomponents.com"
}

response = requests.post(
    "http://localhost:8000/api/parties/",
    json=party
)
print(response.json())
```

### Filter High-KYC Suppliers

```python
response = requests.get(
    "http://localhost:8000/api/parties",
    params={"party_type": "supplier", "limit": 50}
)
parties = response.json()
high_kyc = [p for p in parties if p["kyc_verified"] >= 80]
```

### Update Party KYC Score

```python
response = requests.put(
    "http://localhost:8000/api/parties/1",
    json={"kyc_verified": 95}
)
```
