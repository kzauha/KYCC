# Feature Extraction Pipeline

The feature extraction pipeline transforms raw party data into numerical features suitable for credit scoring.

## Overview

Features are extracted from three data sources by specialized extractors:

| Extractor | Source Table | Features |
|-----------|--------------|----------|
| KYCFeatureExtractor | parties | kyc_verified, company_age_years, party_type_score, contact_completeness, has_tax_id |
| TransactionFeatureExtractor | transactions | transaction_count_6m, avg_transaction_amount, total_transaction_volume_6m, transaction_regularity_score, recent_activity_flag |
| NetworkFeatureExtractor | relationships | direct_counterparty_count, network_depth_downstream, network_size, supplier_count, customer_count, network_balance_ratio |

---

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                   FeaturePipelineService                            │
│                                                                     │
│   extract_all_features(party_id)                                    │
│         │                                                           │
│         ├─────────────────┬─────────────────┬─────────────────┐    │
│         │                 │                 │                 │    │
│         ▼                 ▼                 ▼                 │    │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐           │    │
│   │    KYC    │    │Transaction│    │  Network  │           │    │
│   │ Extractor │    │ Extractor │    │ Extractor │           │    │
│   └─────┬─────┘    └─────┬─────┘    └─────┬─────┘           │    │
│         │                │                │                 │    │
│         ▼                ▼                ▼                 │    │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐           │    │
│   │ Features  │    │ Features  │    │ Features  │           │    │
│   │  + meta   │    │  + meta   │    │  + meta   │           │    │
│   └─────┬─────┘    └─────┬─────┘    └─────┬─────┘           │    │
│         │                │                │                 │    │
│         └────────────────┼────────────────┘                 │    │
│                          ▼                                  │    │
│                   _store_features()                         │    │
│                          │                                  │    │
│                          ▼                                  │    │
│                   ┌─────────────┐                           │    │
│                   │  features   │                           │    │
│                   │   table     │                           │    │
│                   └─────────────┘                           │    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## FeaturePipelineService

### Location
`backend/app/services/feature_pipeline_service.py`

### Initialization

```python
class FeaturePipelineService:
    def __init__(self, db: Session):
        self.db = db
        self.extractors = [
            KYCFeatureExtractor(),
            TransactionFeatureExtractor(),
            NetworkFeatureExtractor()
        ]
        
        self.source_name_map = {
            "kyc": "KYC",
            "transaction": "TRANSACTIONS",
            "network": "RELATIONSHIPS"
        }
```

### Key Methods

#### extract_all_features

Extracts features from all sources for a single party:

```python
def extract_all_features(self, party_id: int, as_of_date: datetime = None) -> dict:
    """
    Extract features from all sources for a party.
    
    Args:
        party_id: ID of the party
        as_of_date: Optional historical date for temporal analysis
        
    Returns:
        dict with party_id, feature_count, sources, features_list
    """
```

#### run

Extracts features for all parties in a batch:

```python
def run(self, batch_id: str) -> dict:
    """
    Run feature extraction for all parties in a batch.
    
    Returns:
        dict with batch_id, processed_parties, status
    """
```

#### run_single

Extracts features from a specific source:

```python
def run_single(self, batch_id: str, source: str) -> dict:
    """
    Run extraction for a specific source type.
    
    Args:
        batch_id: Batch identifier
        source: 'kyc', 'transaction', or 'network'
    """
```

---

## Base Extractor Interface

### Location
`backend/app/extractors/base_extractor.py`

### Interface

```python
from dataclasses import dataclass, field
from typing import List, Any, Dict

@dataclass
class FeatureExtractorResult:
    feature_name: str
    feature_value: float
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseFeatureExtractor:
    def get_source_type(self) -> str:
        """Return the source type identifier (e.g., 'KYC', 'TRANSACTIONS')."""
        raise NotImplementedError
    
    def extract(
        self, 
        party_id: int, 
        db: Session, 
        as_of_date: datetime = None
    ) -> List[FeatureExtractorResult]:
        """
        Extract features for a party.
        
        Args:
            party_id: ID of the party
            db: Database session
            as_of_date: Optional date for temporal analysis
            
        Returns:
            List of FeatureExtractorResult objects
        """
        raise NotImplementedError
```

---

## Feature Storage

