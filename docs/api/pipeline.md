# Pipeline API

The pipeline API triggers and monitors Dagster pipelines for batch processing.

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/pipeline/trigger/{pipeline} | Trigger a pipeline |
| GET | /api/pipeline/status/{run_id} | Get pipeline run status |
| GET | /api/pipeline/runs | List pipeline runs |
| POST | /api/pipeline/cancel/{run_id} | Cancel a running pipeline |

---

## Available Pipelines

| Pipeline | Description |
|----------|-------------|
| full_scoring_pipeline | Complete: ingest, features, score, labels, train, refine |
| ingest_pipeline | Ingest synthetic data only |
| feature_extraction_pipeline | Extract features for a batch |
| scoring_pipeline | Score a batch |
| ml_training_pipeline | Train ML model and refine scorecard |

---

## POST /api/pipeline/trigger/{pipeline}

Trigger a pipeline execution.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| pipeline | string | path | Pipeline name |

### Request Body

```json
{
  "batch_id": "BATCH_001",
  "config": {
    "scorecard_version": "v1",
    "observation_window_days": 180
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| batch_id | string | Yes | Batch identifier |
| config | object | No | Pipeline-specific configuration |

### Response

```json
{
  "run_id": "run_abc123",
  "pipeline": "full_scoring_pipeline",
  "status": "STARTED",
  "batch_id": "BATCH_001",
  "started_at": "2024-01-15T10:30:45Z"
}
```

### Example

```bash
curl -X POST http://localhost:8000/api/pipeline/trigger/full_scoring_pipeline \
  -H "Content-Type: application/json" \
  -d '{"batch_id": "BATCH_001"}'
```

---

## GET /api/pipeline/status/{run_id}

Get status of a pipeline run.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| run_id | string | path | Pipeline run ID |

### Response

```json
{
  "run_id": "run_abc123",
  "pipeline": "full_scoring_pipeline",
  "status": "SUCCESS",
  "batch_id": "BATCH_001",
  "started_at": "2024-01-15T10:30:45Z",
  "ended_at": "2024-01-15T10:35:12Z",
  "duration_seconds": 267,
  "assets": {
    "ingest_synthetic_batch": {
      "status": "SUCCESS",
      "started_at": "2024-01-15T10:30:45Z",
      "ended_at": "2024-01-15T10:31:00Z",
      "output": {
        "parties_created": 100
      }
    },
    "extract_features": {
      "status": "SUCCESS",
      "started_at": "2024-01-15T10:31:00Z",
      "ended_at": "2024-01-15T10:32:30Z",
      "output": {
        "features_extracted": 1600
      }
    },
    "score_batch": {
      "status": "SUCCESS",
      "started_at": "2024-01-15T10:32:30Z",
      "ended_at": "2024-01-15T10:33:00Z",
      "output": {
        "parties_scored": 100
      }
    },
    "generate_scorecard_labels": {
      "status": "SUCCESS",
      "started_at": "2024-01-15T10:33:00Z",
      "ended_at": "2024-01-15T10:33:30Z",
      "output": {
        "labels_generated": 100
      }
    },
    "train_model_asset": {
      "status": "SUCCESS",
      "started_at": "2024-01-15T10:33:30Z",
      "ended_at": "2024-01-15T10:34:30Z",
      "output": {
        "model_id": "model_BATCH_001",
        "auc_roc": 0.72
      }
    },
    "refine_scorecard": {
      "status": "SUCCESS",
      "started_at": "2024-01-15T10:34:30Z",
      "ended_at": "2024-01-15T10:35:12Z",
      "output": {
        "new_version": "ml_v20240115"
      }
    }
  }
}
```

### Status Values

| Status | Description |
|--------|-------------|
| QUEUED | Waiting to start |
| STARTED | Currently running |
| SUCCESS | Completed successfully |
| FAILURE | Failed with error |
| CANCELED | Manually canceled |

### Example

```bash
curl http://localhost:8000/api/pipeline/status/run_abc123
```

---

## GET /api/pipeline/runs

List recent pipeline runs.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| pipeline | string | query | Filter by pipeline name |
| status | string | query | Filter by status |
| batch_id | string | query | Filter by batch |
| limit | integer | query | Max results (default: 20) |

### Response

```json
{
  "runs": [
    {
      "run_id": "run_abc123",
      "pipeline": "full_scoring_pipeline",
      "status": "SUCCESS",
      "batch_id": "BATCH_001",
      "started_at": "2024-01-15T10:30:45Z",
      "duration_seconds": 267
    },
    {
      "run_id": "run_xyz789",
      "pipeline": "scoring_pipeline",
      "status": "FAILURE",
      "batch_id": "BATCH_002",
      "started_at": "2024-01-14T14:00:00Z",
      "duration_seconds": 45,
      "error": "Batch not found"
    }
  ],
  "total": 50,
  "page": 1,
  "per_page": 20
}
```

### Example

```bash
curl "http://localhost:8000/api/pipeline/runs?status=FAILURE&limit=10"
```

---

## POST /api/pipeline/cancel/{run_id}

Cancel a running pipeline.

### Parameters

| Parameter | Type | Location | Description |
|-----------|------|----------|-------------|
| run_id | string | path | Pipeline run ID |

### Response

```json
{
  "run_id": "run_abc123",
  "status": "CANCELING",
  "message": "Pipeline cancellation requested"
}
```

### Example

```bash
curl -X POST http://localhost:8000/api/pipeline/cancel/run_abc123
```

---

## Pipeline Configuration

### full_scoring_pipeline

```json
{
  "batch_id": "BATCH_001",
  "config": {
    "scorecard_version": "v1",
    "observation_window_days": 180,
    "blend_factor": 0.5
  }
}
```

### ml_training_pipeline

```json
{
  "batch_id": "BATCH_001",
  "config": {
    "test_size": 0.2,
    "min_samples": 100,
    "auc_threshold": 0.60
  }
}
```

---

## Webhook Notifications

Configure webhooks to receive pipeline completion notifications:

### POST /api/pipeline/webhooks

```json
{
  "url": "https://your-app.com/webhook",
  "events": ["SUCCESS", "FAILURE"],
  "pipelines": ["full_scoring_pipeline"]
}
```

Webhook payload:

```json
{
  "event": "PIPELINE_COMPLETED",
  "run_id": "run_abc123",
  "pipeline": "full_scoring_pipeline",
  "status": "SUCCESS",
  "batch_id": "BATCH_001",
  "timestamp": "2024-01-15T10:35:12Z"
}
```

---

## Error Responses

### Pipeline Not Found

```json
{
  "status": "error",
  "error": {
    "code": "PIPELINE_NOT_FOUND",
    "message": "Pipeline 'invalid_pipeline' not found"
  }
}
```

### Run Not Found

```json
{
  "status": "error",
  "error": {
    "code": "RUN_NOT_FOUND",
    "message": "Pipeline run 'run_invalid' not found"
  }
}
```

### Pipeline Failed

```json
{
  "status": "error",
  "error": {
    "code": "PIPELINE_FAILED",
    "message": "Pipeline execution failed",
    "details": {
      "failed_asset": "train_model_asset",
      "error": "Insufficient samples: 50 < 100"
    }
  }
}
```
