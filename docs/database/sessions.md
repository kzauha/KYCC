# Session Management

This document covers database session management patterns in KYCC.

## Overview

KYCC uses SQLAlchemy 2.x for database operations with a dependency injection pattern for session management.

## Database Connection

### Location
`backend/app/db/database.py`

### Engine Creation

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://localhost/kycc_db"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

### Automatic Fallback

KYCC implements automatic fallback to SQLite if PostgreSQL is unavailable:

```python
def _test_engine_connection(engine, timeout: float = 2.0) -> bool:
    """Test if database connection works."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

# If PostgreSQL fails, fall back to SQLite
if not _test_engine_connection(engine):
    print("[FALLBACK] Using SQLite")
    engine = create_engine("sqlite:///kycc_local.db")
```

---

## Session Dependency Injection

### The get_db Pattern

All API routes use dependency injection for database sessions:

```python
def get_db():
    """
    Dependency that provides a database session.
    Session is automatically closed after request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Usage in Routes

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.database import get_db

@router.get("/parties/{party_id}")
def get_party(party_id: int, db: Session = Depends(get_db)):
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    return party
```

---

## Session Lifecycle

### Request Lifecycle

```
1. Request arrives at FastAPI endpoint
2. Depends(get_db) creates new SessionLocal()
3. Session is passed to route handler
4. Route handler performs database operations
5. Route returns response
6. finally block calls db.close()
7. Connection returned to pool
```

### Context Manager Pattern

For non-request contexts (scripts, Dagster):

```python
with SessionLocal() as db:
    # Perform database operations
    result = db.query(Party).all()
    # Session automatically closed on exit
```

Or using try/finally:

```python
db = SessionLocal()
try:
    result = db.query(Party).all()
finally:
    db.close()
```

---

## Transaction Management

### Auto-commit Disabled

Sessions are created with `autocommit=False`, requiring explicit commits:

```python
def create_party(db: Session, party_data: dict):
    party = Party(**party_data)
    db.add(party)
    db.commit()
    db.refresh(party)
    return party
```

### Rollback on Error

```python
def create_party_with_transactions(db: Session, data: dict):
    try:
        party = Party(**data["party"])
        db.add(party)
        
        for txn_data in data["transactions"]:
            txn = Transaction(party_id=party.id, **txn_data)
            db.add(txn)
        
        db.commit()
    except Exception:
        db.rollback()
        raise
```

### Nested Transactions

For complex operations requiring partial rollback:

```python
from sqlalchemy import savepoint

def complex_operation(db: Session):
    # Main transaction
    party = Party(name="Test")
    db.add(party)
    
    # Savepoint for nested operation
    sp = db.begin_nested()
    try:
        risky_operation(db)
        sp.commit()
    except Exception:
        sp.rollback()
        # Main transaction continues
    
    db.commit()
```

---

## Common Patterns

### Query Patterns

```python
# Single record by primary key
party = db.query(Party).get(party_id)

# Single record with filter
party = db.query(Party).filter(Party.external_id == ext_id).first()

# Multiple records
parties = db.query(Party).filter(Party.batch_id == batch_id).all()

# Count
count = db.query(Party).filter(Party.batch_id == batch_id).count()

# Exists check
exists = db.query(Party).filter(Party.external_id == ext_id).first() is not None
```

### Bulk Operations

```python
# Bulk insert
db.bulk_insert_mappings(Party, party_dicts)
db.commit()

# Bulk update
db.query(Feature).filter(
    Feature.party_id == party_id,
    Feature.valid_to == None
).update({"valid_to": datetime.utcnow()})
db.commit()
```

### Eager Loading

To avoid N+1 queries:

```python
from sqlalchemy.orm import joinedload

# Load party with relationships
party = db.query(Party).options(
    joinedload(Party.relationships_from),
    joinedload(Party.relationships_to)
).filter(Party.id == party_id).first()
```

---

## Service Layer Sessions

Services receive sessions through their constructors:

```python
class ScoringService:
    def __init__(self, db: Session):
        self.db = db
    
    def compute_score(self, party_id: int) -> dict:
        # Use self.db for all database operations
        party = self.db.query(Party).get(party_id)
        ...
```

### Why Not Create Sessions in Services?

Creating sessions inside services leads to:

1. **Session leaks**: Forgotten closes
2. **Transaction confusion**: Multiple transactions per request
3. **Testing difficulty**: Hard to mock database
4. **Connection exhaustion**: Too many connections

Always inject sessions from the outer layer (route handler or script).

---

## Testing Sessions

### Test Isolation

Tests use SQLite with a fresh database:

```python
# conftest.py
import os
os.environ["DATABASE_URL"] = "sqlite:///test_run.db"

# Delete old test database
if Path("test_run.db").exists():
    Path("test_run.db").unlink()

# Import after setting environment
from app.db.database import engine, Base
Base.metadata.create_all(bind=engine)
```

### Test Fixtures

```python
import pytest
from app.db.database import SessionLocal

@pytest.fixture
def db():
    """Provide a database session for tests."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
```

---

## Connection Pooling

SQLAlchemy manages a connection pool automatically:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=5,           # Number of persistent connections
    max_overflow=10,       # Additional connections when pool exhausted
    pool_timeout=30,       # Seconds to wait for connection
    pool_recycle=1800,     # Recycle connections after 30 minutes
)
```

### Monitoring Pool

```python
from sqlalchemy import event

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    print(f"Connection checked out: {connection_record}")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    print(f"Connection checked in: {connection_record}")
```

---

## Best Practices

### Do

- Use `get_db` dependency in all routes
- Pass sessions to services via constructor
- Commit explicitly after writes
- Use `db.refresh()` after commit to get updated values
- Close sessions in finally blocks

### Do Not

- Create `SessionLocal()` directly in route handlers
- Store sessions in global variables
- Share sessions between threads
- Forget to close sessions
- Use autocommit mode
