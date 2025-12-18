# Relationships API

The relationships API manages business connections between parties in the supply chain.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/relationships | List relationships |
| GET | /api/relationships/{id} | Get relationship details |
| POST | /api/relationships | Create relationship |
| DELETE | /api/relationships/{id} | Delete relationship |
| GET | /api/relationships/network/{party_id} | Get party network |

---

## Relationship Schema

```json
{
  "id": 1,
  "from_party_id": 123,
  "to_party_id": 456,
  "relationship_type": "supplies_to",
  "strength": 0.8,
  "established_date": "2023-01-15",
  "metadata": {
    "contract_value": 100000,
    "contract_end_date": "2025-01-15"
  },
  "created_at": "2024-01-15T10:30:45Z"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| from_party_id | integer | Yes | Source party ID |
| to_party_id | integer | Yes | Target party ID |
| relationship_type | string | Yes | Type of relationship |
| strength | float | No | Relationship strength (0-1) |
| established_date | date | No | When relationship started |
| metadata | object | No | Additional relationship data |

### Relationship Types

| Type | Direction | Description |
|------|-----------|-------------|
| supplies_to | from -> to | from supplies materials to to |
| buys_from | from <- to | from buys from to |
| distributes_for | from -> to | from distributes for to |
| manufactures_for | from -> to | from manufactures for to |

---

## GET /api/relationships

List relationships with filtering.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| party_id | integer | query | Filter by party (either direction) |
| from_party_id | integer | query | Filter by source party |
| to_party_id | integer | query | Filter by target party |
| relationship_type | string | query | Filter by type |
| page | integer | query | Page number |
| per_page | integer | query | Items per page |

### Response

```json
{
  "relationships": [
    {
      "id": 1,
      "from_party": {
        "id": 123,
        "party_name": "Acme Corp"
      },
      "to_party": {
        "id": 456,
        "party_name": "Beta Inc"
      },
      "relationship_type": "supplies_to",
      "strength": 0.8,
      "established_date": "2023-01-15"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 50
  }
}
```

### Example

```bash
curl "http://localhost:8000/api/relationships?party_id=123"
```

---

## GET /api/relationships/{id}

Get relationship details.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| id | integer | path | Relationship ID |

### Response

```json
{
  "id": 1,
  "from_party": {
    "id": 123,
    "party_name": "Acme Corp",
    "party_type": "supplier"
  },
  "to_party": {
    "id": 456,
    "party_name": "Beta Inc",
    "party_type": "manufacturer"
  },
  "relationship_type": "supplies_to",
  "strength": 0.8,
  "established_date": "2023-01-15",
  "metadata": {
    "contract_value": 100000,
    "contract_end_date": "2025-01-15"
  },
  "created_at": "2024-01-15T10:30:45Z"
}
```

---

## POST /api/relationships

Create a new relationship.

### Request

```json
{
  "from_party_id": 123,
  "to_party_id": 456,
  "relationship_type": "supplies_to",
  "strength": 0.8,
  "established_date": "2023-01-15",
  "metadata": {
    "contract_value": 100000
  }
}
```

### Response

```json
{
  "id": 2,
  "from_party_id": 123,
  "to_party_id": 456,
  "relationship_type": "supplies_to",
  "message": "Relationship created successfully"
}
```

### Example

```bash
curl -X POST http://localhost:8000/api/relationships \
  -H "Content-Type: application/json" \
  -d '{
    "from_party_id": 123,
    "to_party_id": 456,
    "relationship_type": "supplies_to"
  }'
```

---

## DELETE /api/relationships/{id}

Delete a relationship.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| id | integer | path | Relationship ID |

### Response

```json
{
  "id": 1,
  "message": "Relationship deleted successfully"
}
```

---

## GET /api/relationships/network/{party_id}

Get the full network graph for a party.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| party_id | integer | path | Central party ID |
| direction | string | query | "upstream", "downstream", or "both" |
| max_depth | integer | query | Maximum traversal depth (default: 3) |

### Response

```json
{
  "center_party": {
    "id": 123,
    "party_name": "Acme Corp",
    "party_type": "distributor"
  },
  "nodes": [
    {
      "id": 123,
      "party_name": "Acme Corp",
      "party_type": "distributor",
      "depth": 0
    },
    {
      "id": 100,
      "party_name": "Supplier A",
      "party_type": "supplier",
      "depth": 1
    },
    {
      "id": 200,
      "party_name": "Retailer B",
      "party_type": "retailer",
      "depth": 1
    },
    {
      "id": 300,
      "party_name": "Raw Materials Inc",
      "party_type": "manufacturer",
      "depth": 2
    }
  ],
  "edges": [
    {
      "from": 100,
      "to": 123,
      "relationship_type": "supplies_to",
      "strength": 0.8
    },
    {
      "from": 123,
      "to": 200,
      "relationship_type": "supplies_to",
      "strength": 0.6
    },
    {
      "from": 300,
      "to": 100,
      "relationship_type": "supplies_to",
      "strength": 0.9
    }
  ],
  "statistics": {
    "total_nodes": 4,
    "total_edges": 3,
    "upstream_count": 2,
    "downstream_count": 1,
    "max_depth_reached": 2
  }
}
```

### Example

```bash
curl "http://localhost:8000/api/relationships/network/123?direction=both&max_depth=3"
```

---

## Bulk Operations

### POST /api/relationships/bulk

Create multiple relationships:

```json
{
  "relationships": [
    {
      "from_party_id": 123,
      "to_party_id": 456,
      "relationship_type": "supplies_to"
    },
    {
      "from_party_id": 123,
      "to_party_id": 789,
      "relationship_type": "supplies_to"
    }
  ]
}
```

Response:

```json
{
  "created": 2,
  "relationship_ids": [3, 4]
}
```

---

## Network Analysis

### GET /api/relationships/analysis/{party_id}

Get network analysis metrics:

```json
{
  "party_id": 123,
  "metrics": {
    "degree_centrality": 0.45,
    "betweenness_centrality": 0.32,
    "upstream_dependency": 0.25,
    "downstream_reach": 0.60,
    "network_diversity": 0.78
  },
  "risk_factors": {
    "single_supplier_dependency": false,
    "single_customer_dependency": true,
    "isolated": false
  }
}
```

---

## Error Responses

### Relationship Not Found

```json
{
  "status": "error",
  "error": {
    "code": "RELATIONSHIP_NOT_FOUND",
    "message": "Relationship with ID 999 not found"
  }
}
```

### Invalid Parties

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_PARTIES",
    "message": "One or both parties not found",
    "details": {
      "from_party_id": 123,
      "from_party_exists": true,
      "to_party_id": 999,
      "to_party_exists": false
    }
  }
}
```

### Self-Reference

```json
{
  "status": "error",
  "error": {
    "code": "SELF_REFERENCE",
    "message": "Cannot create relationship from party to itself"
  }
}
```

### Duplicate Relationship

```json
{
  "status": "error",
  "error": {
    "code": "DUPLICATE_RELATIONSHIP",
    "message": "Relationship between parties 123 and 456 already exists"
  }
}
```
