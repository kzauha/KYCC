# KYCC — Know Your Customer's Customer

## Overview

**KYCC** is an enterprise-grade supply chain intelligence and credit scoring platform. It models companies (parties), their relationships, transactions, and automatically computes creditworthiness scores using a feature-based scorecard model.

### What the System Does

1. **Stores supply chain data**: Parties (suppliers, manufacturers, distributors, retailers), relationships between them, and transaction history
2. **Extracts features**: Automatically derives meaningful financial and network signals from raw data (KYC scores, transaction counts, network depth, etc.)
3. **Computes credit scores**: Applies a weighted scorecard model to produce 300-900 credit scores (FICO-like standard)
4. **Applies business rules**: Enforces decision rules (approve/reject/flag/manual review) based on scores and features
5. **Audits everything**: Logs all scoring requests with full feature snapshots for complete explainability and compliance

### Key Technologies

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | FastAPI + Python 3.11 | REST API with 23 endpoints, async, auto-generated docs |
| Database | PostgreSQL 15 + SQLAlchemy 2.x | Relational data, ORM, temporal features, JSON support |
| Validation | Pydantic v2 | Type-safe API schemas, ORM integration |
| Frontend | React + Vite | Interactive web UI, visualizations with Recharts/ReactFlow |
| Test Data | Synthetic Generator | Risk-based B2B supply chain profiles (Python script) |
| Currency | NRS (Nepalese Rupees) | All monetary values in NPR |

### Tech Stack Rationale

- **FastAPI**: Type hints, async support, auto-generated OpenAPI docs, integration with Pydantic
- **SQLAlchemy 2.x**: Modern async support, clear ORM relationships, session management, query builder
- **PostgreSQL**: Native JSON support (for feature snapshots), recursive CTEs (for graph traversal), ACID guarantees
- **Pydantic v2**: Strict validation, ORM mode for automatic conversion, field aliases and custom namespaces
- **React + Vite**: Fast dev server, component-based UI, Recharts/ReactFlow for visualizations
- **simpleeval**: Safe expression evaluation for business rules (no `eval()` security risks)

### Currency & Localization

- **Primary Currency**: NRS (Nepalese Rupees)
- **Supported Formats**: NPR 1,000.00 (thousands separator)
- All monetary amounts stored as FLOAT in database
- Currency field stored as VARCHAR(3) for multi-currency support

---

## Quickstart (Docker-first)

1) Copy envs:
  - `backend/.env.example` → `backend/.env`
  - `frontend/.env.example` → `frontend/.env` and set `VITE_API_BASE_URL=http://localhost:8000/api`
2) Start stack (backend + Postgres):
  ```powershell
  docker compose up -d
  ```
  - API: http://localhost:8000/docs
  - DB: localhost:5433 (creds from backend/.env)
3) Frontend (dev):
  ```powershell
  cd frontend
  npm install
  npm run dev
  ```
  App: http://localhost:5173 (calls API at http://localhost:8000/api)

## Optional: Run backend on host (venv)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
docker compose up -d postgres   # start DB only
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- Host uses `DATABASE_URL` from backend/.env (localhost:5433). If Postgres is unreachable and allowed, it can fall back to SQLite (`DEV_DATABASE_URL`).

## Database & migrations
- Compose DB data persists in the `kycc_pgdata` named volume.
- Health check: `docker compose exec postgres pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`
- Migrations (host venv or inside backend container exec):
  ```powershell
  cd backend
  alembic revision --autogenerate -m "desc"
  alembic upgrade head
  ```

---

## System Architecture

### High-Level Data Flow

```
User Request (Frontend or API)
        ↓
┌─────────────────────────────────────┐
│  FastAPI REST API (main.py)         │
│  - 23 routes across 3 routers       │
│  - CORS enabled for localhost       │
│  - Pydantic validation              │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│  Scoring Service                    │
│  (app/services/scoring_service.py)  │
│  1. Trigger feature extraction      │
│  2. Fetch scoring model             │
│  3. Apply scorecard algorithm       │
│  4. Apply decision rules            │
│  5. Generate audit log              │
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│  Feature Pipeline Service           │
│  (app/services/feature_pipeline...) │
│  Orchestrates 3 extractors:         │
│  - KYC Extractor (Party table)      │
│  - Transaction Extractor (Txn hist) │
│  - Network Extractor (Relationships)│
└─────────────────────────────────────┘
        ↓
┌─────────────────────────────────────┐
│  SQLAlchemy ORM Layer               │
│  - Reads: Party, Transaction, Rel.  │
│  - Writes: features, score_requests │
│  - Session management + pooling     │
└─────────────────────────────────────┘
        ↓
PostgreSQL 15 (Primary) or SQLite (Fallback)
        ↓
Response → Serialized JSON → Frontend Display
```

### Component Interaction Map

