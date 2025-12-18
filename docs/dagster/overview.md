# Dagster Overview

Dagster orchestrates the KYCC data pipelines for batch processing, ML training, and scorecard refinement.

## Overview

| Property | Value |
|----------|-------|
| Location | `backend/dagster_home/` |
| UI Port | 3000 |
| Configuration | `dagster.yaml` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Dagster Architecture                         │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                      Dagster Webserver                      │  │
│   │                    http://localhost:3000                    │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                               │                                     │
│                               ▼                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                        Dagster Daemon                       │  │
│   │              (Schedules, Sensors, Run Queue)                │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                               │                                     │
│                               ▼                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │                     Asset Definitions                       │  │
│   │   ┌─────────────────────────────────────────────────────┐  │  │
│   │   │  ingest_synthetic_batch                             │  │  │
│   │   │         │                                           │  │  │
│   │   │         ▼                                           │  │  │
│   │   │  extract_features ─────────────────┐                │  │  │
│   │   │         │                          │                │  │  │
│   │   │         ▼                          ▼                │  │  │
│   │   │  score_batch              extract_kyc_features      │  │  │
│   │   │         │                 extract_txn_features      │  │  │
│   │   │         │                 extract_network_features  │  │  │
│   │   │         ▼                          │                │  │  │
│   │   │  generate_scorecard_labels ◄───────┘                │  │  │
│   │   │         │                                           │  │  │
│   │   │         ▼                                           │  │  │
│   │   │  train_model_asset                                  │  │  │
│   │   │         │                                           │  │  │
│   │   │         ▼                                           │  │  │
│   │   │  refine_scorecard                                   │  │  │
│   │   └─────────────────────────────────────────────────────┘  │  │
│   └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
backend/dagster_home/
├── definitions.py      # Asset and job definitions
├── sensors.py          # Event-driven triggers
├── dagster.yaml        # Dagster configuration
└── workspace.yaml      # Workspace configuration
```

---

## Starting Dagster

### Development

```bash
cd backend
dagster dev -f dagster_home/definitions.py
```

### Production

```bash
# Start webserver
dagster-webserver -f dagster_home/definitions.py

# Start daemon (separate process)
dagster-daemon run -f dagster_home/definitions.py
```

### Docker

```yaml
# docker-compose.yml
dagster:
  image: dagster/dagster-k8s
  ports:
    - "3000:3000"
  volumes:
    - ./dagster_home:/opt/dagster/dagster_home
  environment:
    - DAGSTER_HOME=/opt/dagster/dagster_home
```

---

## Configuration

### dagster.yaml

```yaml
scheduler:
  module: dagster.core.scheduler
  class: DagsterDaemonScheduler

run_queue:
  max_concurrent_runs: 5

run_monitoring:
  enabled: true
  poll_interval_seconds: 60

telemetry:
  enabled: false
```

### workspace.yaml

```yaml
load_from:
  - python_file:
      relative_path: definitions.py
      location_name: kycc_scoring
```

---

## Resource Configuration

Resources provide database connections and service instances:

```python
from dagster import resource

@resource
def database_resource(context):
    """Provide database session."""
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@resource
def scoring_service_resource(context):
    """Provide scoring service."""
    from app.services.scoring_service import ScoringService
    db = context.resources.database
    return ScoringService(db)
```

---

## Running Jobs

### Via UI

1. Navigate to `http://localhost:3000`
2. Select job from left sidebar
3. Click "Launchpad"
4. Configure run config
5. Click "Launch Run"

### Via CLI

```bash
dagster job execute -f dagster_home/definitions.py -j full_scoring_job \
  --config '{"ops": {"ingest_synthetic_batch": {"config": {"batch_id": "BATCH_001"}}}}'
```

### Via API

```python
from dagster import DagsterInstance
from dagster_home.definitions import full_scoring_job

instance = DagsterInstance.get()
result = full_scoring_job.execute_in_process(
    run_config={
        "ops": {
            "ingest_synthetic_batch": {
                "config": {"batch_id": "BATCH_001"}
            }
        }
    },
    instance=instance
)
```

---

## Monitoring

### Run History

View in UI at `http://localhost:3000/runs`

### Logs

```python
@asset
def my_asset(context):
    context.log.info("Processing started")
    context.log.warning("Low sample count")
    context.log.error("Processing failed")
```

### Metrics

Custom metrics via Dagster events:

```python
from dagster import Output, AssetMaterialization

@asset
def score_batch(context, extract_features):
    # ... scoring logic ...
    
    yield AssetMaterialization(
        asset_key="score_batch",
        metadata={
            "parties_scored": len(results),
            "avg_score": statistics.mean(scores),
            "processing_time_seconds": elapsed
        }
    )
    
    yield Output(results)
```

---

## Best Practices

1. **Idempotency**: Assets should produce same output for same input
2. **Atomic Operations**: Use database transactions
3. **Error Handling**: Catch and log errors, allow retries
4. **Configuration**: Use run config for runtime parameters
5. **Testing**: Test assets in isolation with mock data
6. **Partitioning**: Use partitions for large batch processing
