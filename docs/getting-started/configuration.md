# Configuration

This guide covers all configuration options for KYCC.

## Environment Variables

### Database Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://localhost/kycc_db` | Full database connection string |
| `POSTGRES_USER` | `kycc_user` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `kycc_pass` | PostgreSQL password |
| `POSTGRES_DB` | `kycc_db` | PostgreSQL database name |
| `POSTGRES_PORT` | `5433` | PostgreSQL port |
| `POSTGRES_HOST` | `localhost` | PostgreSQL host |

### Application Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_CREATE_TABLES` | `0` | Auto-create tables on startup (1=yes, 0=no) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `FORCE_SQLITE_FALLBACK` | `0` | Force SQLite instead of PostgreSQL |

### Dagster Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DAGSTER_HOME` | `./dagster_instance` | Dagster instance directory |
| `PYTHONPATH` | `.` | Python path for imports |

---

## Configuration Files

### Backend Environment File

Location: `backend/.env`

```env
# Database
DATABASE_URL=postgresql://kycc_user:kycc_pass@localhost:5433/kycc_db
POSTGRES_USER=kycc_user
POSTGRES_PASSWORD=kycc_pass
POSTGRES_DB=kycc_db
POSTGRES_PORT=5433

# Application Settings
AUTO_CREATE_TABLES=1
LOG_LEVEL=INFO

# Dagster
DAGSTER_HOME=./dagster_instance
```

### Alembic Configuration

Location: `backend/alembic.ini`

Key settings:

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql://kycc_user:kycc_pass@localhost:5433/kycc_db

[logging]
level = INFO
```

### Dagster Configuration

Location: `backend/dagster_instance/dagster.yaml`

```yaml
storage:
  sqlite:
    base_dir: ./dagster_instance/history

run_launcher:
  module: dagster.core.launcher
  class: DefaultRunLauncher

run_coordinator:
  module: dagster.core.run_coordinator
  class: DefaultRunCoordinator

telemetry:
  enabled: false
```

### Dagster Workspace

Location: `backend/dagster_home/workspace.yaml`

```yaml
load_from:
  - python_file:
      relative_path: definitions.py
      working_directory: /workspace/dagster_home
```

---

## Scorecard Configuration

The default scorecard configuration is defined in `backend/app/scorecard/scorecard_config.py`:

```python
INITIAL_SCORECARD_V1 = {
    'version': '1.0',
    'base_score': 300,
    'max_score': 900,
    'target_default_rate': 0.05,
    
    'weights': {
        # KYC Features
        'kyc_verified': 15,
        'has_tax_id': 10,
        'contact_completeness': 5,
        
        # Company Profile
        'company_age_years': 10,
        'party_type_score': 10,
        
        # Transaction Features
        'transaction_count_6m': 20,
        'avg_transaction_amount': 15,
        'recent_activity_flag': 25,
        'transaction_regularity_score': 15,
        
        # Network Features
        'network_size': 10,
        'direct_counterparty_count': 10,
        'network_balance_ratio': 10,
        'network_depth_downstream': 10,
    },
    
    'feature_scaling': {
        'company_age_years': {'max_value': 5, 'method': 'cap'},
        'transaction_count_6m': {'max_value': 50, 'method': 'cap'},
        'avg_transaction_amount': {'max_value': 100000, 'method': 'log_scale'},
        'network_size': {'max_value': 20, 'method': 'cap'},
        'direct_counterparty_count': {'max_value': 10, 'method': 'cap'},
        'network_depth_downstream': {'max_value': 5, 'method': 'cap'},
    }
}
```

### Modifying Scorecard Weights

To modify the scorecard:

1. **Through the database**: Update the `scorecard_versions` table
2. **Through ML refinement**: Run the training pipeline to create a new version
3. **Through code**: Modify `scorecard_config.py` (requires restart)

---

## CORS Configuration

Location: `backend/main.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Add additional origins as needed for production deployments.

---

## ML Pipeline Configuration

### Quality Gates

Located in `backend/app/services/scorecard_version_service.py`:

```python
MIN_AUC_THRESHOLD = 0.55      # Minimum AUC to accept model
IMPROVEMENT_THRESHOLD = 0.005  # Required improvement over current (0.5%)
```

### Model Training Defaults

Located in `backend/app/services/model_training_service.py`:

```python
default_hyperparams = {
    'C': 1.0,
    'penalty': 'l2',
    'max_iter': 1000,
    'solver': 'lbfgs',
    'class_weight': 'balanced'
}
```

---

## Cache Configuration

The TTL cache is configured in `backend/app/cache/ttl_cache.py`:

```python
DEFAULT_TTL = 300  # 5 minutes
MAX_CACHE_SIZE = 1000
```

Cache key format: `party:{party_id}:features:all`

---

## Docker Configuration

### docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "${POSTGRES_PORT:-5433}:5432"
    volumes:
      - kycc_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

  dagster:
    build: ./backend
    command: dagster-webserver -h 0.0.0.0 -p 3000
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      DAGSTER_HOME: /workspace/dagster_instance
    ports:
      - "3000:3000"
```

---

## Production Configuration

For production deployments:

### Security

```env
# Use strong passwords
POSTGRES_PASSWORD=<strong-random-password>

# Disable auto table creation
AUTO_CREATE_TABLES=0

# Restrict CORS origins
# Modify main.py allow_origins list
```

### Performance

```env
# Increase worker count
UVICORN_WORKERS=4

# Enable connection pooling
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

### Logging

```env
LOG_LEVEL=WARNING
LOG_FORMAT=json
```