| Component | Depends On | Provides | When Called |
|-----------|-----------|----------|-------------|
| FastAPI Router | Database, Scoring Service | HTTP JSON response | Client calls `/api/scoring/score/{id}` |
| Scoring Service | Feature Pipeline, Model Registry, Decision Rules | Credit score + decision + audit log | Router calls `compute_score(party_id)` |
| Feature Pipeline | 3 Extractors, Database | Feature dictionary | Scoring Service calls `_ensure_features_exist()` |
| KYC Extractor | Party table | `{kyc_score, company_age_days, party_type_encoded, ...}` | Pipeline calls `.extract(party_id, db)` |
| Transaction Extractor | Transaction table | `{transaction_count, avg_amount, regularity, recency}` | Pipeline calls `.extract(party_id, db)` |
| Network Extractor | Relationship table | `{network_size, counterparty_count, network_depth}` | Pipeline calls `.extract(party_id, db)` |
| Model Registry | Database (SELECT) | Active scorecard weights + intercept | Scoring Service queries during compute |
| Decision Rules | Database (SELECT) | Rule conditions + actions | Scoring Service evaluates after score |
| Feature Storage | Database (INSERT/UPDATE) | Versioned features with valid_from/valid_to | Pipeline calls `_store_features()` |

---

## Core Scoring Logic

### 1. Feature Extraction (Parallel, Multi-Source)

**Purpose**: Convert raw company data into normalized numerical features suitable for credit scoring.

Three extractors run in parallel and are combined:

#### KYC Extractor
```python
# Reads from: parties table

features = {
  "kyc_score": 85,                    # from Party.kyc_verified (0-100)
  "company_age_days": 180,            # days since Party.created_at
  "party_type_encoded": 1,            # numeric encoding: supplier=1, mfg=2, etc.
  "contact_completeness": 75          # % of contact fields filled
}
```

**Why these features?**
- KYC score: Indicator of compliance and due diligence completion
- Company age: Older = more established (lower risk)
- Party type: Some types considered inherently lower risk
- Contact completeness: Better data quality = lower risk

#### Transaction Extractor
```python
# Reads from: transactions table (filtered by party_id)

features = {
  "transaction_count": 15,            # total txns in history
  "avg_transaction_amount": 5000,     # mean transaction value ($)
  "transaction_regularity": 0.96,     # 1 - (std_dev / mean), high = consistent
  "days_since_last_transaction": 2    # recency (lower = more active)
}
```

**Why these features?**
- Volume: More transactions = longer business history
- Consistency: Regular txns indicate stable, predictable business
- Recency: Recent activity = company is currently operating

#### Network Extractor
```python
# Reads from: relationships table (graph traversal)

features = {
  "network_size": 2,                  # total distinct parties in component
  "counterparty_count": 1,            # immediate neighbors (suppliers + customers)
  "network_depth": 2                  # max hops in relationship graph
}
```

**Why these features?**
- Network size: Larger supply chains indicate established position
- Counterparty count: Diversified customer/supplier base = lower concentration risk
- Network depth: Deep integration in supply chain = important player

#### Feature Versioning (Temporal Validity)
```sql
-- Storage model in features table:
party_id: 1
feature_name: "kyc_score"
feature_value: 85.0
source_type: "KYC"
valid_from: 2025-12-12T10:30:00
valid_to: NULL                -- NULL = current version (active)

-- When re-computed 7 days later:
-- UPDATE old record: valid_to = 2025-12-19T10:30:00 (mark as expired)
-- INSERT new record: valid_from = 2025-12-19T10:30:00, valid_to = NULL

-- Benefits:
-- ✅ Historical audit: can replay old scores with old features
-- ✅ Debugging: compare how feature values changed over time
-- ✅ Rollback: revert to old features if extraction logic was wrong
```

---

### 2. Scorecard Scoring Algorithm (Weighted Linear Model)

**Algorithm**: `score = intercept + Σ(normalized_feature[i] × weight[i])`

**Step 1: Normalize Features (0-1 Scale)**

Raw features come in different units (days, dollars, counts, percentages). Normalize using min-max scaling:

```python
normalized = (value - min) / (max - min)

Examples:
  kyc_score: 85 → 0.85 (divide by 100)
  company_age_days: 180 → 0.49 (assume max ~365)
  transaction_count: 15 → 0.75 (assume max ~20)
  transaction_regularity: 0.96 → 0.96 (already in 0-1 range)
```

**Step 2: Fetch Model from model_registry**

```sql
SELECT model_version, model_config, feature_list, intercept
FROM model_registry
WHERE is_active = 1
ORDER BY deployed_date DESC
LIMIT 1;

-- Returns:
{
  "model_version": "default_scorecard_v1",
  "intercept": 0.0,
  "weights": {
    "kyc_score": 0.20,
    "company_age_days": 0.10,
    "transaction_count": 0.25,
    "transaction_regularity": 0.15,
    "days_since_last_transaction": 0.10,
    "network_size": 0.10,
    "counterparty_count": 0.05
  }
}
```

**Step 3: Apply Weighted Sum**

```python
score_0_to_1 = intercept
score_0_to_1 += 0.85 * 0.20    # kyc_score: 0.17
score_0_to_1 += 0.49 * 0.10    # company_age: 0.049
score_0_to_1 += 0.75 * 0.25    # transaction_count: 0.1875
score_0_to_1 += 0.96 * 0.15    # regularity: 0.144
score_0_to_1 += 0.99 * 0.10    # recency: 0.099
score_0_to_1 += 0.33 * 0.10    # network_size: 0.033
score_0_to_1 += 0.25 * 0.05    # counterparty: 0.0125
# = 0.769 (on 0-1 scale)
```

