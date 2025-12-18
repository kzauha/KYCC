# Scorecard Versioning

The versioning system maintains multiple scorecard configurations with full audit trail.

## Overview

| Property | Value |
|----------|-------|
| Location | `backend/app/services/scorecard_version_service.py` |
| Table | scorecard_versions |
| Initial Version | v1 |
| Status States | draft, active, inactive |

---

## Version Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Version Lifecycle                               │
│                                                                     │
│   ┌────────────┐    ┌────────────┐    ┌────────────┐               │
│   │   DRAFT    │───>│   ACTIVE   │───>│  INACTIVE  │               │
│   └────────────┘    └────────────┘    └────────────┘               │
│         │                 │                  │                      │
│         │                 │                  │                      │
│   Created by:       Activated by:      Replaced by:                 │
│   - ML refinement   - Manual approval  - New version                │
│   - Manual create   - API call         - Rollback                   │
│                                                                     │
│   Can be:           Only ONE active    Can be:                      │
│   - Edited          at a time          - Reactivated               │
│   - Deleted                            - Archived                   │
│   - Activated                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Version Schema

```sql
CREATE TABLE scorecard_versions (
    id SERIAL PRIMARY KEY,
    version_id VARCHAR(50) UNIQUE NOT NULL,
    base_version VARCHAR(50),
    model_id VARCHAR(100),
    features JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activated_at TIMESTAMP,
    deactivated_at TIMESTAMP,
    created_by VARCHAR(100),
    notes TEXT
);
```

---

## Version Model

```python
class ScorecardVersion(Base):
    __tablename__ = "scorecard_versions"
    
    id = Column(Integer, primary_key=True)
    version_id = Column(String(50), unique=True, nullable=False)
    base_version = Column(String(50))
    model_id = Column(String(100))
    features = Column(JSON, nullable=False)
    status = Column(String(20), default='draft')
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime)
    deactivated_at = Column(DateTime)
    created_by = Column(String(100))
    notes = Column(Text)
```

---

## Initial Version

The initial scorecard configuration (v1):

```python
INITIAL_SCORECARD_V1 = {
    "version_id": "v1",
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
        "party_type_score": {
            "weight": 5,
            "multiplier": 1.0,
            "max_value": 10
        },
        "contact_completeness": {
            "weight": 5,
            "multiplier": 0.1,
            "max_value": 100
        },
        "has_tax_id": {
            "weight": 10,
            "multiplier": 1.0,
            "max_value": 1
        },
        "transaction_count_6m": {
            "weight": 10,
            "multiplier": 0.5,
            "max_value": 100
        },
        "avg_transaction_amount": {
            "weight": 5,
            "multiplier": 0.001,
            "max_value": 50000
        },
        "total_transaction_volume_6m": {
            "weight": 5,
            "multiplier": 0.00001,
            "max_value": 1000000
        },
        "transaction_regularity_score": {
            "weight": 10,
            "multiplier": 0.1,
            "max_value": 100
        },
        "recent_activity_flag": {
            "weight": 15,
            "multiplier": 1.0,
            "max_value": 1
        },
        "direct_counterparty_count": {
            "weight": 5,
            "multiplier": 0.5,
            "max_value": 20
        },
        "network_size": {
            "weight": 5,
            "multiplier": 0.2,
            "max_value": 50
        }
    },
    "status": "active"
}
```

---

## Version Operations

### Create Version

```python
def create_version(
    self,
    version_id: str,
    features: dict,
    base_version: str = None,
    notes: str = None
) -> dict:
    """Create a new scorecard version."""
    # Check version doesn't exist
    existing = self.db.query(ScorecardVersion).filter(
        ScorecardVersion.version_id == version_id
    ).first()
    
    if existing:
        raise ValueError(f"Version {version_id} already exists")
    
    version = ScorecardVersion(
        version_id=version_id,
        base_version=base_version,
        features=features,
        status='draft',
        notes=notes
    )
    
    self.db.add(version)
    self.db.commit()
    
    return self._version_to_dict(version)
```

### Get Version

```python
def get_version(self, version_id: str) -> dict:
    """Get scorecard version by ID."""
    version = self.db.query(ScorecardVersion).filter(
        ScorecardVersion.version_id == version_id
    ).first()
    
    if not version:
        # Return default v1 if not in database
        return INITIAL_SCORECARD_V1
    
    return self._version_to_dict(version)
```

### Get Active Version

```python
def get_active_version(self) -> dict:
    """Get currently active scorecard version."""
    version = self.db.query(ScorecardVersion).filter(
        ScorecardVersion.status == 'active'
    ).first()
    
    if not version:
        return INITIAL_SCORECARD_V1
    
    return self._version_to_dict(version)
```

