# Running Tests

This guide covers how to run tests for the KYCC backend.

## Quick Start

```bash
cd backend
pytest
```

---

## Prerequisites

### Virtual Environment

```bash
# Windows
cd backend
.\venv\Scripts\Activate.ps1

# Linux/Mac
cd backend
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Running Tests

### All Tests

```bash
pytest
```

### Specific Test File

```bash
pytest tests/test_scorecard_service.py
```

### Specific Test Function

```bash
pytest tests/test_scorecard_service.py::test_compute_score
```

### Tests Matching Pattern

```bash
pytest -k "score"           # Tests containing "score"
pytest -k "not slow"        # Exclude slow tests
pytest -k "score and batch" # Multiple patterns
```

---

## Output Options

### Verbose Output

```bash
pytest -v                 # Verbose
pytest -vv                # Very verbose
pytest -vvv               # Maximum verbosity
```

### Show Print Statements

```bash
pytest -s
```

### Show Test Durations

```bash
pytest --durations=10     # Show 10 slowest tests
pytest --durations=0      # Show all test durations
```

### Stop on First Failure

```bash
pytest -x                 # Stop on first failure
pytest --maxfail=3        # Stop after 3 failures
```

---

## Coverage Reports

### Basic Coverage

```bash
pytest --cov=app
```

### HTML Report

```bash
pytest --cov=app --cov-report=html
```

Opens: `backend/htmlcov/index.html`

### Terminal Report with Missing Lines

```bash
pytest --cov=app --cov-report=term-missing
```

### XML Report (for CI)

```bash
pytest --cov=app --cov-report=xml
```

---

## Test Categories

### Run by Marker

```bash
pytest -m slow            # Only slow tests
pytest -m "not slow"      # Exclude slow tests
pytest -m integration     # Only integration tests
```

### Run by Directory

```bash
pytest tests/             # All tests in directory
pytest tests/unit/        # Only unit tests
pytest tests/integration/ # Only integration tests
```

---

## Parallel Execution

### Install pytest-xdist

```bash
pip install pytest-xdist
```

### Run in Parallel

```bash
pytest -n auto            # Use all CPU cores
pytest -n 4               # Use 4 processes
```

---

## Debugging

### Drop into Debugger on Failure

```bash
pytest --pdb
```

### Drop into Debugger at Start

```bash
pytest --pdb --pdbcls=IPython.terminal.debugger:Pdb
```

### Run Last Failed Tests

```bash
pytest --lf               # Last failed
pytest --ff               # Failed first, then rest
```

---

## Configuration

### pytest.ini

Create `backend/pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
python_classes = Test*
addopts = -v --tb=short
markers =
    slow: marks tests as slow
    integration: marks integration tests
filterwarnings =
    ignore::DeprecationWarning
```

### pyproject.toml Alternative

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"
```

---

## Test Database

### Default Configuration

Tests automatically use SQLite (`test_run.db`) set in `conftest.py`:

```python
os.environ["DATABASE_URL"] = "sqlite:///test_run.db"
```

### Fresh Database Each Run

The test database is deleted at the start of each test run:

```python
test_db = Path("test_run.db")
if test_db.exists():
    test_db.unlink()
```

### In-Memory Database (Faster)

For even faster tests, modify `conftest.py`:

```python
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
```

---

## Common Commands

### Development Workflow

```bash
# Run all tests with coverage
pytest --cov=app -v

# Run only failed tests from last run
pytest --lf -v

# Run tests matching pattern
pytest -k "score" -v

# Run with maximum output
pytest -vvs --tb=long
```

### CI/CD Commands

```bash
# Full test suite with XML coverage
pytest --cov=app --cov-report=xml --junitxml=results.xml

# Parallel execution for speed
pytest -n auto --cov=app

# Fail if coverage below threshold
pytest --cov=app --cov-fail-under=80
```

### Quick Checks

```bash
# Syntax check only (no execution)
pytest --collect-only

# Show test items that would run
pytest --collect-only -q

# List available markers
pytest --markers

# List available fixtures
pytest --fixtures
```

---

## Troubleshooting

### Import Errors

Ensure you are in the backend directory:

```bash
cd backend
pytest tests/
```

### Database Errors

Delete test database and retry:

```bash
# Windows
del test_run.db

# Linux/Mac
rm test_run.db
```

### Module Not Found

Install package in editable mode:

```bash
pip install -e .
```

### Fixture Not Found

Check conftest.py is in the tests directory and fixtures are properly decorated.

---

## Test Output Example

```
================================ test session starts ================================
platform win32 -- Python 3.11.0, pytest-7.4.0
rootdir: c:\Users\Anshu\Desktop\KYCC\backend
configfile: pytest.ini
plugins: cov-4.1.0
collected 24 items

tests/test_adapter_registry.py::test_register_adapter PASSED               [  4%]
tests/test_adapter_registry.py::test_get_adapter PASSED                    [  8%]
tests/test_feature_pipeline.py::test_extract_kyc_features PASSED           [ 12%]
tests/test_feature_pipeline.py::test_extract_transaction_features PASSED   [ 16%]
tests/test_feature_pipeline.py::test_extract_network_features PASSED       [ 20%]
tests/test_rule_evaluator.py::test_simple_rule PASSED                      [ 25%]
tests/test_rule_evaluator.py::test_complex_rule PASSED                     [ 29%]
tests/test_scorecard_service.py::test_compute_score PASSED                 [ 33%]
tests/test_scorecard_service.py::test_score_breakdown PASSED               [ 37%]
tests/test_scorecard_service.py::test_batch_scoring PASSED                 [ 41%]
tests/test_ttl_cache.py::test_cache_set_get PASSED                         [ 45%]
tests/test_ttl_cache.py::test_cache_expiration PASSED                      [ 50%]
...

================================ 24 passed in 2.45s =================================
```
