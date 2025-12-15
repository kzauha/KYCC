# Database Schema

## Overview

KYCC uses a relational database design with 14 tables organized into three logical groups:

1. **Core Supply Chain Data**: Parties, Relationships, Transactions
2. **Scoring & Features**: Features, ScoreRequests, ModelRegistry, DecisionRules
3. **Metadata & Configuration**: BatchIngestion, FeatureDefinition, etc.

## Entity Relationship Diagram

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Party     │────────▶│ Relationship │◀────────│   Party     │
│             │ from_id │              │ to_id   │             │
└─────────────┘         └──────────────┘         └─────────────┘
       │                                                 │
       │                                                 │
       │                                                 │
       ▼                                                 ▼
┌─────────────┐                                  ┌─────────────┐
│ Transaction │                                  │   Feature   │
│             │                                  │  (versioned)│
└─────────────┘                                  └─────────────┘
                                                         │
                                                         │
                                                         ▼
                                                 ┌──────────────┐
                                                 │ ScoreRequest │
                                                 │  (audit log) │
                                                 └──────────────┘
```

## Core Tables

### parties

Supply chain actors (companies).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `party_name` | VARCHAR(255) | NOT NULL | Company name |
| `party_type` | VARCHAR(50) | NOT NULL | supplier, manufacturer, etc. |
| `kyc_verified` | INTEGER | | KYC score (0-100) |
| `tax_id` | VARCHAR(50) | | Tax identification number |
| `address` | TEXT | | Physical address |
| `contact_person` | VARCHAR(100) | | Primary contact name |
| `email` | VARCHAR(100) | | Contact email |
| `phone` | VARCHAR(20) | | Contact phone |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation time |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last update time |

**Indices**:
- `idx_party_type` on `party_type`
- `idx_kyc_verified` on `kyc_verified`

---

### relationships

Supply chain connections between parties.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `from_party_id` | INTEGER | FK → parties(id) | Source party |
| `to_party_id` | INTEGER | FK → parties(id) | Destination party |
| `relationship_type` | VARCHAR(50) | NOT NULL | supplies_to, distributes_to |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Indices**:
- `idx_from_party` on `from_party_id`
- `idx_to_party` on `to_party_id`
- `idx_relationship_type` on `relationship_type`

**Constraints**:
- CHECK: `from_party_id != to_party_id` (no self-loops)

---

### transactions

Payment or shipment history between parties.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `from_party_id` | INTEGER | FK → parties(id) | Payer/shipper |
| `to_party_id` | INTEGER | FK → parties(id) | Payee/receiver |
| `amount` | DECIMAL(15,2) | NOT NULL | Transaction value |
| `transaction_date` | TIMESTAMP | NOT NULL | When transaction occurred |
| `payment_type` | VARCHAR(50) | | Cash, wire, crypto, etc. |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Indices**:
- `idx_from_party_txn` on `from_party_id`
- `idx_to_party_txn` on `to_party_id`
- `idx_transaction_date` on `transaction_date`

---

## Scoring Tables

### features

Extracted features for credit scoring (versioned for audit).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-increment ID |
| `party_id` | INTEGER | FK → parties(id) | Party being scored |
| `feature_name` | VARCHAR(100) | NOT NULL | kyc_score, transaction_count, etc. |
| `feature_value` | DECIMAL(15,4) | NOT NULL | Numerical value |
| `confidence_score` | DECIMAL(5,4) | | Extractor confidence (0-1) |
| `source_type` | VARCHAR(50) | | KYC, TRANSACTION, NETWORK |
| `computation_timestamp` | TIMESTAMP | DEFAULT NOW() | When computed |
| `valid_from` | TIMESTAMP | NOT NULL | Start of validity |
| `valid_to` | TIMESTAMP | | End of validity (NULL = current) |

**Indices**:
- `idx_feature_lookup` on `(party_id, feature_name, valid_to)`
- `idx_source_type` on `source_type`

**Temporal Queries**:
```sql
-- Current features
SELECT * FROM features
WHERE party_id = 1 AND valid_to IS NULL;

-- Historical features at specific time
SELECT * FROM features
WHERE party_id = 1
  AND valid_from <= '2025-12-01'
  AND (valid_to IS NULL OR valid_to > '2025-12-01');