**Step 4: Scale to 300-900 Range (FICO-like)**

Why 300-900? Industry standard for credit scores (FICO, VantageScore). Makes scores interpretable to domain experts.

```python
final_score = 300 + (score_0_to_1 × 600)
            = 300 + (0.769 × 600)
            = 300 + 461.4
            = 761 ✓
```

**Step 5: Assign Score Band**

```python
if final_score >= 800:
    band = "excellent"
elif final_score >= 650:
    band = "good"          ← 761 falls here
elif final_score >= 550:
    band = "fair"
else:
    band = "poor"
```

**Step 6: Compute Confidence**

```python
confidence = count(available_features) / total_expected_features
           = 8 / 15 = 0.53

# Higher confidence = more features were available for scoring
```

**Why Linear Scorecard?**
- ✅ **Interpretable**: Easy to explain which features drive score
- ✅ **Fast**: O(n) computation (fast even with many features)
- ✅ **Auditable**: Weights stored in database, versioned
- ✅ **ML-Ready**: Scorecard is a special case of logistic regression (can swap in ML later)
- ✅ **Regulatory**: Easier to comply with explainability requirements

---

### 3. Decision Rules Engine

**Purpose**: Apply business rules on top of the raw score to produce final decision.

#### Rule Structure
```python
class DecisionRule:
    rule_id: str                  # "RULE_001"
    rule_name: str                # "Reject low KYC"
    condition_expression: str     # Python expression: "kyc_score < 50"
    action: str                   # "reject" | "flag" | "manual_review" | "approve"
    priority: int                 # 1=highest (first match wins)
    is_active: bool               # only evaluate active rules
```

#### Evaluation Logic
```python
def apply_decision_rules(features: dict) -> (decision, reasons):
    rules = db.query(DecisionRule)\
        .filter(DecisionRule.is_active.in_([1, True]))\
        .order_by(DecisionRule.priority)\
        .all()
    
    for rule in rules:
        try:
            # Build safe evaluation context (no builtins)
            safe_context = {"__builtins__": {}}
            safe_context.update(features)
            
            # Evaluate rule condition with feature values
            if eval(rule.condition_expression, safe_context):
                return rule.action, [rule.rule_name]
        except Exception:
            # Skip rules that fail to evaluate
            pass
    
    # Default if no rules matched
    return "approved", []
```

#### Example Decision Rules

| Priority | Condition | Action | Reason |
|----------|-----------|--------|--------|
| 1 | `transaction_count == 0` | reject | No transaction history = cannot assess |
| 2 | `kyc_score < 40` | reject | Very poor KYC verification |
| 3 | `network_size < 2` | flag | Isolated in supply chain (risky) |
| 4 | `company_age_days < 30` | manual_review | Too new to assess |
| 5 | `final_score > 800` | approve | Excellent creditworthiness |

**Default rule set (loaded in database):** 20 production-ready rules covering fraud, KYC/KYCC validity, behavioral/transactional patterns, age/stability, score overrides, and safety nets. First match wins by ascending priority; if nothing matches, the score-based decision is used. See `decision_rules` table for the live set.

