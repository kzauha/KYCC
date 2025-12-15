# System Architecture

## Overview

KYCC follows a modular, service-oriented architecture with clear separation of concerns across the data flow pipeline.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                       │
│  React + Vite │ Streamlit │ API Clients                   │
└─────────────────────────────────────────────────────────────┘
                           ↓ HTTP/REST
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                      │
│         FastAPI Routers (CORS, Validation, Auth)           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                          │
│  ScoringService │ FeaturePipelineService │ NetworkService  │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Extractor Layer                          │
│  KYC │ Transaction │ Network │ [Future Extractors]         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    Data Access Layer                        │
│           SQLAlchemy ORM + Session Management               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                     Database Layer                          │
│         PostgreSQL 15 (Primary) │ SQLite (Fallback)        │
└─────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### API Layer (`backend/app/api/`)

**Purpose**: HTTP endpoint handlers with validation

**Components**:
- `parties.py` - Party CRUD operations
- `relationships.py` - Relationship management
- `scoring.py` - Legacy scoring endpoints
- `scoring_v2.py` - Enhanced scoring with caching
- `synthetic.py` - Test data generation

**Responsibilities**:
- Request validation (Pydantic)
- Response serialization
- Error handling
- Database session injection

### Service Layer (`backend/app/services/`)

**Purpose**: Business logic orchestration

**Components**:
- `scoring_service.py` - Credit score computation
- `feature_pipeline_service.py` - Feature extraction orchestration
- `scorecard_service.py` - Scorecard model management
- `network_service.py` - Graph traversal algorithms
- `synthetic_seed_service.py` - Test data ingestion

**Responsibilities**:
- Coordinate extractors
- Apply business rules
- Manage scoring models
- Audit logging

### Extractor Layer (`backend/app/extractors/`)

**Purpose**: Feature extraction from raw data

**Components**:
- `base_extractor.py` - Abstract base class
- `kyc_extractor.py` - KYC compliance features
- `transaction_extractor.py` - Transaction patterns
- `network_extractor.py` - Supply chain graph metrics

**Responsibilities**:
- Compute features from raw data
- Handle missing data gracefully
- Tag features with metadata
- Return normalized results

### Data Models (`backend/app/models/`)

**Purpose**: Database schema definitions

**Key Models**:
- `Party` - Companies in supply chain
- `Relationship` - Supply chain connections
- `Transaction` - Payment/shipment history
- `Feature` - Extracted signals (versioned)
- `ScoreRequest` - Audit log
- `ModelRegistry` - Scoring models
- `DecisionRule` - Business rules

### Adapters (`backend/app/adapters/`)

**Purpose**: Normalize external data sources

**Components**:
- `base.py` - Adapter interface
- `synthetic_adapter.py` - Test data adapter
- `registry.py` - Adapter registration

**Pattern**: Transform heterogeneous input → standardized Party schema

### Rules Engine (`backend/app/rules/`)

**Purpose**: Evaluate decision rules on features

**Components**:
- `evaluator.py` - Safe expression evaluation
- `schema.py` - Rule validation schemas

**Capabilities**:
- Python expression evaluation
- Priority-based rule matching
- Safe execution (no `eval` risks)

### Cache Layer (`backend/app/cache/`)

**Purpose**: In-memory feature caching

**Components**:
- `ttl_cache.py` - TTL-based cache
- `cache_key.py` - Key generation

**Features**:
- 5-minute TTL
- Thread-safe operations
- Automatic expiration

## Data Flow: Score Computation

```
1. API Request (POST /api/scoring/score/1)
        ↓
2. ScoringService.compute_score(party_id=1)
        ↓
3. Check cache for features (miss)
        ↓
4. FeaturePipelineService.extract_all_features()
        ↓
5. Parallel extractor execution:
   - KYCExtractor → 4 features
   - TransactionExtractor → 4 features
   - NetworkExtractor → 3 features
        ↓
6. Store features in DB (versioned)
        ↓
7. Cache features (5 min TTL)
        ↓
8. Fetch active scorecard model
        ↓
9. Normalize features (0-1 scale)
        ↓
10. Apply weighted scorecard formula
        ↓
11. Scale to 300-900 range
        ↓
12. Evaluate decision rules (priority order)
        ↓
13. Create ScoreRequest audit log
        ↓
14. Return ScoreResponse (JSON)
```

