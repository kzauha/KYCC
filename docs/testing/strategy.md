# Testing Strategy

This document outlines the testing approach for the KYCC credit scoring platform.

## Overview

| Property | Value |
|----------|-------|
| Framework | pytest |
| Database | SQLite (in-memory for tests) |
| Coverage Tool | pytest-cov |
| Location | `backend/tests/` |

---

## Testing Philosophy

1. **Real Database Operations**: Tests use real SQLAlchemy operations against SQLite, not mocks
2. **Isolation**: Each test run gets a fresh database
3. **Comprehensive**: Cover all service layers and edge cases
4. **Fast**: SQLite in-memory keeps tests fast

---

## Test Structure

```
backend/tests/
├── conftest.py                    # Shared fixtures
├── test_adapter_registry.py       # Adapter pattern tests
├── test_feature_pipeline.py       # Feature extraction tests
├── test_feature_service.py        # Feature service tests
├── test_iterative_learning.py     # ML refinement tests
├── test_rule_evaluator.py         # Decision rules tests
├── test_scorecard_persistence.py  # Scorecard storage tests
├── test_scorecard_service.py      # Scoring tests
├── test_synthetic_adapter.py      # Synthetic data tests
└── test_ttl_cache.py              # Cache tests
```

---

## Test Configuration

### conftest.py

```python
# backend/tests/conftest.py

import os
import sys
from pathlib import Path

# Set test database BEFORE any imports
os.environ["DATABASE_URL"] = "sqlite:///test_run.db"
os.environ["TESTING"] = "true"

# Delete existing test database
test_db = Path("test_run.db")
if test_db.exists():
    test_db.unlink()

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base, get_db
from app.models.models import *  # Import all models

# Create test engine
engine = create_engine(
    "sqlite:///test_run.db",
    connect_args={"check_same_thread": False}
)

# Create all tables
Base.metadata.create_all(bind=engine)

# Test session factory
TestingSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)


@pytest.fixture
def db():
    """Provide database session for tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_party(db):
    """Create a sample party for testing."""
    from app.models.models import Party
    
    party = Party(
        party_id="TEST-001",
        party_type="supplier",
        name="Test Supplier",
        kyc_score=75.0,
        company_age_days=1000,
        batch_id="TEST_BATCH"
    )
    db.add(party)
    db.commit()
    db.refresh(party)
    return party
```

---

## Test Categories

### Unit Tests

Test individual functions in isolation:

```python
# test_ttl_cache.py

import time
from app.cache.ttl_cache import TTLCache


def test_cache_set_get():
    """Test basic cache operations."""
    cache = TTLCache(default_ttl=60)
    
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"


def test_cache_expiration():
    """Test TTL expiration."""
    cache = TTLCache(default_ttl=1)  # 1 second TTL
    
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    
    time.sleep(1.5)
    assert cache.get("key1") is None


def test_cache_delete():
    """Test cache deletion."""
    cache = TTLCache(default_ttl=60)
    
    cache.set("key1", "value1")
    cache.delete("key1")
    assert cache.get("key1") is None
```

### Integration Tests

Test service interactions:

```python
# test_feature_pipeline.py

from app.services.feature_pipeline_service import FeaturePipelineService


def test_feature_extraction_pipeline(db, sample_party):
    """Test complete feature extraction."""
    service = FeaturePipelineService(db)
    
    features = service.extract_all_features(sample_party.party_id)
    
    assert len(features) > 0
    assert any(f.feature_name == "kyc_score" for f in features)
    assert any(f.feature_name == "company_age_days" for f in features)


def test_feature_extraction_with_transactions(db, sample_party):
    """Test feature extraction with transaction data."""
    from app.models.models import Transaction, Relationship
    
    # Create counterparty
    counterparty = Party(
        party_id="COUNTER-001",
        party_type="manufacturer",
        name="Counterparty Inc",
        batch_id="TEST_BATCH"
    )
    db.add(counterparty)
    
    # Create relationship
    rel = Relationship(
        party_id=sample_party.party_id,
        counterparty_id="COUNTER-001",
        relationship_type="customer"
    )
    db.add(rel)
    
    # Create transactions
    for i in range(5):
        txn = Transaction(
            party_id=sample_party.party_id,
            counterparty_id="COUNTER-001",
            amount=1000.0 + i * 100,
            currency="USD"
        )
        db.add(txn)
    
    db.commit()
    
    service = FeaturePipelineService(db)
    features = service.extract_all_features(sample_party.party_id)
    
    # Should have transaction features
    feature_names = [f.feature_name for f in features]
    assert "txn_count" in feature_names
    assert "avg_amount" in feature_names
```

### Service Tests

Test business logic:

```python
# test_scorecard_service.py

from app.services.scoring_service import ScoringService


def test_compute_score(db, sample_party):
    """Test score computation."""
    service = ScoringService(db)
    
    result = service.compute_score(sample_party.party_id)
    
    assert "total_score" in result
    assert 300 <= result["total_score"] <= 900
    assert result["band"] in ["excellent", "good", "fair", "poor", "very_poor"]


def test_score_breakdown(db, sample_party):
    """Test score breakdown components."""
    service = ScoringService(db)
    
    result = service.compute_score(sample_party.party_id)
    
    assert "breakdown" in result
    breakdown = result["breakdown"]
    
    # Should have component scores
    assert "kyc_score" in breakdown or "base_score" in breakdown


def test_batch_scoring(db):
    """Test scoring multiple parties."""
    # Create multiple parties
    for i in range(5):
        party = Party(
            party_id=f"BATCH-{i:03d}",
            party_type="supplier",
            name=f"Batch Party {i}",
            kyc_score=60 + i * 5,
            batch_id="BATCH_TEST"
        )
        db.add(party)
    db.commit()
    
    service = ScoringService(db)
    results = service.score_batch("BATCH_TEST")
    
    assert len(results) == 5
    assert all("total_score" in r for r in results)
```

### Rule Evaluator Tests

Test decision rules:

```python
# test_rule_evaluator.py

from app.rules.evaluator import RuleEvaluator


def test_simple_rule():
    """Test simple comparison rule."""
    evaluator = RuleEvaluator()
    
    rule = "score >= 700"
    context = {"score": 750}
    
    assert evaluator.evaluate(rule, context) is True


def test_complex_rule():
    """Test complex rule with multiple conditions."""
    evaluator = RuleEvaluator()
    
    rule = "score >= 700 and risk_flags == 0"
    context = {"score": 750, "risk_flags": 0}
    
    assert evaluator.evaluate(rule, context) is True


def test_rule_with_functions():
    """Test rule with function calls."""
    evaluator = RuleEvaluator()
    
    rule = "abs(score_change) < 50"
    context = {"score_change": -30}
    
    assert evaluator.evaluate(rule, context) is True


def test_invalid_rule():
    """Test handling of invalid rules."""
    evaluator = RuleEvaluator()
    
    result = evaluator.evaluate("invalid syntax {{{", {})
    
    assert result is False
```

---

## Fixtures

### Common Fixtures

```python
@pytest.fixture
def sample_party_with_history(db, sample_party):
    """Party with transaction history."""
    from app.models.models import Transaction
    from datetime import datetime, timedelta
    
    for i in range(10):
        txn = Transaction(
            party_id=sample_party.party_id,
            counterparty_id="COUNTER-001",
            amount=1000.0,
            transaction_date=datetime.utcnow() - timedelta(days=i*30)
        )
        db.add(txn)
    
    db.commit()
    return sample_party


@pytest.fixture
def sample_network(db, sample_party):
    """Party with network relationships."""
    from app.models.models import Relationship, Party
    
    for i in range(5):
        counterparty = Party(
            party_id=f"NETWORK-{i:03d}",
            party_type="distributor",
            name=f"Network Party {i}",
            batch_id="TEST_BATCH"
        )
        db.add(counterparty)
        
        rel = Relationship(
            party_id=sample_party.party_id,
            counterparty_id=f"NETWORK-{i:03d}",
            relationship_type="supplier"
        )
        db.add(rel)
    
    db.commit()
    return sample_party


@pytest.fixture
def scored_party(db, sample_party):
    """Party with existing score."""
    from app.services.scoring_service import ScoringService
    
    service = ScoringService(db)
    service.compute_score(sample_party.party_id)
    return sample_party
```

---

## Mocking Strategy

### When to Mock

- External API calls
- Time-dependent functions
- Random number generators
- File system operations (optional)

### What NOT to Mock

- Database operations
- Service layer interactions
- Model validations

### Mock Examples

```python
from unittest.mock import patch, MagicMock

def test_with_mocked_time():
    """Test time-dependent behavior."""
    with patch('app.cache.ttl_cache.time') as mock_time:
        mock_time.time.return_value = 1000
        
        cache = TTLCache(default_ttl=60)
        cache.set("key", "value")
        
        mock_time.time.return_value = 1100  # 100 seconds later
        assert cache.get("key") is None


def test_with_mocked_external_api():
    """Test with mocked external service."""
    with patch('app.adapters.external_adapter.requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"data": "value"}
        
        adapter = ExternalAdapter()
        result = adapter.fetch("endpoint")
        
        assert result == {"data": "value"}
```

---

## Test Coverage

### Generate Coverage Report

```bash
cd backend
pytest --cov=app --cov-report=html tests/
```

### Coverage Targets

| Module | Target |
|--------|--------|
| Services | 90% |
| Extractors | 85% |
| Rules | 95% |
| Models | 80% |
| API Routes | 75% |

---

## Best Practices

1. **One Assertion Focus**: Each test should verify one concept
2. **Descriptive Names**: Test names should describe what is tested
3. **Setup in Fixtures**: Move common setup to fixtures
4. **Clean Teardown**: Ensure tests clean up after themselves
5. **Independence**: Tests should not depend on execution order
6. **Fast Execution**: Keep tests fast for quick feedback
