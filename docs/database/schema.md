# Database Schema Reference

This document provides the complete SQL schema reference for KYCC.

## Table Schemas

### parties

```sql
CREATE TABLE parties (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR UNIQUE,
    batch_id VARCHAR,
    name VARCHAR NOT NULL,
    party_type VARCHAR NOT NULL,
    tax_id VARCHAR UNIQUE,
    registration_number VARCHAR,
    address TEXT,
    contact_person VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    kyc_verified INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_parties_external_id ON parties(external_id);
CREATE INDEX idx_parties_batch_id ON parties(batch_id);
CREATE INDEX idx_parties_name ON parties(name);
CREATE INDEX idx_parties_tax_id ON parties(tax_id);
```

### relationships

```sql
CREATE TABLE relationships (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR,
    from_party_id INTEGER NOT NULL REFERENCES parties(id),
    to_party_id INTEGER NOT NULL REFERENCES parties(id),
    relationship_type VARCHAR NOT NULL,
    established_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_relationships_batch_id ON relationships(batch_id);
CREATE INDEX idx_relationships_from_party ON relationships(from_party_id);
CREATE INDEX idx_relationships_to_party ON relationships(to_party_id);
```

### transactions

```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR,
    account_id INTEGER REFERENCES accounts(id),
    party_id INTEGER NOT NULL REFERENCES parties(id),
    counterparty_id INTEGER REFERENCES parties(id),
    transaction_date TIMESTAMP NOT NULL,
    amount FLOAT NOT NULL,
    transaction_type VARCHAR NOT NULL,
    reference VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_transactions_batch_id ON transactions(batch_id);
CREATE INDEX idx_transactions_party_id ON transactions(party_id);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
```

### accounts

```sql
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR,
    batch_id VARCHAR,
    party_id INTEGER NOT NULL REFERENCES parties(id),
    account_number VARCHAR NOT NULL,
    account_type VARCHAR DEFAULT 'checking',
    currency VARCHAR DEFAULT 'USD',
    balance FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_accounts_party_id ON accounts(party_id);
CREATE INDEX idx_accounts_batch_id ON accounts(batch_id);
```

### features

```sql
CREATE TABLE features (
    id SERIAL PRIMARY KEY,
    party_id INTEGER NOT NULL REFERENCES parties(id),
    feature_name VARCHAR NOT NULL,
    feature_value FLOAT,
    value_text VARCHAR,
    confidence_score FLOAT,
    computation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_to TIMESTAMP,
    source_type VARCHAR,
    source_data_id VARCHAR REFERENCES raw_data_sources(id),
    feature_version VARCHAR,
    feature_metadata JSONB
);

CREATE INDEX idx_features_feature_name ON features(feature_name);
CREATE INDEX idx_party_feature_valid ON features(party_id, feature_name, valid_to);
```

### feature_definitions

```sql
CREATE TABLE feature_definitions (
    feature_name VARCHAR PRIMARY KEY,
    category VARCHAR,
    data_type VARCHAR,
    description TEXT,
    computation_logic TEXT,
    required_sources JSONB,
    normalization_method VARCHAR,
    normalization_params JSONB,
    default_value FLOAT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### raw_data_sources

```sql
CREATE TABLE raw_data_sources (
    id VARCHAR PRIMARY KEY,
    party_id INTEGER NOT NULL REFERENCES parties(id),
    source_type VARCHAR NOT NULL,
    source_subtype VARCHAR,
    data_payload JSONB NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed INTEGER DEFAULT 0,
    processing_version VARCHAR
);
```

### score_requests

```sql
CREATE TABLE score_requests (
    id VARCHAR PRIMARY KEY,
    party_id INTEGER NOT NULL REFERENCES parties(id),
    request_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_version VARCHAR NOT NULL,
    model_type VARCHAR NOT NULL,
    features_snapshot JSONB NOT NULL,
    raw_score FLOAT,
    final_score INTEGER,
    score_band VARCHAR,
    confidence_level FLOAT,
    decision VARCHAR,
    decision_reasons JSONB,
    processing_time_ms INTEGER,
    api_client_id VARCHAR,
    scorecard_version_id INTEGER REFERENCES scorecard_versions(id)
);

CREATE INDEX idx_score_requests_timestamp ON score_requests(request_timestamp);
CREATE INDEX idx_score_requests_party ON score_requests(party_id);
```

### credit_scores

```sql
CREATE TABLE credit_scores (
    id SERIAL PRIMARY KEY,
    party_id INTEGER NOT NULL REFERENCES parties(id),
    overall_score FLOAT NOT NULL,
    payment_regularity_score FLOAT,
    transaction_volume_score FLOAT,
    kyc_score FLOAT,
    network_score FLOAT,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    score_request_id VARCHAR REFERENCES score_requests(id),
    scored_with_version VARCHAR(50) REFERENCES scorecard_versions(version)
);

