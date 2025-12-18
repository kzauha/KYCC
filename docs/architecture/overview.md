# System Architecture Overview

This document provides a comprehensive overview of the KYCC system architecture.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend (React + Vite)                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │
│  │  Dashboard   │ │ ML Dashboard │ │  Party List  │ │  Network Graph   │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────────┘   │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ REST API (HTTP/JSON)
┌────────────────────────────────────▼────────────────────────────────────────┐
│                           FastAPI Backend                                   │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                        API Layer (Routers)                         │    │
│  │  /api/scoring  │  /api/pipeline  │  /api/parties  │  /api/...     │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                       Service Layer                                │    │
│  │  ScoringService │ FeaturePipelineService │ ModelTrainingService   │    │
│  │  LabelGenerationService │ ScorecardVersionService │ Analytics     │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                      Domain Layer                                  │    │
│  │  Extractors │ Scorecard Engine │ Rule Evaluator │ Adapters        │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                        │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    Data Access Layer                               │    │
│  │  SQLAlchemy ORM │ Session Management │ CRUD Operations            │    │
│  └────────────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────────┐
│                         Dagster Pipeline                                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │  Ingest    │ │  Features  │ │   Score    │ │   Train    │              │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘              │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────────┐
│                    PostgreSQL Database                                      │
│  parties │ transactions │ relationships │ features │ scores │ models       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Layers

### 1. Presentation Layer (Frontend)

The React frontend provides user interfaces for:

| Component | Purpose |
|-----------|---------|
| Dashboard | Pipeline management, batch monitoring |
| ML Dashboard | Scorecard versions, weight evolution |
| Party List | CRUD operations for parties |
| Party Detail | Individual party view with scoring |
| Network Graph | Supply chain visualization |
| Credit Score | Score visualization |

**Technology**: React 18, Vite, React Router v7, Recharts, ReactFlow

### 2. API Layer

FastAPI routers expose RESTful endpoints:

| Router | Prefix | Responsibility |
|--------|--------|----------------|
| `scoring_v2` | `/api/scoring` | Score computation, history, versions |
| `pipeline` | `/api/pipeline` | Batch management, training triggers |
| `parties` | `/api/parties` | Party CRUD |
| `relationships` | `/api/relationships` | Relationship CRUD |
| `synthetic` | `/synthetic` | Synthetic data ingestion |

**Location**: `backend/app/api/`

### 3. Service Layer

Business logic services orchestrate operations:

| Service | Responsibility |
|---------|----------------|
| `ScoringService` | Score computation, model application |
| `FeaturePipelineService` | Feature extraction orchestration |
| `ModelTrainingService` | ML model training |
| `LabelGenerationService` | Ground truth label creation |
| `ScorecardVersionService` | Scorecard version management |
| `AnalyticsService` | Analytics and reporting |
| `NetworkService` | Network graph traversal |

**Location**: `backend/app/services/`

### 4. Domain Layer

Core business logic components:

| Component | Responsibility |
|-----------|----------------|
| Feature Extractors | Extract features from raw data |
| Scorecard Engine | Apply scorecard weights to features |
| Rule Evaluator | Evaluate business rules |
| Adapters | Normalize data from various sources |
| Validators | Validate data quality |

**Locations**: 
- `backend/app/extractors/`
- `backend/app/scorecard/`
- `backend/app/rules/`
- `backend/app/adapters/`
- `backend/app/validators/`

### 5. Data Access Layer

Database interaction through SQLAlchemy:

| Component | Responsibility |
|-----------|----------------|
| Models | SQLAlchemy table definitions |
| Database | Engine and session management |
| CRUD | Database operations |

**Location**: `backend/app/db/`, `backend/app/models/`

### 6. Pipeline Layer (Dagster)

Data pipeline orchestration:

| Asset | Responsibility |
|-------|----------------|
| `ingest_synthetic_batch` | Load data from files |
| `features_all` | Extract all features |
| `score_batch` | Score all parties |
| `generate_scorecard_labels` | Create training labels |
| `train_model_asset` | Train ML model |
| `refine_scorecard` | Update scorecard weights |

**Location**: `backend/dagster_home/definitions.py`

---

## Key Design Patterns

### 1. Extractor Pattern

All feature extractors inherit from `BaseFeatureExtractor`:

```python
class BaseFeatureExtractor:
    def get_source_type(self) -> str:
        """Return source type identifier."""
        pass
    
    def extract(self, party_id: int, db: Session, as_of_date: datetime = None) -> List[FeatureExtractorResult]:
        """Extract features for a party."""
        pass
```

This pattern enables:
- Consistent interface across extractors
- Easy addition of new feature sources
- Traceability through `source_type` metadata

### 2. Adapter Pattern

Data adapters normalize inputs from various sources:

```python
class BaseAdapter:
    def parse(self, data: dict) -> dict:
        """Parse raw data into standard schema."""
        pass
```

Registry pattern enables runtime adapter selection:

```python
AdapterRegistry.register("synthetic", SyntheticAdapter)
adapter = AdapterRegistry.get("synthetic")
```

### 3. Service Layer Pipeline

All scoring follows a consistent flow:

```
API Router
    └── ScoringService.compute_score()
            ├── FeaturePipelineService.extract_all_features()
            │       ├── KYCFeatureExtractor.extract()
            │       ├── TransactionFeatureExtractor.extract()
            │       └── NetworkFeatureExtractor.extract()
            ├── ScorecardEngine.compute_scorecard_score()
            ├── RuleEvaluator.evaluate()
            └── ScoreRequest (audit log)
```

### 4. Temporal Versioning

Features use `valid_from`/`valid_to` for versioning:

- `valid_to = NULL` indicates current version
- New features expire old ones
- Historical queries use date-based filtering

---

## Communication Patterns

### Frontend to Backend

- Protocol: HTTP/JSON
- Authentication: None (development), JWT (production)
- Error Handling: HTTP status codes with JSON error bodies

### Backend to Database

- ORM: SQLAlchemy 2.x
- Connection Pooling: Built-in pool
- Transactions: Per-request sessions

### Dagster to Backend

- Shared database connection
- Direct Python imports of services
- Asset dependencies for ordering

---

## Scalability Considerations

### Horizontal Scaling

- **Backend**: Stateless, can run multiple instances
- **Database**: Read replicas for reporting
- **Dagster**: Distributed execution with Dagster+

### Performance Optimizations

- TTL cache for feature lookups (5-minute default)
- Batch processing for large datasets
- Index optimization on frequently queried columns
- Lazy loading for relationships

### Bottleneck Mitigation

| Bottleneck | Mitigation |
|------------|------------|
| Database connections | Connection pooling |
| Feature extraction | Parallel extractors |
| Large batches | Chunked processing |
| Network graph traversal | Depth limits |
