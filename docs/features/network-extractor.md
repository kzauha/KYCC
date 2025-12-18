# Network Feature Extractor

The Network Feature Extractor derives features from business relationship graphs.

## Overview

| Property | Value |
|----------|-------|
| Location | `backend/app/extractors/network_extractor.py` |
| Source Type | `RELATIONSHIPS` |
| Source Table | `relationships` |
| Features | 6 |

---

## Features Extracted

### direct_counterparty_count

Total number of direct business partners (suppliers and customers).

| Property | Value |
|----------|-------|
| Type | Count |
| Range | 0 to unlimited |
| Default | 0 |
| Confidence | 1.0 |

**Logic**:
```python
# Count downstream (customers)
downstream = db.query(Relationship).filter(
    Relationship.from_party_id == party_id
).count()

# Count upstream (suppliers)
upstream = db.query(Relationship).filter(
    Relationship.to_party_id == party_id
).count()

feature_value = float(downstream + upstream)
```

**Significance**: More direct partners indicate diversified business and lower concentration risk.

---

### network_depth_downstream

Maximum number of hops to the furthest customer in the supply chain.

| Property | Value |
|----------|-------|
| Type | Count |
| Range | 0 to max_depth (typically 5) |
| Default | 0 |
| Confidence | 0.9 |

**Logic**:
```python
downstream_network = get_downstream_network(db, party_id, max_depth=5)
max_depth = max([node['depth'] for node in downstream_network['nodes']], default=0)
feature_value = float(max_depth)
```

**Significance**: Deeper networks indicate reach and influence in the supply chain.

---

### network_size

Total unique parties connected to this party (directly or indirectly).

| Property | Value |
|----------|-------|
| Type | Count |
| Range | 0 to unlimited |
| Default | 0 |
| Confidence | 0.9 |

**Logic**:
```python
downstream_network = get_downstream_network(db, party_id, max_depth=5)
feature_value = float(len(downstream_network['nodes']))
```

**Significance**: Larger networks indicate integration into the supply chain ecosystem.

---

### supplier_count

Number of upstream suppliers.

| Property | Value |
|----------|-------|
| Type | Count |
| Range | 0 to unlimited |
| Default | 0 |
| Confidence | 1.0 |

**Logic**:
```python
feature_value = float(db.query(Relationship).filter(
    Relationship.to_party_id == party_id
).count())
```

**Significance**: Multiple suppliers reduce dependency on single sources.

---

### customer_count

Number of downstream customers.

| Property | Value |
|----------|-------|
| Type | Count |
| Range | 0 to unlimited |
| Default | 0 |
| Confidence | 1.0 |

**Logic**:
```python
feature_value = float(db.query(Relationship).filter(
    Relationship.from_party_id == party_id
).count())
```

**Significance**: Multiple customers indicate diversified revenue streams.

---

### network_balance_ratio

Ratio indicating balance between suppliers and customers.

| Property | Value |
|----------|-------|
| Type | Ratio |
| Range | 0 to 1 |
| Default | 0.5 |
| Confidence | 0.8 |

**Logic**:
```python
total = supplier_count + customer_count
if total == 0:
    feature_value = 0.5
else:
    # Ratio of smaller to larger
    smaller = min(supplier_count, customer_count)
    larger = max(supplier_count, customer_count)
    feature_value = smaller / larger if larger > 0 else 0.5
```

**Significance**: Balanced networks (ratio closer to 1) indicate stable supply chain position.

---

## Implementation

