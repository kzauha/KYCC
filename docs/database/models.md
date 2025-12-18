# Database Models

This document provides a comprehensive reference for all database models in KYCC.

## Model Overview

KYCC uses 17 database tables organized into functional groups:

| Group | Tables | Purpose |
|-------|--------|---------|
| Core Entities | Party, Relationship, Transaction, Account | Supply chain data |
| Feature Store | Feature, FeatureDefinition, RawDataSource | Computed features |
| Scoring | ScoreRequest, CreditScore, DecisionRule | Score computation |
| ML Pipeline | GroundTruthLabel, ModelRegistry, ModelExperiment | Machine learning |
| Versioning | ScorecardVersion, Batch, TrainingJob | Version management |
| Audit | AuditLog | Audit trail |

---

## Core Entities

### Party

The central entity representing companies or individuals in the supply chain.

```python
class Party(Base):
    __tablename__ = "parties"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, unique=True, index=True)
    batch_id = Column(String, index=True)
    name = Column(String, nullable=False, index=True)
    party_type = Column(String, nullable=False)  # supplier, manufacturer, etc.
    tax_id = Column(String, unique=True, index=True)
    registration_number = Column(String)
    address = Column(Text)
    contact_person = Column(String)
    email = Column(String)
    phone = Column(String)
    kyc_verified = Column(Integer, default=0)  # 0 or 1
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Party Types**:

- `supplier`
- `manufacturer`
- `distributor`
- `retailer`
- `customer`
- `individual`
- `business`

### Relationship

Models business connections between parties.

```python
class Relationship(Base):
    __tablename__ = "relationships"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, index=True)
    from_party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    to_party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    relationship_type = Column(Enum(RelationshipType), nullable=False)
    established_date = Column(DateTime, default=datetime.utcnow)
```

**Relationship Types**:

- `supplies_to`
- `manufactures_for`
- `distributes_for`
- `sells_to`

### Transaction

Records financial activity between parties.

```python
class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    counterparty_id = Column(Integer, ForeignKey("parties.id"))
    transaction_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    reference = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Transaction Types**:

- `invoice`
- `payment`
- `credit_note`

### Account

Bank accounts tied to parties.

```python
class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, index=True)
    batch_id = Column(String, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    account_number = Column(String, nullable=False)
    account_type = Column(String, default="checking")
    currency = Column(String, default="USD")
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## Feature Store

### Feature

Stores computed features with temporal versioning.

```python
class Feature(Base):
    __tablename__ = "features"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    feature_name = Column(String, nullable=False, index=True)
    feature_value = Column(Float)
    value_text = Column(String)  # For categorical features
    confidence_score = Column(Float)  # 0.0-1.0
    computation_timestamp = Column(DateTime, default=datetime.utcnow)
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_to = Column(DateTime, nullable=True)  # NULL = current version
    source_type = Column(String)  # KYC, TRANSACTIONS, RELATIONSHIPS
    source_data_id = Column(String, ForeignKey("raw_data_sources.id"))
    feature_version = Column(String)
    feature_metadata = Column(JSON)
```

**Key Index**: `idx_party_feature_valid` on `(party_id, feature_name, valid_to)`

**Temporal Querying**:

- Current features: `WHERE valid_to IS NULL`
- Historical features: `WHERE valid_from <= date AND (valid_to IS NULL OR valid_to > date)`

### FeatureDefinition

Metadata about each feature type.

```python
class FeatureDefinition(Base):
    __tablename__ = "feature_definitions"
    
    feature_name = Column(String, primary_key=True)
    category = Column(String)  # stability, income, behavior
    data_type = Column(String)  # numeric, categorical, boolean
    description = Column(Text)
    computation_logic = Column(Text)
    required_sources = Column(JSON)  # ['KYC', 'TRANSACTIONS']
    normalization_method = Column(String)  # min_max, z_score
    normalization_params = Column(JSON)  # {min: 0, max: 100}
    default_value = Column(Float)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### RawDataSource

Stores raw data snapshots for reprocessing.

```python
class RawDataSource(Base):
    __tablename__ = "raw_data_sources"
    
    id = Column(String, primary_key=True)  # UUID
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    source_type = Column(String, nullable=False)  # KYC, TRANSACTIONS
    source_subtype = Column(String)
    data_payload = Column(JSON, nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)
    processing_version = Column(String)
```

---

## Scoring Models

### ScoreRequest

Audit log of all scoring computations.

```python
class ScoreRequest(Base):
    __tablename__ = "score_requests"
    
    id = Column(String, primary_key=True)  # UUID
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    request_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    model_version = Column(String, nullable=False)
    model_type = Column(String, nullable=False)  # scorecard, ml_model
    features_snapshot = Column(JSON, nullable=False)
    raw_score = Column(Float)
    final_score = Column(Integer)  # 300-900
    score_band = Column(String)  # excellent, good, fair, poor
    confidence_level = Column(Float)
    decision = Column(String)  # approved, rejected, manual_review
    decision_reasons = Column(JSON)
    processing_time_ms = Column(Integer)
    api_client_id = Column(String)
    scorecard_version_id = Column(Integer, ForeignKey("scorecard_versions.id"))
```

### CreditScore

Stores computed credit scores (legacy compatibility).

```python
class CreditScore(Base):
    __tablename__ = "credit_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    overall_score = Column(Float, nullable=False)
    payment_regularity_score = Column(Float)
    transaction_volume_score = Column(Float)
    kyc_score = Column(Float)
    network_score = Column(Float)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    score_request_id = Column(String, ForeignKey("score_requests.id"))
    scored_with_version = Column(String(50), ForeignKey("scorecard_versions.version"))
```