```

---

### score_requests

Complete audit log of all score computations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | VARCHAR(36) | PRIMARY KEY | UUID |
| `party_id` | INTEGER | FK → parties(id) | Party scored |
| `request_timestamp` | TIMESTAMP | NOT NULL | When score computed |
| `model_version` | VARCHAR(50) | NOT NULL | Scorecard version used |
| `model_type` | VARCHAR(50) | NOT NULL | scorecard, xgboost, etc. |
| `features_snapshot` | JSON | NOT NULL | All features at scoring time |
| `raw_score` | DECIMAL(10,8) | NOT NULL | 0-1 range score |
| `final_score` | INTEGER | NOT NULL | 300-900 range score |
| `score_band` | VARCHAR(20) | NOT NULL | excellent, good, fair, poor |
| `confidence_level` | DECIMAL(5,4) | NOT NULL | Feature completeness |
| `decision` | VARCHAR(50) | NOT NULL | approve, reject, flag, review |
| `decision_reasons` | JSON | | Rule names that matched |
| `processing_time_ms` | INTEGER | | Computation latency |

**Indices**:
- `idx_score_party` on `party_id`
- `idx_score_timestamp` on `request_timestamp DESC`
- `idx_score_band` on `score_band`

---

### model_registry

Scoring model repository (versioned).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `model_version` | VARCHAR(50) | PRIMARY KEY | e.g., "default_scorecard_v1" |
| `model_type` | VARCHAR(50) | NOT NULL | scorecard, xgboost, neural_net |
| `model_config` | JSON | NOT NULL | Weights, hyperparams, etc. |
| `feature_list` | JSON | NOT NULL | Required feature names |
| `intercept` | DECIMAL(10,4) | | Scorecard intercept |
| `normalization_method` | VARCHAR(50) | | min-max, z-score, etc. |
| `training_date` | TIMESTAMP | | When model trained |
| `deployed_date` | TIMESTAMP | NOT NULL | When deployed to production |
| `is_active` | INTEGER | NOT NULL | 0=inactive, 1=active |
| `performance_metrics` | JSON | | AUC, precision, recall, etc. |
| `description` | TEXT | | Model notes |
| `created_by` | VARCHAR(100) | | Model creator |

**Constraints**:
- Only one model can have `is_active = 1` at a time

---

### decision_rules

Business rules for score-based decisions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `rule_id` | VARCHAR(50) | PRIMARY KEY | e.g., "RULE_001" |
| `rule_name` | VARCHAR(255) | NOT NULL | Descriptive name |
| `condition_expression` | TEXT | NOT NULL | Python expression |
| `action` | VARCHAR(50) | NOT NULL | approve, reject, flag, review |
| `priority` | INTEGER | NOT NULL | Lower = higher priority |
| `is_active` | INTEGER | NOT NULL | 0=disabled, 1=enabled |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | |

**Constraints**:
- UNIQUE on `priority` (no duplicate priorities)

---

## Supporting Tables

### batch_ingestion

Track bulk data imports.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `batch_id` | VARCHAR(50) | PRIMARY KEY | Unique batch identifier |
| `source_type` | VARCHAR(50) | NOT NULL | synthetic, csv, api, etc. |
| `records_processed` | INTEGER | | Count of records imported |
| `records_failed` | INTEGER | | Count of failures |
| `ingestion_timestamp` | TIMESTAMP | DEFAULT NOW() | When batch ran |
| `metadata` | JSON | | Additional batch info |

---

### feature_definitions

Metadata about available features.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `feature_name` | VARCHAR(100) | PRIMARY KEY | kyc_score, etc. |
| `feature_type` | VARCHAR(50) | NOT NULL | numeric, categorical, boolean |
| `source_type` | VARCHAR(50) | NOT NULL | KYC, TRANSACTION, NETWORK |
| `description` | TEXT | | Human-readable description |
| `min_value` | DECIMAL(15,4) | | Minimum expected value |
| `max_value` | DECIMAL(15,4) | | Maximum expected value |
| `default_weight` | DECIMAL(5,4) | | Default scorecard weight |
| `is_required` | INTEGER | NOT NULL | 0=optional, 1=required |

---

## Data Types

### party_type Values

- `supplier` - Raw material/component provider
- `manufacturer` - Goods producer
- `distributor` - Wholesale distribution
- `retailer` - Retail sales
- `customer` - End consumer

### relationship_type Values

- `supplies_to` - A supplies B
- `distributes_to` - A distributes for B
- `manufactures_for` - A manufactures for B
- `sells_to` - A sells to B

### payment_type Values

- `cash`
- `wire_transfer`
- `check`
- `crypto`
- `credit`
- `trade_credit`

### source_type Values (Features)

- `KYC` - From party compliance data
- `TRANSACTION` - From transaction history
- `NETWORK` - From relationship graph

---

## Normalization

The database follows **3NF (Third Normal Form)**:
- No transitive dependencies
- All non-key attributes depend on primary key
- Minimal data redundancy

## Constraints Summary

### Referential Integrity
- All foreign keys enforced with ON DELETE CASCADE
- Orphaned records prevented

### Check Constraints
- `kyc_verified` between 0-100
- `final_score` between 300-900
- `confidence_level` between 0-1
- `amount` must be positive

### Unique Constraints
- `decision_rules.priority` must be unique
- `model_registry.is_active = 1` (only one active model)

---

## Backup & Maintenance

### Backup Strategy
```sql
-- Daily full backup
pg_dump kycc_db > backup_$(date +%Y%m%d).sql

-- Point-in-time recovery enabled (WAL archiving)
```

### Vacuum & Analyze
```sql
-- Weekly vacuum
VACUUM ANALYZE parties;
VACUUM ANALYZE features;
VACUUM ANALYZE score_requests;
```

### Index Maintenance
```sql
-- Reindex when fragmented
REINDEX TABLE features;
REINDEX TABLE score_requests;
```

---

## Performance Tuning

### Partitioning
For high-volume tables, consider partitioning:
- `score_requests` by `request_timestamp` (monthly)
- `transactions` by `transaction_date` (yearly)

### Connection Pooling
SQLAlchemy pool settings:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30
)
```

### Query Optimization
- Use covering indices for common queries
- Avoid SELECT * (specify columns)
- Use EXPLAIN ANALYZE for slow queries

---

## Migrations

Use Alembic for schema changes:
```bash
# Create migration
alembic revision --autogenerate -m "Add column xyz"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```
