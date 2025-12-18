# Dagster Jobs

Jobs define executable pipelines composed of assets or ops.

## Job Catalog

| Job | Description | Assets |
|-----|-------------|--------|
| full_scoring_job | Complete pipeline | All assets |
| ingest_job | Data ingestion only | ingest_synthetic_batch |
| feature_job | Feature extraction only | extract_* |
| scoring_job | Scoring only | score_batch |
| ml_training_job | ML pipeline only | generate_labels, train_model, refine_scorecard |

---

## Job Definitions

### full_scoring_job

Complete end-to-end pipeline.

```python
from dagster import define_asset_job, AssetSelection

full_scoring_job = define_asset_job(
    name="full_scoring_job",
    description="Complete scoring pipeline: ingest, extract, score, train, refine",
    selection=AssetSelection.all(),
    config={
        "ops": {
            "ingest_synthetic_batch": {
                "config": {
                    "batch_id": {"env": "BATCH_ID"},
                    "file_path": "data/synthetic_profiles.json"
                }
            },
            "score_batch": {
                "config": {
                    "scorecard_version": "v1"
                }
            },
            "train_model_asset": {
                "config": {
                    "min_samples": 100,
                    "test_size": 0.2
                }
            },
            "refine_scorecard": {
                "config": {
                    "blend_factor": 0.5
                }
            }
        }
    }
)
```

---

### ingest_job

Data ingestion only.

```python
ingest_job = define_asset_job(
    name="ingest_job",
    description="Ingest synthetic data",
    selection=AssetSelection.assets(ingest_synthetic_batch)
)
```

---

### feature_job

Feature extraction only.

```python
feature_job = define_asset_job(
    name="feature_job",
    description="Extract features for existing batch",
    selection=AssetSelection.assets(
        extract_features,
        extract_kyc_features,
        extract_txn_features,
        extract_network_features
    )
)
```

---

### scoring_job

Scoring only.

```python
scoring_job = define_asset_job(
    name="scoring_job",
    description="Score existing batch with extracted features",
    selection=AssetSelection.assets(score_batch)
)
```

---

### ml_training_job

ML training pipeline only.

```python
ml_training_job = define_asset_job(
    name="ml_training_job",
    description="Train ML model and refine scorecard",
    selection=AssetSelection.assets(
        generate_scorecard_labels,
        train_model_asset,
        refine_scorecard
    )
)
```

---

## Run Configuration

### Default Configuration

```python
default_config = {
    "ops": {
        "ingest_synthetic_batch": {
            "config": {
                "batch_id": "BATCH_001",
                "file_path": "data/synthetic_profiles.json"
            }
        }
    }
}
```

### Runtime Configuration

Jobs accept runtime configuration via Launchpad or API:

```python
from dagster import RunRequest

def create_run_request(batch_id: str):
    return RunRequest(
        run_key=batch_id,
        run_config={
            "ops": {
                "ingest_synthetic_batch": {
                    "config": {
                        "batch_id": batch_id
                    }
                }
            }
        }
    )
```

---

## Schedules

### Daily Scoring Schedule

```python
from dagster import ScheduleDefinition

daily_scoring_schedule = ScheduleDefinition(
    job=full_scoring_job,
    cron_schedule="0 2 * * *",  # 2 AM daily
    run_config={
        "ops": {
            "ingest_synthetic_batch": {
                "config": {
                    "batch_id": {"env": "DAILY_BATCH_ID"}
                }
            }
        }
    }
)
```

### Weekly ML Training Schedule

```python
weekly_ml_schedule = ScheduleDefinition(
    job=ml_training_job,
    cron_schedule="0 3 * * 0",  # 3 AM Sunday
    run_config={
        "ops": {
            "train_model_asset": {
                "config": {
                    "min_samples": 500
                }
            }
        }
    }
)
```

---

## Sensors

### New Data Sensor

Triggers pipeline when new data files appear.

```python
from dagster import sensor, RunRequest
import os

@sensor(job=full_scoring_job)
def new_data_sensor(context):
    """Detect new data files and trigger ingestion."""
    data_dir = "data/incoming"
    
    for filename in os.listdir(data_dir):
        if filename.endswith(".json"):
            filepath = os.path.join(data_dir, filename)
            batch_id = filename.replace(".json", "")
            
            # Check if already processed
            if not context.instance.has_run_for_key(batch_id):
                yield RunRequest(
                    run_key=batch_id,
                    run_config={
                        "ops": {
                            "ingest_synthetic_batch": {
                                "config": {
                                    "batch_id": batch_id,
                                    "file_path": filepath
                                }
                            }
                        }
                    }
                )
```

### Score Threshold Sensor

Triggers alert when scores fall below threshold.

```python
@sensor(job=alert_job)
def low_score_sensor(context):
    """Alert when average score drops."""
    db = get_database()
    
    recent_scores = db.query(ScoreRequest).filter(
        ScoreRequest.created_at >= datetime.utcnow() - timedelta(hours=1)
    ).all()
    
    if recent_scores:
        avg_score = statistics.mean([s.total_score for s in recent_scores])
        
        if avg_score < 500:  # Threshold
            yield RunRequest(
                run_key=f"low_score_alert_{datetime.utcnow():%Y%m%d%H}",
                run_config={
                    "ops": {
                        "send_alert": {
                            "config": {
                                "message": f"Low average score: {avg_score:.0f}",
                                "severity": "warning"
                            }
                        }
                    }
                }
            )
```

---

## Executing Jobs

### Via Dagster UI

1. Navigate to `http://localhost:3000`
2. Select job from sidebar
3. Click "Launchpad"
4. Edit configuration if needed
5. Click "Launch Run"

### Via CLI

```bash
# Execute with default config
dagster job execute -f dagster_home/definitions.py -j full_scoring_job

# Execute with custom config
dagster job execute -f dagster_home/definitions.py -j full_scoring_job \
  --config run_config.yaml

# Execute specific assets only
dagster asset materialize -f dagster_home/definitions.py --select score_batch
```

### Via Python

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

if result.success:
    print("Pipeline completed successfully")
else:
    print(f"Pipeline failed: {result.failure_data}")
```

---

## Job Resources

Jobs can share resources:

```python
from dagster import Definitions, resource

@resource
def database_resource():
    from app.db.database import SessionLocal
    return SessionLocal()

defs = Definitions(
    assets=[...],
    jobs=[full_scoring_job, ml_training_job],
    resources={
        "database": database_resource
    }
)
```

---

## Error Handling

### Retry Policy

```python
from dagster import RetryPolicy

@asset(
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=30  # seconds
    )
)
def score_batch(context, extract_features):
    # Will retry up to 3 times with 30s delay
    pass
```

### Failure Hooks

```python
from dagster import failure_hook

@failure_hook
def notify_on_failure(context):
    """Send notification on job failure."""
    send_slack_message(
        channel="#alerts",
        message=f"Job {context.job_name} failed: {context.op_exception}"
    )

full_scoring_job_with_hooks = full_scoring_job.with_hooks({notify_on_failure})
```