## Design Patterns

### Extractor Pattern
All extractors inherit `BaseFeatureExtractor`:
```python
class BaseFeatureExtractor(ABC):
    @abstractmethod
    def extract(self, party_id: int, db: Session) -> List[FeatureExtractorResult]
    
    @abstractmethod
    def get_source_type(self) -> str
```

**Benefits**:
- Pluggable extractors
- Consistent interface
- Easy to test in isolation

### Adapter Pattern
External data sources implement `BaseAdapter`:
```python
class BaseAdapter(ABC):
    @abstractmethod
    def parse(self, data: dict) -> dict
    
    @abstractmethod
    def validate(self, data: dict) -> bool
```

**Benefits**:
- Normalize heterogeneous inputs
- Swap data sources without changing logic
- Easy to add new integrations

### Repository Pattern
Database access through session dependency:
```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/api/parties/{id}")
def get_party(id: int, db: Session = Depends(get_db)):
    return db.query(Party).filter(Party.id == id).first()
```

**Benefits**:
- Automatic session management
- No session leaks
- Testable (mock db dependency)

### Strategy Pattern
Scoring models are pluggable via `ModelRegistry`:
```python
model = db.query(ModelRegistry)\
    .filter(ModelRegistry.is_active == 1)\
    .first()

if model.model_type == "scorecard":
    score = apply_scorecard(features, model.weights)
elif model.model_type == "xgboost":
    score = apply_ml_model(features, model.model_config)
```

**Benefits**:
- Swap scoring algorithms without code changes
- A/B test models
- Rollback to previous model versions

## Scalability Considerations

### Horizontal Scaling
- **Stateless API**: No in-memory state (except cache)
- **Database pooling**: Connection reuse
- **Load balancer**: Distribute requests across instances

### Caching Strategy
- **Feature cache**: Avoid recomputing expensive features
- **TTL expiration**: Balance freshness vs performance
- **Cache invalidation**: On feature updates

### Database Optimization
- **Indices**: On `party_id`, `feature_name`, `valid_to`
- **Partitioning**: By `request_timestamp` for audit logs
- **Read replicas**: Separate read/write workloads

### Async Processing
- **Background tasks**: Long-running feature extraction
- **Message queue**: Celery/RabbitMQ for batch scoring
- **Webhooks**: Notify on score changes

## Security Considerations

### API Security
- **CORS**: Restricted origins
- **Rate limiting**: Prevent abuse
- **Authentication**: OAuth2/JWT (future)
- **Input validation**: Pydantic schemas

### Database Security
- **Prepared statements**: SQLAlchemy ORM (no SQL injection)
- **Encrypted connections**: TLS for Postgres
- **Credential management**: Environment variables

### Rule Evaluation Safety
- **No `eval()`**: Use `simpleeval` library
- **Restricted builtins**: No file system access
- **Expression timeout**: Prevent infinite loops

## Monitoring & Observability

### Logging
- **Structured logs**: JSON format
- **Log levels**: DEBUG, INFO, WARNING, ERROR
- **Request IDs**: Trace requests across services

### Metrics
- **Response times**: Per endpoint
- **Error rates**: 4xx/5xx counts
- **Feature extraction latency**: Per extractor
- **Cache hit rate**: Feature cache effectiveness

### Tracing
- **Distributed tracing**: OpenTelemetry (future)
- **Database query profiling**: Slow query logs
- **Audit logs**: All score computations

## Technology Stack

| Component | Technology | Reason |
|-----------|-----------|--------|
| API Framework | FastAPI | Async, type hints, auto-generated docs |
| ORM | SQLAlchemy 2.x | Modern async, relationships, migrations |
| Database | PostgreSQL 15 | JSON support, recursive CTEs, ACID |
| Validation | Pydantic v2 | Type safety, ORM mode, performance |
| Frontend | React + Vite | Fast HMR, component-based, modern |
| Alternate UI | Streamlit | Rapid prototyping, data apps |
| Caching | In-memory dict | Simple, thread-safe, TTL-based |
| Testing | pytest | Fixtures, parametrization, coverage |
| Containerization | Docker | Portable, isolated, reproducible |