### List Versions

```python
def list_versions(self, include_inactive: bool = False) -> list:
    """List all scorecard versions."""
    query = self.db.query(ScorecardVersion)
    
    if not include_inactive:
        query = query.filter(ScorecardVersion.status != 'inactive')
    
    versions = query.order_by(ScorecardVersion.created_at.desc()).all()
    
    return [self._version_to_dict(v) for v in versions]
```

### Activate Version

```python
def activate_version(self, version_id: str) -> dict:
    """Activate a scorecard version."""
    # Get version
    version = self.db.query(ScorecardVersion).filter(
        ScorecardVersion.version_id == version_id
    ).first()
    
    if not version:
        raise ValueError(f"Version {version_id} not found")
    
    if version.status == 'active':
        return self._version_to_dict(version)
    
    # Deactivate current active version
    current_active = self.db.query(ScorecardVersion).filter(
        ScorecardVersion.status == 'active'
    ).first()
    
    if current_active:
        current_active.status = 'inactive'
        current_active.deactivated_at = datetime.utcnow()
    
    # Activate new version
    version.status = 'active'
    version.activated_at = datetime.utcnow()
    
    self.db.commit()
    
    return self._version_to_dict(version)
```

### Rollback Version

```python
def rollback_to_version(self, version_id: str) -> dict:
    """Rollback to a previous version."""
    # Verify version exists and is inactive
    version = self.db.query(ScorecardVersion).filter(
        ScorecardVersion.version_id == version_id,
        ScorecardVersion.status == 'inactive'
    ).first()
    
    if not version:
        raise ValueError(f"Inactive version {version_id} not found")
    
    return self.activate_version(version_id)
```

---

## Version Comparison

```python
def compare_versions(self, version_a: str, version_b: str) -> dict:
    """Compare two scorecard versions."""
    a = self.get_version(version_a)
    b = self.get_version(version_b)
    
    features_a = a['features']
    features_b = b['features']
    
    comparison = []
    all_features = set(features_a.keys()) | set(features_b.keys())
    
    for feature in all_features:
        config_a = features_a.get(feature, {})
        config_b = features_b.get(feature, {})
        
        weight_a = config_a.get('weight', 0)
        weight_b = config_b.get('weight', 0)
        
        comparison.append({
            'feature': feature,
            'version_a': {
                'weight': weight_a,
                'multiplier': config_a.get('multiplier', 0),
                'max_value': config_a.get('max_value', 0)
            },
            'version_b': {
                'weight': weight_b,
                'multiplier': config_b.get('multiplier', 0),
                'max_value': config_b.get('max_value', 0)
            },
            'weight_change': weight_b - weight_a,
            'pct_change': ((weight_b - weight_a) / weight_a * 100) if weight_a > 0 else 0
        })
    
    return {
        'version_a': version_a,
        'version_b': version_b,
        'comparison': sorted(comparison, key=lambda x: abs(x['pct_change']), reverse=True)
    }
```

---

## API Endpoints

### List Versions

```
GET /api/scoring/versions
```

Response:
```json
{
  "versions": [
    {
      "version_id": "ml_v20240115",
      "status": "active",
      "created_at": "2024-01-15T10:30:45",
      "activated_at": "2024-01-15T14:00:00"
    },
    {
      "version_id": "v1",
      "status": "inactive",
      "created_at": "2024-01-01T00:00:00"
    }
  ]
}
```

### Get Version Details

```
GET /api/scoring/versions/{version_id}
```

### Compare Versions

```
GET /api/scoring/versions/compare?a=v1&b=ml_v20240115
```

### Activate Version

```
POST /api/scoring/versions/{version_id}/activate
```

### Rollback

```
POST /api/scoring/versions/{version_id}/rollback
```

---

## Audit Trail

Every version change is logged:

```python
class ScorecardVersionAudit(Base):
    __tablename__ = "scorecard_version_audit"
    
    id = Column(Integer, primary_key=True)
    version_id = Column(String(50))
    action = Column(String(20))  # created, activated, deactivated
    previous_state = Column(JSON)
    new_state = Column(JSON)
    changed_by = Column(String(100))
    changed_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(Text)
```

---

## Best Practices

1. **Never Edit Active**: Create new version instead of editing active
2. **Test Before Activate**: Validate draft versions thoroughly
3. **Document Changes**: Include notes explaining why changes were made
4. **Gradual Rollout**: Consider A/B testing before full activation
5. **Keep History**: Never delete inactive versions
6. **Monitor Impact**: Track score distribution after version change