CREATE INDEX idx_credit_scores_party ON credit_scores(party_id);
```

### decision_rules

```sql
CREATE TABLE decision_rules (
    rule_id VARCHAR PRIMARY KEY,
    rule_name VARCHAR NOT NULL,
    condition_expression TEXT NOT NULL,
    action VARCHAR NOT NULL,
    priority INTEGER NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### ground_truth_labels

```sql
CREATE TABLE ground_truth_labels (
    id SERIAL PRIMARY KEY,
    party_id INTEGER UNIQUE NOT NULL REFERENCES parties(id),
    will_default INTEGER NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    label_source VARCHAR(50) NOT NULL,
    label_confidence FLOAT DEFAULT 1.0,
    scorecard_version VARCHAR(20),
    scorecard_raw_score FLOAT,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    dataset_batch VARCHAR(100) NOT NULL
);

CREATE INDEX idx_labels_party ON ground_truth_labels(party_id);
CREATE INDEX idx_labels_batch ON ground_truth_labels(dataset_batch);
```

### model_registry

```sql
CREATE TABLE model_registry (
    model_version VARCHAR(50) PRIMARY KEY,
    model_type VARCHAR(50),
    model_config JSONB,
    feature_list JSONB,
    intercept FLOAT,
    normalization_method VARCHAR(50),
    training_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deployed_date TIMESTAMP,
    is_active INTEGER DEFAULT 0,
    performance_metrics JSONB,
    scaler_binary BYTEA,
    description TEXT,
    created_by VARCHAR(100)
);
```

### model_experiments

```sql
CREATE TABLE model_experiments (
    id SERIAL PRIMARY KEY,
    experiment_name VARCHAR(100) NOT NULL,
    algorithm VARCHAR(50) NOT NULL,
    hyperparameters JSONB NOT NULL,
    cv_scores JSONB NOT NULL,
    mean_cv_score FLOAT NOT NULL,
    std_cv_score FLOAT NOT NULL,
    training_time_seconds FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE INDEX idx_experiments_name ON model_experiments(experiment_name);
```

### scorecard_versions

```sql
CREATE TABLE scorecard_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) UNIQUE NOT NULL,
    version_number INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    weights JSONB NOT NULL,
    base_score INTEGER NOT NULL DEFAULT 300,
    max_score INTEGER NOT NULL DEFAULT 900,
    scaling_config JSONB,
    source VARCHAR(20) NOT NULL DEFAULT 'expert',
    ml_model_id VARCHAR(50),
    ml_auc FLOAT,
    ml_f1 FLOAT,
    training_data_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    activated_at TIMESTAMP,
    retired_at TIMESTAMP,
    archived_at TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system',
    notes TEXT
);

CREATE INDEX idx_scorecard_version ON scorecard_versions(version);
CREATE INDEX idx_scorecard_version_number ON scorecard_versions(version_number);
```

### batches

```sql
CREATE TABLE batches (
    id VARCHAR(50) PRIMARY KEY,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scored_at TIMESTAMP,
    outcomes_generated_at TIMESTAMP,
    profile_count INTEGER DEFAULT 0,
    label_count INTEGER DEFAULT 0,
    default_rate FLOAT DEFAULT 0.0
);

CREATE INDEX idx_batch_status ON batches(status);
```

### training_jobs

```sql
CREATE TABLE training_jobs (
    id VARCHAR(50) PRIMARY KEY,
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    training_data_count INTEGER DEFAULT 0,
    new_version_id INTEGER REFERENCES scorecard_versions(id)
);
```

### audit_log

```sql
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR NOT NULL,
    party_id INTEGER REFERENCES parties(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR,
    api_client_id VARCHAR,
    model_version VARCHAR,
    request_payload JSONB,
    response_payload JSONB,
    ip_address VARCHAR
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
```

---

## Common Queries

### Get Current Features for a Party

```sql
SELECT feature_name, feature_value, source_type
FROM features
WHERE party_id = :party_id
  AND valid_to IS NULL
ORDER BY feature_name;
```

### Get Active Scorecard

```sql
SELECT id, version, weights, base_score, max_score, ml_auc
FROM scorecard_versions
WHERE status = 'active'
ORDER BY id DESC
LIMIT 1;
```

### Get Score History for a Party

```sql
SELECT final_score, score_band, decision, request_timestamp, model_version
FROM score_requests
WHERE party_id = :party_id
ORDER BY request_timestamp DESC
LIMIT 10;
```

### Count Parties by Batch

```sql
SELECT batch_id, COUNT(*) as party_count
FROM parties
GROUP BY batch_id
ORDER BY batch_id;
```

### Get Default Rate by Batch

```sql
SELECT 
    dataset_batch,
    COUNT(*) as total,
    SUM(will_default) as defaults,
    ROUND(100.0 * SUM(will_default) / COUNT(*), 2) as default_rate
FROM ground_truth_labels
GROUP BY dataset_batch;
```

### Get Feature Statistics

```sql
SELECT 
    feature_name,
    COUNT(*) as count,
    AVG(feature_value) as mean,
    MIN(feature_value) as min,
    MAX(feature_value) as max
FROM features
WHERE valid_to IS NULL
GROUP BY feature_name
ORDER BY feature_name;
```

---

## Migrations

KYCC uses Alembic for database migrations.

### Create Migration

```bash
cd backend
alembic revision --autogenerate -m "description"
```

### Apply Migrations

```bash
alembic upgrade head
```

### Rollback Migration

```bash
alembic downgrade -1
```

### View Current Version

```bash
alembic current
```

---

## SQLite vs PostgreSQL

KYCC supports both PostgreSQL (primary) and SQLite (fallback).

### Feature Differences

| Feature | PostgreSQL | SQLite |
|---------|------------|--------|
| JSON columns | JSONB (native) | TEXT (serialized) |
| Enum types | Native ENUM | VARCHAR |
| Binary data | BYTEA | BLOB |
| Boolean | BOOLEAN | INTEGER (0/1) |
| Concurrent writes | Full support | Limited |

### Connection String Formats

PostgreSQL:
```
postgresql://user:password@host:port/database
```

SQLite:
```
sqlite:///path/to/database.db
```