#### Safety Notes
- Only `__builtins__` removed (no `open()`, `exec()`, `import`)
- Features dict provides variable context
- Failed expressions skip silently (don't break entire scoring)
- Production: Use expression parser like `simpleeval` instead of `eval()`

---

### 4. Audit Logging (Complete Traceability)

**Every score computation creates a ScoreRequest record:**

```python
class ScoreRequest:
    id: str                          # UUID
    party_id: int                    # Which company?
    request_timestamp: datetime      # When scored
    model_version: str               # "default_scorecard_v1"
    model_type: str                  # "scorecard" | "ml_model"
    features_snapshot: JSON          # All features used (for replay)
    raw_score: float                 # 0-1
    final_score: int                 # 300-900
    score_band: str                  # excellent/good/fair/poor
    confidence_level: float          # % of available features
    decision: str                    # approve/reject/flag/review
    decision_reasons: JSON           # [rule names that matched]
    processing_time_ms: int
```

**Benefits**:
- ✅ **Explainability**: Show user "these features were used at score time"
- ✅ **Audit Trail**: When was company scored? By which model?
- ✅ **Replay**: If model weights change, re-run old scores with old features
- ✅ **Debugging**: If score seems wrong, check features_snapshot
- ✅ **Compliance**: Full traceability for regulatory reviews

**Example Snapshot**:
```json
{
  "kyc_score": 85,
  "company_age_days": 180,
  "party_type_encoded": 1,
  "transaction_count": 15,
  "avg_transaction_amount": 5000,
  "transaction_regularity": 0.96,
  "days_since_last_transaction": 2,
  "network_size": 2,
  "counterparty_count": 1,
  "network_depth": 2
}
```

---

## Complete Example: Scoring Three Companies

### Setup: Three Test Parties in Supply Chain

```
┌─────────────────────────────────────────────────────────┐
│  SUPPLY CHAIN NETWORK                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Party 1: ACME SUPPLIERS (supplier)                    │
│    ├─ Created: 180 days ago                            │
│    ├─ KYC Score: 85/100                                │
│    ├─ Transactions: 15 to Global Distributor           │
│    │   - Avg: $5,000 each                              │
│    │   - Regularity: Very consistent (std_dev: $200)   │
│    │   - Latest: 2 days ago                            │
│    └─ Network: 1 direct customer (Global)              │
│                                                         │
│  ↓ supplies_to                                          │
│                                                         │
│  Party 2: GLOBAL DISTRIBUTOR (distributor)             │
│    ├─ Created: 200 days ago                            │
│    ├─ KYC Score: 92/100                                │
│    ├─ Transactions: 8 to Local Retailer                │
│    │   - Avg: $3,000 each                              │
│    │   - Regularity: Somewhat irregular (std_dev: $1.5k)
│    │   - Latest: 5 days ago                            │
│    ├─ Upstream: 1 supplier (ACME)                      │
│    └─ Downstream: 1 customer (Local Retailer)          │
│                                                         │
│  ↓ distributes_to                                       │
│                                                         │
│  Party 3: LOCAL RETAILER (retailer)                    │
│    ├─ Created: 30 days ago                             │
│    ├─ KYC Score: 60/100                                │
│    ├─ Transactions: 2 total                            │
│    │   - Avg: $500 each                                │
│    │   - Regularity: Very irregular                    │
│    │   - Latest: 1 day ago (recent)                    │
│    └─ Upstream: 1 supplier (Global)                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Step-by-Step: Computing Score for ACME SUPPLIERS (Party 1)

#### **Step 1: User Clicks "Compute Credit Score" in Frontend**

```javascript
// React component
onClick={() => fetch(
  `http://localhost:8001/api/scoring/score/1`,
  { method: 'POST', headers: { 'Content-Type': 'application/json' } }
)}
```

#### **Step 2: API Receives Request**

```python
# app/api/scoring.py
@router.post("/api/scoring/score/{party_id}")
def get_credit_score(
    party_id: int,
    model_version: Optional[str] = None,
    include_explanation: bool = True,
    db: Session = Depends(get_db)
) → ScoreResponse:
    scoring_service = ScoringService(db)
    result = scoring_service.compute_score(party_id=1)
    return result  # JSON serialized by Pydantic
```

#### **Step 3: Scoring Service Ensures Features Are Fresh**

```python
# app/services/scoring_service.py

def compute_score(self, party_id: int):
    # Check if features already computed and not stale (< 7 days)
    latest = db.query(Feature)\
        .filter(Feature.party_id == 1, Feature.valid_to == None)\
        .first()
    
    if not latest or (datetime.utcnow() - latest.computation_timestamp).days > 7:
        # Trigger extraction
        pipeline = FeaturePipelineService(db)
        pipeline.extract_all_features(party_id=1)
```

#### **Step 4: Feature Pipeline Orchestrates Extraction**

```python
# Three extractors run in parallel context:

KYC_EXTRACTOR.extract(party_id=1, db):
  party = db.query(Party).filter(Party.id == 1).first()  # ACME SUPPLIERS
  return [
    FeatureExtractorResult("kyc_score", 85.0),
    FeatureExtractorResult("company_age_days", 180.0),
    FeatureExtractorResult("party_type_encoded", 1.0),    # supplier=1
    FeatureExtractorResult("contact_completeness", 75.0)
  ]

TRANSACTION_EXTRACTOR.extract(party_id=1, db):
  txns = db.query(Transaction).filter(Transaction.from_party_id == 1).all()
  # 15 transactions to Global Distributor
  return [
    FeatureExtractorResult("transaction_count", 15.0),
    FeatureExtractorResult("avg_transaction_amount", 5000.0),
    FeatureExtractorResult("transaction_regularity", 0.96),  # very consistent
    FeatureExtractorResult("days_since_last_transaction", 2.0)
  ]

NETWORK_EXTRACTOR.extract(party_id=1, db):
  # Graph traversal: ACME → Global → Local
  # ACME has 1 direct customer (Global)
  return [
    FeatureExtractorResult("network_size", 2.0),           # ACME + Global
    FeatureExtractorResult("counterparty_count", 1.0),     # 1 direct customer
    FeatureExtractorResult("network_depth", 2.0)           # 2 hops downstream
  ]
```

#### **Step 5: Store Features in Database (Versioned)**

```sql
INSERT INTO features (party_id, feature_name, feature_value, source_type, valid_from)
VALUES
  (1, 'kyc_score', 85.0, 'KYC', 2025-12-12 10:30:00),
  (1, 'company_age_days', 180.0, 'KYC', 2025-12-12 10:30:00),
  (1, 'party_type_encoded', 1.0, 'KYC', 2025-12-12 10:30:00),
  (1, 'contact_completeness', 75.0, 'KYC', 2025-12-12 10:30:00),
  (1, 'transaction_count', 15.0, 'TRANSACTION', 2025-12-12 10:30:00),
  (1, 'avg_transaction_amount', 5000.0, 'TRANSACTION', 2025-12-12 10:30:00),
  (1, 'transaction_regularity', 0.96, 'TRANSACTION', 2025-12-12 10:30:00),
  (1, 'days_since_last_transaction', 2.0, 'TRANSACTION', 2025-12-12 10:30:00),
  (1, 'network_size', 2.0, 'NETWORK', 2025-12-12 10:30:00),
  (1, 'counterparty_count', 1.0, 'NETWORK', 2025-12-12 10:30:00),
  (1, 'network_depth', 2.0, 'NETWORK', 2025-12-12 10:30:00);
```

#### **Step 6: Normalize Features to 0-1 Scale**

```python
normalized_features = {
    'kyc_score': 85.0 / 100.0 = 0.85,
    'company_age_days': 180.0 / 365.0 = 0.49,
    'party_type_encoded': 1.0 / 5.0 = 0.20,
    'contact_completeness': 75.0 / 100.0 = 0.75,
    'transaction_count': 15.0 / 20.0 = 0.75,
    'avg_transaction_amount': 5000.0 / 7500.0 = 0.67,
    'transaction_regularity': 0.96,
    'days_since_last_transaction': (365.0 - 2.0) / 365.0 = 0.99,
    'network_size': 2.0 / 6.0 = 0.33,
    'counterparty_count': 1.0 / 4.0 = 0.25,
    'network_depth': 2.0 / 3.0 = 0.67
}
```

#### **Step 7: Fetch Scorecard Model**

```sql
SELECT * FROM model_registry
WHERE is_active = 1
ORDER BY deployed_date DESC
LIMIT 1;

-- Returns:
{
  model_version: "default_scorecard_v1",
  model_type: "scorecard",
  is_active: 1,
  intercept: 0.0,
  weights: {
    "kyc_score": 0.20,
    "company_age_days": 0.10,
    "party_type_encoded": 0.05,
    "contact_completeness": 0.00,
    "transaction_count": 0.25,
    "avg_transaction_amount": 0.05,
    "transaction_regularity": 0.15,
    "days_since_last_transaction": 0.10,
    "network_size": 0.10,
    "counterparty_count": 0.05,
    "network_depth": 0.00
  }
}
```

#### **Step 8: Apply Scorecard Formula (Weighted Sum)**

```python
score_0_to_1 = 0.0  # intercept

# Apply each feature weight
score_0_to_1 += 0.85 * 0.20       # kyc_score = 0.170
score_0_to_1 += 0.49 * 0.10       # company_age = 0.049
score_0_to_1 += 0.20 * 0.05       # party_type = 0.010
score_0_to_1 += 0.75 * 0.00       # contact = 0.000
score_0_to_1 += 0.75 * 0.25       # transaction_count = 0.1875
score_0_to_1 += 0.67 * 0.05       # avg_amount = 0.0335
score_0_to_1 += 0.96 * 0.15       # regularity = 0.144
score_0_to_1 += 0.99 * 0.10       # recency = 0.099
score_0_to_1 += 0.33 * 0.10       # network_size = 0.033
score_0_to_1 += 0.25 * 0.05       # counterparty = 0.0125
score_0_to_1 += 0.67 * 0.00       # network_depth = 0.000

# Total: 0.769 (on 0-1 scale)
```

#### **Step 9: Scale to Credit Score Range (300-900)**

```python
final_score = 300 + (0.769 * 600)
            = 300 + 461.4
            = 761 ✓

score_band = "good" (650-800 range)
confidence = 10 / 11 = 0.91 (10 features used, 11 defined)
```

#### **Step 10: Apply Decision Rules**

```sql
SELECT * FROM decision_rules
WHERE is_active = 1
ORDER BY priority;

-- Evaluation:

Rule 1 (Priority 1): "Reject if no transactions"
  Condition: transaction_count == 0
  Eval: 15 == 0? NO → skip

Rule 2 (Priority 2): "Reject if kyc_score < 40"
  Condition: kyc_score < 40
  Eval: 85 < 40? NO → skip

Rule 3 (Priority 3): "Flag if network_size < 2"
  Condition: network_size < 2
  Eval: 2 < 2? NO → skip

Rule 4 (Priority 4): "Approve if final_score > 750"
  Condition: final_score > 750
  Eval: 761 > 750? YES ✓ → MATCH!

Final Decision: APPROVE
Reasons: ["Rule 4: Approve if final_score > 750"]
```

#### **Step 11: Create Audit Log**

```python
score_request = ScoreRequest(
    id="550e8400-e29b-41d4-a716-446655440000",  # UUID
    party_id=1,
    model_version="default_scorecard_v1",
    model_type="scorecard",
    features_snapshot=json.dumps({
        "kyc_score": 85.0,
        "company_age_days": 180.0,
        "party_type_encoded": 1.0,
        "contact_completeness": 75.0,
        "transaction_count": 15.0,
        "avg_transaction_amount": 5000.0,
        "transaction_regularity": 0.96,
        "days_since_last_transaction": 2.0,
        "network_size": 2.0,
        "counterparty_count": 1.0,
        "network_depth": 2.0
    }),
    raw_score=0.769,
    final_score=761,
    score_band="good",
    confidence_level=0.91,
    decision="APPROVE",
    decision_reasons=json.dumps([
        "Rule 4: Approve if final_score > 750"
    ]),
    processing_time_ms=145,
    request_timestamp=datetime.utcnow()
)
db.add(score_request)
db.commit()
```

#### **Step 12: Return Response to API**

```json
{
  "party_id": 1,
  "score": 761,
  "score_band": "good",
  "confidence": 0.91,
  "decision": "APPROVE",
  "decision_reasons": [
    "Rule 4: Approve if final_score > 750"
  ],
  "explanation": {
    "top_positive_factors": [
      {
        "feature": "transaction_count",
        "value": 15.0,
        "contribution": 0.1875
      },
      {
        "feature": "transaction_regularity",
        "value": 0.96,
        "contribution": 0.144
      },
      {
        "feature": "kyc_score",
        "value": 85.0,
        "contribution": 0.170
      }
    ],
    "top_negative_factors": []
  },
  "computed_at": "2025-12-12T10:31:00",
  "model_version": "default_scorecard_v1"
}
```

#### **Step 13: Frontend Displays Results**

```
┌────────────────────────────────────────┐
│  ACME SUPPLIERS - Credit Assessment   │
├────────────────────────────────────────┤
│                                        │
│        Credit Score: 761               │
│        ████████████░░░░░░░░ 66%        │
│                                        │
│  Band: GOOD                            │
│  Decision: ✅ APPROVE                  │
│  Confidence: 91%                       │
│                                        │
│  Scoring Breakdown:                    │
│  • Transaction Count:      +0.1875     │
│  • Regularity:             +0.144      │
│  • KYC Score:              +0.170      │
│  • Days Since Last Txn:    +0.099      │
│  • Company Age:            +0.049      │
│  • Network Size:           +0.033      │
│  • Counterparty Count:     +0.0125     │
│  ───────────────────────────────       │
│  Total (Raw): 0.769 → Final: 761       │
│                                        │
│  Rules Applied:                        │
│  ✓ Rule 4: Approve if score > 750      │
│                                        │
│  Computed: 2025-12-12 10:31:00         │
│  Model: default_scorecard_v1           │
│  Processing Time: 145ms                │
│                                        │
└────────────────────────────────────────┘
```

### Summary Table: All Three Companies

| Company | KYC | Age | Txns | Regularity | Score | Band | Decision |
|---------|-----|-----|------|------------|-------|------|----------|
| **ACME Suppliers** (ID=1) | 85 | 180d | 15 | 0.96 | **761** | GOOD | ✅ APPROVE |
| **Global Distributor** (ID=2) | 92 | 200d | 8 | 0.70 | **748** | GOOD | ⚠️ REVIEW |
| **Local Retailer** (ID=3) | 60 | 30d | 2 | 0.40 | **425** | POOR | ❌ REJECT |

**Why Different Decisions?**

- **ACME (761)**: High KYC, consistent transactions, established history → APPROVE
- **Global Distributor (748)**: High KYC but borderline score (748 vs 750 threshold) → requires MANUAL REVIEW
- **Local Retailer (425)**: New company, low KYC, few transactions, isolation in network → REJECT per Rule 1

---

## Project Structure & Components

### Directory Layout

```
KYCC/
├── backend/                           # FastAPI server
│   ├── __init__.py                   # Makes backend a package
│   ├── main.py                       # FastAPI app + 3 routers + health/stats
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py           # Engine, SessionLocal, get_db()
│   │   │   ├── crud.py               # Create/read/update/delete helpers
│   │   │   └── __pycache__/
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── models.py             # 14 SQLAlchemy ORM models
│   │   │   └── __pycache__/
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── schemas.py            # Pydantic validation schemas
│   │   │   └── __pycache__/
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── parties.py            # /api/parties/* endpoints
│   │   │   ├── relationships.py      # /api/relationships/* endpoints
│   │   │   ├── scoring.py            # /api/scoring/* endpoints (★ MAIN)
│   │   │   └── __pycache__/
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── scoring_service.py    # Orchestrates scoring pipeline
│   │   │   ├── feature_pipeline_service.py  # Orchestrates feature extraction
│   │   │   ├── network_service.py    # Graph traversal for relationships
│   │   │   └── __pycache__/
│   │   │
│   │   └── extractors/
│   │       ├── __init__.py
│   │       ├── base_extractor.py     # BaseFeatureExtractor + FeatureExtractorResult
│   │       ├── kyc_extractor.py      # KYC features from parties table
│   │       ├── transaction_extractor.py  # Transaction features (volume, consistency)
│   │       ├── network_extractor.py  # Network features (size, depth)
│   │       └── __pycache__/
│   │
│   ├── alembic/                       # Database migrations (future)
│   │   ├── env.py
│   │   ├── README
│   │   ├── script.py.mako
│   │   └── versions/
│   │
│   ├── .env                           # Environment config (DO NOT COMMIT)
│   ├── alembic.ini                    # Alembic config
│   ├── requirements.txt                # Python dependencies
│   └── test_*.py / view_database.py   # Test scripts
│
├── frontend/                           # React + Streamlit UIs
│   ├── src/
│   │   ├── components/
│   │   │   ├── PartyList.jsx
│   │   │   ├── PartyForm.jsx
│   │   │   ├── CreditScore.jsx       # Display scoring results (★)
│   │   │   ├── NetworkGraph.jsx
│   │   │   ├── FeatureBreakdown.jsx
│   │   │   └── ...
│   │   ├── App.jsx                    # Main routing
│   │   └── index.js
│   │
│   ├── streamlit_app.py               # Lightweight alternative UI
│   ├── package.json                   # Node dependencies
│   ├── esbuild.config.js             # Build configuration
│   └── node_modules/
│
├── README.md                           # This file
├── .git/                               # Version control
└── .gitignore                          # Exclude .env, venv, etc.
```

---

## Database Schema (Logical)

### Core Tables

#### `parties` (Supply Chain Actors)
| Column | Type | Notes |
|--------|------|-------|
| id | INT | Primary key |
| party_name | VARCHAR | Company name |
| party_type | VARCHAR | supplier, manufacturer, distributor, retailer, customer |
| kyc_verified | INT | 0-100 compliance score |
| tax_id | VARCHAR | Tax identification |
| address | VARCHAR | |
| contact_person | VARCHAR | |
| email | VARCHAR | |
| phone | VARCHAR | |
| created_at | TIMESTAMP | When registered |
| updated_at | TIMESTAMP | Last modification |

#### `relationships` (Supply Chain Connections)
| Column | Type | Notes |
|--------|------|-------|
| id | INT | Primary key |
| from_party_id | INT | FK → parties |
| to_party_id | INT | FK → parties |
| relationship_type | VARCHAR | supplies_to, distributes_to, etc. |
| created_at | TIMESTAMP | When created |

#### `transactions` (Payment/Shipment History)
| Column | Type | Notes |
|--------|------|-------|
| id | INT | Primary key |
| from_party_id | INT | FK → parties |
| to_party_id | INT | FK → parties |
| amount | DECIMAL | Transaction value |
| transaction_date | TIMESTAMP | When occurred |
| payment_type | VARCHAR | Cash, wire, crypto, etc. |
| created_at | TIMESTAMP | |

### Scoring & Features Tables

#### `features` (Extracted Signals - Versioned)
| Column | Type | Notes |
|--------|------|-------|
| id | INT | Primary key |
| party_id | INT | FK → parties |
| feature_name | VARCHAR | kyc_score, transaction_count, etc. |
| feature_value | DECIMAL | Numerical value |
| confidence_score | DECIMAL | 0-1, extractor confidence |
| source_type | VARCHAR | KYC, TRANSACTION, NETWORK |
| computation_timestamp | TIMESTAMP | When computed |
| valid_from | TIMESTAMP | Start of validity |
| valid_to | TIMESTAMP | End of validity (NULL = current) |

**Indices**:
- `(party_id, feature_name, valid_to)` - Fast lookup of current features

#### `score_requests` (Audit Log - Complete Traceability)
| Column | Type | Notes |
|--------|------|-------|
| id | VARCHAR | UUID, primary key |
| party_id | INT | FK → parties |
| request_timestamp | TIMESTAMP | When scored |
| model_version | VARCHAR | Scorecard ID |
| model_type | VARCHAR | scorecard, ml_model |
| features_snapshot | JSON | All features at scoring time |
| raw_score | DECIMAL | 0-1 |
| final_score | INT | 300-900 |
| score_band | VARCHAR | excellent, good, fair, poor |
| confidence_level | DECIMAL | 0-1 |
| decision | str | approve, reject, flag, manual_review |
| decision_reasons | JSON | Rule names that matched |
| processing_time_ms | INT | Latency |

**Indices**:
- `(party_id)` - Lookup scores by company
- `(request_timestamp DESC)` - Latest scores first

#### `model_registry` (Scorecard Repository)
| Column | Type | Notes |
|--------|------|-------|
| model_version | VARCHAR | PK, e.g. "default_scorecard_v1" |
| model_type | VARCHAR | scorecard, xgboost, neural_net |
| model_config | JSON | Weights, intercept, hyperparams |
| feature_list | JSON | ["kyc_score", "transaction_count", ...] |
| intercept | DECIMAL | Offset for scorecard |
| normalization_method | VARCHAR | min-max, z-score, etc. |
| training_date | TIMESTAMP | When trained |
| deployed_date | TIMESTAMP | When put in production |
| is_active | INT | 0/1 (current model) |
| performance_metrics | JSON | AUC, precision, recall, etc. |
| description | TEXT | Notes |
| created_by | VARCHAR | Model creator |

#### `decision_rules` (Business Rules)
| Column | Type | Notes |
|--------|------|-------|
| rule_id | VARCHAR | PK, e.g. "RULE_001" |
| rule_name | VARCHAR | Descriptive name |
| condition_expression | TEXT | Python expression |
| action | VARCHAR | approve, reject, flag, manual_review |
| priority | INT | 1=highest (first match wins) |
| is_active | INT | 0/1 (enable/disable) |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

---

## API Endpoints (23 Total)

### Parties CRUD (7 endpoints)
- `POST /api/parties/` — Create party
- `GET /api/parties/` — List parties (filterable: `?party_type=supplier`)
- `GET /api/parties/{id}` — Get one party
- `PUT /api/parties/{id}` — Update party
- `DELETE /api/parties/{id}` — Delete party
- `GET /api/parties/{id}/network` — Get relationship graph (tree)
- `GET /api/parties/{id}/counterparties` — Get direct neighbors only

### Relationships CRUD (3 endpoints)
- `POST /api/relationships/` — Create relationship
- `GET /api/relationships/` — List relationships
- `DELETE /api/relationships/{id}` — Remove relationship

### **Scoring** ⭐ (4 endpoints)
- **`POST /api/scoring/score/{party_id}`** — **Compute credit score** (MAIN)
- `GET /api/scoring/score/{party_id}/history` — Score audit trail
- `GET /api/scoring/features/{party_id}` — View extracted features
- `POST /api/scoring/compute-features/{party_id}` — Manually trigger extraction

### Utility (3 endpoints)
- `GET /` — API info + endpoints list
- `GET /health` — Health check
- `GET /api/stats` — System statistics (party counts, avg scores, distributions)

---

## Setup & Local Development

### Prerequisites
- Python 3.11+
- Docker Desktop (for PostgreSQL)
- Node.js 18+ (optional, for React frontend)

### Step 1: Clone & Create Virtual Environment

```powershell
# Clone repo
git clone <repo> && cd KYCC

# Create Python venv
python -m venv venv
venv\Scripts\Activate.ps1  # Windows PowerShell

# Install dependencies
pip install -r backend/requirements.txt
```

### Step 2: Start PostgreSQL (choose one)

**Option A: Docker Compose (recommended)**

```powershell
# From repo root
docker compose up -d postgres
```

**Option B: Single docker run**

```powershell
# Run Postgres container (persistent volume)
docker run -d --name kycc-postgres `
  -e POSTGRES_USER=kycc_user `
  -e POSTGRES_PASSWORD=kycc_pass `
  -e POSTGRES_DB=kycc_db `
  -p 5433:5432 `
  -v kycc_pgdata:/var/lib/postgresql/data `
  postgres:15

# Verify ready
docker exec kycc-postgres pg_isready -U kycc_user -d kycc_db
```

### Step 3: Configure `.env`

```env
# backend/.env
DATABASE_URL=postgresql://kycc_user:kycc_pass@localhost:5433/kycc_db
DEV_DATABASE_URL=sqlite:///./dev.db
AUTO_CREATE_TABLES=1
FORCE_SQLITE_FALLBACK=0
```

### Step 4: Generate Test Data

```powershell
cd backend

# Generate 100 synthetic companies (excellent/good/fair/poor profiles)
python -m scripts.seed_synthetic_profiles \
    --batch-id BATCH_001 \
    --count 100 \
    --scenario balanced \
    --out data/synthetic_profiles.json

# Load into database
python ingest_data.py
```

**Output**: 100 parties, 100 accounts (NRS currency), ~10,000 transactions, ~650 relationships

See [SYNTHETIC_DATA.md](SYNTHETIC_DATA.md) for detailed documentation.

### Step 5: Run API Server

**Option A: Docker Compose (backend + Postgres)**

```powershell
# From repo root
docker compose up -d
# API: http://localhost:8000 | Docs: http://localhost:8000/docs
```

**Option B: Local uvicorn (uses host venv)**

```powershell
cd backend
python -m uvicorn main:app --reload --port 8001

# API available at:
# - http://localhost:8001
# - API docs: http://localhost:8001/docs
# - ReDoc: http://localhost:8001/redoc
```

### Step 6: Run Frontend (Optional)

**Option A: React (esbuild)**
```powershell
cd frontend
npm install && npm run dev
# Open http://localhost:5173
```

**Option B: Streamlit (Lightweight)**
```powershell
cd frontend
python -m streamlit run streamlit_app.py
# Opens automatically in browser
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'app'"
**Solution**: Ensure `backend/__init__.py` exists (makes backend a package).

### Postgres Connection Error
**Solution**:
1. Verify container running: `docker ps`
2. Check credentials in `.env` match Docker setup
3. Set `FORCE_SQLITE_FALLBACK=1` to use SQLite instead

### Score Seems Wrong
**Debug**:
1. Call `GET /api/scoring/features/{party_id}` to see extracted features
2. Check `model_registry` table for correct weights
3. Review `score_requests` audit log entry for `features_snapshot`

---

## Design Principles

✅ **Modular**: Extractors are pluggable (add new ones without touching scoring logic)

✅ **Auditable**: Every computation logged with full feature snapshot + model version

✅ **Interpretable**: Linear scorecard explains which factors matter most

✅ **Extensible**: ML model support via `model_registry` (plug in any model)

✅ **Robust**: Fallback from Postgres to SQLite, error handling in extractors

✅ **Scalable**: Stateless API (can run multiple instances), database-backed persistence

---

## Next Steps & Future Work

- [ ] Add Alembic migrations for schema versioning
- [ ] Implement ML scoring option (XGBoost, Neural Network) in model_registry
- [ ] Add data validation rules for incoming transactions
- [ ] Build admin dashboard for model/rule management
- [ ] Add webhooks for score change notifications
- [ ] Implement feature importance explainability (SHAP values)
- [ ] Add API rate limiting and authentication (OAuth2)
- [ ] Deploy to cloud (AWS ECS, GCP Cloud Run, Azure Container Instances)
