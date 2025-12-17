# KYCC & Credit Scoring System: Technical Documentation

## 1. System Overview

**KYCC (Know Your Customer's Customer)** is a supply chain credit scoring platform designed to model parties (suppliers, manufacturers, distributors, retailers), their relationships, and transactions. The system extracts features from multiple sources (KYC data, transaction history, network graph), computes credit scores (300-900) using scorecard models, applies business rules, and generates auditable scoring explanations.

- **Backend:** FastAPI, SQLAlchemy 2.x, PostgreSQL (with SQLite fallback)
- **Frontend:** React + Vite, Recharts, ReactFlow
- **Data Models:** Pydantic v2

---

## 2. Architecture & Patterns

### 2.1 Service Layer Pipeline
All scoring operations follow a strict pipeline:

1. **API Router** (e.g., `POST /api/scoring/run`)
2. **ScoringService** (`scoring_service.compute_score()`): Orchestrates the scoring process.
3. **FeaturePipelineService**: Manages parallel feature extraction.
4. **Extractors**: Specialized classes for KYC, Transaction, and Network features.
5. **Database**: Persistent storage for parties, transactions, features, and scores.

### 2.2 Extractor Pattern
- All extractors inherit from `BaseFeatureExtractor` ([backend/app/extractors/base_extractor.py]).
- Each extractor returns `List[FeatureExtractorResult]`.
- **KYCFeatureExtractor:** Reads from `Party` table (e.g., `kyc_score`, `company_age_days`).
- **TransactionFeatureExtractor:** Reads from `Transaction` table (e.g., `txn_count`, `avg_amount`).
- **NetworkFeatureExtractor:** Reads from `Relationship` table (e.g., `network_size`, `counterparty_count`).
- **Traceability:** All results are tagged with `metadata["source_type"]`.

### 2.3 Adapter Pattern
- Adapters normalize data from various sources ([backend/app/adapters/base.py]).
- **SyntheticAdapter:** Converts synthetic test profiles to the Party schema.
- **Registry:** `AdapterRegistry.register("synthetic", SyntheticAdapter)` enables runtime selection.
- **Future Integrations:** CSV, API, ERP adapters must implement `parse(data) -> dict`.

### 2.4 TTL Cache
- In-memory, thread-safe cache with 5-minute TTL ([backend/app/cache/ttl_cache.py]).
- Key format: `party:{party_id}:features:all`.
- Use `cache.get()` before DB queries; fallback to DB if cache miss.

---

## 3. Database Design & Models

### 3.1 Session Management
- Always use dependency injection: `db: Session = Depends(get_db)` ([backend/app/db/database.py]).
- Never instantiate sessions directly in routes.

### 3.2 Enum Storage
- Store enums as **plain strings** (not Python enum values) to avoid serialization issues.

### 3.3 Temporal Features
- `Feature` table uses `valid_from`/`valid_to` for versioning.
- New features expire old ones: `UPDATE Feature SET valid_to = NOW() WHERE party_id = X`.
- Query current features: `WHERE valid_to IS NULL`.

### 3.4 Main Models ([backend/app/models/models.py])
- **Party:** Core entity for KYC data.
- **Transaction:** Records of financial activity.
- **Relationship:** Network graph edges.
- **Feature:** Extracted features with temporal versioning.
- **ScoreRequest:** Logs scoring requests and results.

---

## 4. Feature Extraction & Scoring Logic

### 4.1 FeaturePipelineService ([backend/app/services/feature_pipeline_service.py])
- Orchestrates parallel execution of all registered extractors.
- Aggregates results for scoring.

### 4.2 ScoringService ([backend/app/services/scoring_service.py])
- Coordinates feature extraction, scorecard computation, rule evaluation, and logging.
- Applies scorecard weights to features.
- Evaluates business rules for banding and explanations.

### 4.3 Rule Evaluation ([backend/app/rules/evaluator.py])
- Uses `simpleeval` for safe expression parsing.
- Supports custom business logic for score bands and overrides.

---

## 5. API Endpoints & Integration

### 5.1 Main API Routes ([backend/app/api/])
- **/api/scoring/run:** Trigger scoring for a party.
- **/api/parties:** CRUD for party entities.
- **/api/relationships:** CRUD for network relationships.
- **/api/synthetic:** Ingest synthetic data for testing.

### 5.2 Frontend Integration
- **REST API:** Consumed via axios at `http://localhost:8000/api/*`.
- **SPA Routing:** React Router v7.
- **Visualizations:** Recharts (scores), ReactFlow (network graphs).

---

## 6. Testing & Development Workflows

### 6.1 Database Isolation ([backend/tests/conftest.py])
- Tests use SQLite (`test_run.db`) to avoid polluting Postgres.
- DB file is deleted/recreated per test run.
- Real SQLAlchemy operations (no mocks).

### 6.2 Test Structure ([backend/tests/])
- Each test is self-contained and uses real DB operations.
- Example:
  ```python
  def test_feature_name():
      result = compute_score("synthetic", {"party_id": "P-123", ...})
      assert result["total_score"] >= 80
      assert result["band"] == "excellent"
  ```
- Run tests: `cd backend && pytest`

### 6.3 Data Seeding
- Use `synthetic_seed_service.ingest_seed_file()` to load synthetic profiles.
- Example:
  ```shell
  python -c "from app.services.synthetic_seed_service import ingest_seed_file; from app.db.database import SessionLocal; db=SessionLocal(); ingest_seed_file(db, 'data/synthetic_profiles.json', batch_id='BATCH_001')"
  ```

---

## 7. Deployment, Startup, and Migration

### 7.1 Startup
- Use `run_all.ps1` to start backend and frontend with port auto-detection.
- Backend: `http://127.0.0.1:8000/docs`
- Frontend: `http://localhost:5173`

### 7.2 Backend Only
- Activate venv and run with Uvicorn:
  ```shell
  cd backend
  .\venv\Scripts\Activate.ps1
  python -m uvicorn main:app --port 8000 --reload
  ```

### 7.3 Database Migrations
- Use Alembic for schema changes:
  ```shell
  cd backend
  alembic revision --autogenerate -m "description"
  alembic upgrade head
  ```

### 7.4 Docker
- Dockerfile and docker-compose.yml provided for containerized deployment.
- Postgres 15 as primary DB; SQLite fallback if unavailable.

---

## 8. Common Gotchas & Best Practices

- **Circular Imports:** Import models at function level if needed.
- **Session Leaks:** Always use `get_db()` dependency.
- **Enum Serialization:** Store as strings, convert to enum only when needed.
- **Port Conflicts:** `run_all.ps1` auto-resolves.
- **Postgres Unavailable:** System falls back to SQLite (see logs for `[FALLBACK] Using SQLite`).
- **Feature Traceability:** Always tag features with `metadata["source_type"]`.
- **Testing:** Never mock DB layer; always use real DB.

---

## 9. File Reference Map

- **Core scoring logic:** [backend/app/services/scoring_service.py]
- **Feature orchestration:** [backend/app/services/feature_pipeline_service.py]
- **Database models:** [backend/app/models/models.py]
- **API routes:** [backend/app/api/scoring_v2.py]
- **Rule evaluation:** [backend/app/rules/evaluator.py]
- **Database connection:** [backend/app/db/database.py]
- **Cache:** [backend/app/cache/ttl_cache.py]
- **Adapters:** [backend/app/adapters/base.py], [backend/app/adapters/registry.py], [backend/app/adapters/synthetic_adapter.py]
- **Extractors:** [backend/app/extractors/]
- **Tests:** [backend/tests/]

---

## 10. Extending the System

- **New API Endpoint:** Add route in `backend/app/api/`, include in `main.py` routers.
- **New Feature Extractor:** Inherit `BaseFeatureExtractor`, implement `extract()` and `get_source_type()`, register in `FeaturePipelineService`.
- **New Data Source:** Create adapter inheriting `BaseAdapter`, register in `AdapterRegistry`.
- **Database Schema Change:** Create Alembic migration, update models.
- **Always Write Tests:** Follow patterns in [backend/tests/].

---

## 11. References
- See [QUICKSTART.md], [README.md], and in-code docstrings for further details.