### DecisionRule

Business rules for credit decisions.

```python
class DecisionRule(Base):
    __tablename__ = "decision_rules"
    
    rule_id = Column(String, primary_key=True)
    rule_name = Column(String, nullable=False)
    condition_expression = Column(Text, nullable=False)
    action = Column(String, nullable=False)  # reject, flag, manual_review
    priority = Column(Integer, nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## ML Pipeline Models

### GroundTruthLabel

Ground truth labels for training data.

```python
class GroundTruthLabel(Base):
    __tablename__ = "ground_truth_labels"
    
    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), unique=True, nullable=False)
    will_default = Column(Integer, nullable=False)  # 0 or 1
    risk_level = Column(String(20), nullable=False)  # high, medium, low
    label_source = Column(String(50), nullable=False)  # scorecard, observed, mixed
    label_confidence = Column(Float, default=1.0)
    scorecard_version = Column(String(20), nullable=True)
    scorecard_raw_score = Column(Float, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    dataset_batch = Column(String(100), nullable=False, index=True)
```

### ModelRegistry

Registry of trained ML models.

```python
class ModelRegistry(Base):
    __tablename__ = "model_registry"
    
    model_version = Column(String(50), primary_key=True)
    model_type = Column(String(50))  # scorecard, ml_model
    model_config = Column(JSON)  # weights, intercept, hyperparams
    feature_list = Column(JSON)  # list of feature names
    intercept = Column(Float)
    normalization_method = Column(String(50))
    training_date = Column(DateTime, default=datetime.utcnow)
    deployed_date = Column(DateTime)
    is_active = Column(Integer, default=0)
    performance_metrics = Column(JSON)  # auc, precision, recall, f1
    scaler_binary = Column(LargeBinary)  # Serialized scaler
    description = Column(Text)
    created_by = Column(String(100))
```

### ModelExperiment

Hyperparameter tuning experiments.

```python
class ModelExperiment(Base):
    __tablename__ = "model_experiments"
    
    id = Column(Integer, primary_key=True, index=True)
    experiment_name = Column(String(100), nullable=False, index=True)
    algorithm = Column(String(50), nullable=False)
    hyperparameters = Column(JSON, nullable=False)
    cv_scores = Column(JSON, nullable=False)
    mean_cv_score = Column(Float, nullable=False)
    std_cv_score = Column(Float, nullable=False)
    training_time_seconds = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
```

---

## Version Management

### ScorecardVersion

Versioned scorecard storage.

```python
class ScorecardVersion(Base):
    __tablename__ = "scorecard_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(20), unique=True, nullable=False, index=True)
    version_number = Column(Integer, index=True)
    status = Column(String(20), nullable=False, default='active')  # active, archived, failed
    weights = Column(JSON, nullable=False)
    base_score = Column(Integer, nullable=False, default=300)
    max_score = Column(Integer, nullable=False, default=900)
    scaling_config = Column(JSON)
    source = Column(String(20), nullable=False, default='expert')  # expert, ml_refined
    ml_model_id = Column(String(50))
    ml_auc = Column(Float)
    ml_f1 = Column(Float)
    training_data_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime)
    retired_at = Column(DateTime)
    archived_at = Column(DateTime)
    created_by = Column(String(100), default='system')
    notes = Column(Text)
```

### Batch

Tracks lifecycle of data batches.

```python
class Batch(Base):
    __tablename__ = "batches"
    
    id = Column(String(50), primary_key=True, index=True)
    status = Column(String(50), nullable=False)  # ingested, scored, outcomes_generated
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    scored_at = Column(DateTime)
    outcomes_generated_at = Column(DateTime)
    profile_count = Column(Integer, default=0)
    label_count = Column(Integer, default=0)
    default_rate = Column(Float, default=0.0)
```

### TrainingJob

Tracks ML training jobs.

```python
class TrainingJob(Base):
    __tablename__ = "training_jobs"
    
    id = Column(String(50), primary_key=True)
    status = Column(String(50), nullable=False)  # running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    training_data_count = Column(Integer, default=0)
    new_version_id = Column(Integer, ForeignKey("scorecard_versions.id"))
```

---

## Audit

### AuditLog

Audit trail for all operations.

```python
class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    party_id = Column(Integer, ForeignKey("parties.id"))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String)
    api_client_id = Column(String)
    model_version = Column(String)
    request_payload = Column(JSON)
    response_payload = Column(JSON)
    ip_address = Column(String)
```

---

## Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│   Party     │───────│  Relationship   │───────│   Party     │
│             │  1:N  │                 │  N:1  │             │
└──────┬──────┘       └─────────────────┘       └─────────────┘
       │
       │ 1:N
       ▼
┌─────────────┐       ┌─────────────────┐
│ Transaction │───────│    Account      │
│             │  N:1  │                 │
└──────┬──────┘       └─────────────────┘
       │
       │ (via party_id)
       ▼
┌─────────────┐       ┌─────────────────┐       ┌───────────────────┐
│  Feature    │       │ GroundTruthLabel│       │   ScoreRequest    │
│             │       │                 │       │                   │
└─────────────┘       └─────────────────┘       └─────────┬─────────┘
                                                          │
                                                          │ N:1
                                                          ▼
                                               ┌───────────────────┐
                                               │ ScorecardVersion  │
                                               │                   │
                                               └───────────────────┘
```