```python
class NetworkFeatureExtractor(BaseFeatureExtractor):
    """Extract features from business network"""
    
    def get_source_type(self) -> str:
        return "RELATIONSHIPS"
    
    def extract(self, party_id: int, db, as_of_date: datetime = None) -> List[FeatureExtractorResult]:
        features = []
        filter_date = as_of_date or datetime.utcnow()
        
        # Helper to apply date filter
        def filter_rel(query):
            if as_of_date:
                return query.filter(Relationship.established_date <= filter_date)
            return query
        
        # Count direct relationships
        downstream_q = db.query(Relationship).filter(
            Relationship.from_party_id == party_id
        )
        downstream = filter_rel(downstream_q).count()
        
        upstream_q = db.query(Relationship).filter(
            Relationship.to_party_id == party_id
        )
        upstream = filter_rel(upstream_q).count()
        
        # direct_counterparty_count
        features.append(FeatureExtractorResult(
            feature_name="direct_counterparty_count",
            feature_value=float(downstream + upstream),
            confidence=1.0
        ))
        
        # Network graph analysis
        try:
            network = get_downstream_network(db, party_id, max_depth=5, as_of_date=filter_date)
            max_depth = max([n['depth'] for n in network['nodes']], default=0)
            network_size = len(network['nodes'])
        except Exception:
            max_depth = 0
            network_size = 0
        
        # network_depth_downstream
        features.append(FeatureExtractorResult(
            feature_name="network_depth_downstream",
            feature_value=float(max_depth),
            confidence=0.9
        ))
        
        # network_size
        features.append(FeatureExtractorResult(
            feature_name="network_size",
            feature_value=float(network_size),
            confidence=0.9
        ))
        
        # supplier_count
        features.append(FeatureExtractorResult(
            feature_name="supplier_count",
            feature_value=float(upstream),
            confidence=1.0
        ))
        
        # customer_count
        features.append(FeatureExtractorResult(
            feature_name="customer_count",
            feature_value=float(downstream),
            confidence=1.0
        ))
        
        # network_balance_ratio
        total = upstream + downstream
        if total > 0:
            smaller = min(upstream, downstream)
            larger = max(upstream, downstream)
            balance = smaller / larger if larger > 0 else 0.5
        else:
            balance = 0.5
        
        features.append(FeatureExtractorResult(
            feature_name="network_balance_ratio",
            feature_value=balance,
            confidence=0.8
        ))
        
        return features
```

---

## Network Traversal

The `get_downstream_network` function performs recursive graph traversal:

```python
def get_downstream_network(
    db: Session, 
    party_id: int, 
    max_depth: int = 5,
    as_of_date: datetime = None
) -> dict:
    """
    Traverse downstream network from a party.
    
    Returns:
        dict with 'nodes' and 'edges' lists
    """
    visited = set()
    nodes = []
    edges = []
    
    def traverse(current_id, depth):
        if depth > max_depth or current_id in visited:
            return
        
        visited.add(current_id)
        nodes.append({'id': current_id, 'depth': depth})
        
        # Get downstream relationships
        query = db.query(Relationship).filter(
            Relationship.from_party_id == current_id
        )
        if as_of_date:
            query = query.filter(Relationship.established_date <= as_of_date)
        
        for rel in query.all():
            edges.append({'from': current_id, 'to': rel.to_party_id})
            traverse(rel.to_party_id, depth + 1)
    
    traverse(party_id, 0)
    return {'nodes': nodes, 'edges': edges}
```

---

## Usage

```python
from app.extractors.network_extractor import NetworkFeatureExtractor

extractor = NetworkFeatureExtractor()
features = extractor.extract(party_id=123, db=session)

for f in features:
    print(f"{f.feature_name}: {f.feature_value}")
```

Output:
```
direct_counterparty_count: 8.0
network_depth_downstream: 3.0
network_size: 15.0
supplier_count: 3.0
customer_count: 5.0
network_balance_ratio: 0.6
```

---

## Temporal Analysis

The extractor respects `as_of_date` for historical network analysis:

```python
# Network as it existed on January 1, 2024
features = extractor.extract(
    party_id=123,
    db=session,
    as_of_date=datetime(2024, 1, 1)
)
```

Only relationships with `established_date <= as_of_date` are included.

---

## Performance Considerations

| Factor | Impact | Mitigation |
|--------|--------|------------|
| Deep networks | Exponential traversal | max_depth limit (default: 5) |
| Large networks | Memory for visited set | Efficient set operations |
| Cyclic relationships | Infinite loops | visited set tracking |