### Temporal Versioning

Features use `valid_from` and `valid_to` for versioning:

- `valid_to = NULL`: Current version
- `valid_to = timestamp`: Expired version

When new features are extracted:

1. Previous features with matching `source_type` are expired (`valid_to = NOW()`)
2. New features are inserted with `valid_from = NOW()`, `valid_to = NULL`

### Storage Logic

```python
def _store_features(self, party_id: int, features: list, affected_sources: List[str] = None):
    """
    Store features in database.
    
    Args:
        party_id: Party ID
        features: List of FeatureExtractorResult
        affected_sources: Source types to expire (None = all)
    """
    # Expire old features
    query = self.db.query(Feature).filter(
        Feature.party_id == party_id,
        Feature.valid_to == None
    )
    
    if affected_sources:
        query = query.filter(Feature.source_type.in_(affected_sources))
    
    query.update({"valid_to": datetime.utcnow()})
    
    # Insert new features
    for feat in features:
        feature = Feature(
            party_id=party_id,
            feature_name=feat.feature_name,
            feature_value=feat.feature_value,
            confidence_score=feat.confidence,
            source_type=feat.metadata.get("source_type"),
            feature_metadata=feat.metadata,
            valid_from=datetime.utcnow()
        )
        self.db.add(feature)
    
    self.db.commit()
```

---

## Temporal Feature Extraction

The `as_of_date` parameter enables historical analysis:

```python
# Get features as of January 1, 2024
features = pipeline.extract_all_features(
    party_id=123,
    as_of_date=datetime(2024, 1, 1)
)
```

When `as_of_date` is provided:

1. Transactions are filtered: `transaction_date <= as_of_date`
2. Relationships are filtered: `established_date <= as_of_date`
3. Company age is calculated relative to `as_of_date`
4. Features are NOT stored in database (read-only analysis)

---

## Feature List

### KYC Features

| Feature | Type | Range | Description |
|---------|------|-------|-------------|
| kyc_verified | Binary | 0-1 | Whether party passed KYC verification |
| company_age_years | Numeric | 0+ | Years since company creation |
| party_type_score | Numeric | 5-10 | Score based on party type |
| contact_completeness | Percentage | 0-100 | Percentage of contact fields filled |
| has_tax_id | Binary | 0-1 | Whether party has tax ID on file |

### Transaction Features

| Feature | Type | Range | Description |
|---------|------|-------|-------------|
| transaction_count_6m | Count | 0+ | Number of transactions in last 6 months |
| avg_transaction_amount | Currency | 0+ | Average transaction amount |
| total_transaction_volume_6m | Currency | 0+ | Total transaction volume in 6 months |
| transaction_regularity_score | Percentage | 0-100 | Consistency of monthly volumes |
| recent_activity_flag | Binary | 0-1 | Activity in last 30 days |

### Network Features

| Feature | Type | Range | Description |
|---------|------|-------|-------------|
| direct_counterparty_count | Count | 0+ | Direct business partners |
| network_depth_downstream | Count | 0+ | Maximum hops to furthest customer |
| network_size | Count | 0+ | Total unique parties in network |
| supplier_count | Count | 0+ | Number of upstream suppliers |
| customer_count | Count | 0+ | Number of downstream customers |
| network_balance_ratio | Ratio | 0-1 | Ratio of suppliers to customers |

---

## Batch Processing

For processing entire batches:

```python
# Run all extractors for a batch
pipeline = FeaturePipelineService(db)
result = pipeline.run(batch_id="BATCH_001")

# Output: {"batch_id": "BATCH_001", "processed_parties": 100, "status": "completed"}
```

Or run specific sources:

```python
# Run only KYC extraction
pipeline.run_single(batch_id="BATCH_001", source="kyc")

# Run only transaction extraction
pipeline.run_single(batch_id="BATCH_001", source="transaction")
```

---

## Error Handling

Extractors handle errors gracefully:

```python
for extractor in self.extractors:
    try:
        features = extractor.extract(party_id, self.db, as_of_date=as_of_date)
        all_features.extend(features)
    except Exception as e:
        print(f"Error extracting from {extractor.get_source_type()}: {e}")
        # Continue with other extractors
```

Failed extractions:
- Log the error
- Continue with remaining extractors
- Return partial results
