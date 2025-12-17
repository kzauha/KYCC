# KYCC Agent Instructions

## Project Overview

**KYCC (Know Your Customer's Customer)** is a supply chain credit scoring platform that:
- Models parties (suppliers/manufacturers/distributors/retailers), relationships, and transactions
- Extracts features from multiple sources (KYC data, transaction history, network graph)
- Computes 300-900 credit scores using scorecard models
- Applies business rules and generates auditable scoring explanations

**Stack**: FastAPI + SQLAlchemy 2.x + PostgreSQL (SQLite fallback) | React + Vite | Pydantic v2

---

## Architecture Patterns

### Service Layer Pipeline
All scoring follows this flow:
1. **API Router** → 2. **ScoringService** → 3. **FeaturePipelineService** → 4. **Extractors** (KYC/Transaction/Network) → 5. **Database**

Example: `POST /api/scoring/run` triggers `scoring_service.compute_score()` which orchestrates feature extraction from 3 parallel extractors, applies scorecard weights, evaluates decision rules, and logs to `ScoreRequest` table.

### Extractor Pattern (see [backend/app/extractors/base_extractor.py](backend/app/extractors/base_extractor.py))
All extractors inherit `BaseFeatureExtractor` and return `List[FeatureExtractorResult]`:
- `KYCFeatureExtractor` → reads `Party` table (kyc_score, company_age_days, party_type_encoded)
- `TransactionFeatureExtractor` → reads `Transaction` table (txn_count, avg_amount, regularity)
- `NetworkFeatureExtractor` → reads `Relationship` table (network_size, counterparty_count, depth)

**Key Convention**: Extractors MUST tag results with `metadata["source_type"]` for traceability.

### Adapter Pattern (see [backend/app/adapters/base.py](backend/app/adapters/base.py))
Data sources normalize through adapters (`BaseAdapter`):
- `SyntheticAdapter` → converts synthetic test profiles to standardized Party schema
- Future: CSV, API, ERP integrations follow same `parse(data) -> dict` interface

Registry pattern: `AdapterRegistry.register("synthetic", SyntheticAdapter)` enables runtime adapter selection.

### TTL Cache (see [backend/app/cache/ttl_cache.py](backend/app/cache/ttl_cache.py))
Features are cached in-memory with 5-minute TTL:
- Key format: `party:{party_id}:features:all`
- Thread-safe with `threading.Lock()`
- Use `cache.get()` before DB queries, fallback to DB if miss

---

## Database Patterns

### Session Management
Always use dependency injection (never create sessions directly):
```python
from app.db.database import get_db
@router.get("/endpoint")
def handler(db: Session = Depends(get_db)):
    # db auto-closes after request
```

### Enum Storage Convention
Store enums as **plain strings** (not Python enum values) to avoid serialization issues:
```python
party = Party(party_type="supplier")  # ✓ Correct
party = Party(party_type=PartyType.SUPPLIER)  # ✗ Avoid
```

### Temporal Features (see [backend/app/models/models.py](backend/app/models/models.py))
`Feature` table uses `valid_from`/`valid_to` for versioning:
- When extracting new features, expire old ones: `UPDATE Feature SET valid_to = NOW() WHERE party_id = X`
- Query current: `WHERE valid_to IS NULL`

---

## Testing Patterns

### Database Isolation (see [backend/tests/conftest.py](backend/tests/conftest.py))
Tests **always** use SQLite (`test_run.db`) to avoid Postgres state pollution:
- `conftest.py` sets `DATABASE_URL=sqlite:///test_run.db` before imports
- DB file deleted/recreated per test run
- Never mock the database layer—use real SQLAlchemy operations

### Test Structure
```python
def test_feature_name():
    """One-line description of what's tested."""
    result = compute_score("synthetic", {"party_id": "P-123", ...})
    assert result["total_score"] >= 80
    assert result["band"] == "excellent"
```

**Run tests**: `cd backend && pytest` (no additional config needed)

---

## Development Workflows

### Startup (Recommended)
```powershell
.\run_all.ps1  # Finds available ports, starts backend + frontend, monitors logs
```
Backend: `http://127.0.0.1:8000/docs` | Frontend: `http://localhost:5173`

### Backend Only
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn main:app --port 8000 --reload
```

### Database Migrations
```powershell
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Seed Synthetic Data
```powershell
cd backend
python -c "from app.services.synthetic_seed_service import ingest_seed_file; from app.db.database import SessionLocal; db=SessionLocal(); ingest_seed_file(db, 'data/synthetic_profiles.json', batch_id='BATCH_001')"
```

---

## Critical File Locations

- **Core scoring logic**: [backend/app/services/scoring_service.py](backend/app/services/scoring_service.py)
- **Feature orchestration**: [backend/app/services/feature_pipeline_service.py](backend/app/services/feature_pipeline_service.py)
- **Database models**: [backend/app/models/models.py](backend/app/models/models.py)
- **API routes**: [backend/app/api/scoring_v2.py](backend/app/api/scoring_v2.py)
- **Rule evaluation**: [backend/app/rules/evaluator.py](backend/app/rules/evaluator.py) (uses `simpleeval` for safe expression parsing)
- **Database connection**: [backend/app/db/database.py](backend/app/db/database.py) (auto-fallback to SQLite if Postgres unavailable)

---

## Integration Points

### External Dependencies
- **PostgreSQL 15**: Primary database (Docker: `postgres:15-alpine`)
- **Fallback**: SQLite auto-enabled if Postgres unreachable (see [database.py](backend/app/db/database.py#L24))

### Cross-Component Communication
- Frontend → Backend: REST API (axios) at `http://localhost:8000/api/*`
- React Router v7 for SPA routing
- Recharts for score visualizations
- ReactFlow for network graph rendering

---

## When Adding Features

1. **New API endpoint**: Create route in `backend/app/api/`, include in [main.py](backend/main.py) routers
2. **New feature extractor**: Inherit `BaseFeatureExtractor`, implement `extract()` + `get_source_type()`, register in `FeaturePipelineService.__init__()`
3. **New data source**: Create adapter inheriting `BaseAdapter`, register in `AdapterRegistry`
4. **Database schema change**: Create Alembic migration, update models in [models.py](backend/app/models/models.py)
5. **Always write tests**: Follow pattern in [tests/test_scorecard_service.py](backend/tests/test_scorecard_service.py)

---

## Common Gotchas

- **Circular imports**: Import models at function level if needed, not module level
- **Session leaks**: Always use `get_db()` dependency, never `SessionLocal()` in routes
- **Enum serialization**: Store as strings, convert to enum only when needed
- **Port conflicts**: `run_all.ps1` auto-detects and resolves conflicts
- **Postgres unavailable**: Code gracefully falls back to SQLite—check logs for `[FALLBACK] Using SQLite`

Explain anything you do in beginner language