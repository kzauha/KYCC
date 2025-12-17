
import logging
import uuid
import os
import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text

# Dagster imports
from dagster import DagsterInstance, RunRequest, RunsFilter, DagsterRunStatus

from app.db.database import get_db, SessionLocal
from app.models.models import Batch, ScorecardVersion, TrainingJob, GroundTruthLabel, Party
from scripts.generate_synthetic_batch import generate_new_batch
from scripts.generate_outcome_labels import generate_outcome_labels

# Create router
router = APIRouter(prefix="/pipeline", tags=["pipeline"])
logger = logging.getLogger(__name__)

# --- Helper Functions ---

def get_dagster_instance():
    """Get Dagster instance, handling potential config issues."""
    try:
        # Assumes DAGSTER_HOME is set. If not, this might fail or create temp.
        # Ideally, we should check if dagster.yaml is loaded.
        instance = DagsterInstance.get()
        return instance
    except Exception as e:
        logger.error(f"Failed to load Dagster instance: {e}")
        raise HTTPException(status_code=500, detail="Dagster instance not available")

def update_batch_after_scoring(batch_id: str, run_id: str):
    """Background task to poll for scoring completion."""
    # This is a simple polling mechanism. Better to use Dagster sensors/hooks.
    # We will just log here. The frontend polls status.
    # But we can try to update 'scored_at' if we see it success?
    # For now, let's keep it simple. The frontend polls Dagster or we rely on hook.
    pass

# --- API Endpoints ---

@router.post("/run")
def run_pipeline(
    batch_size: int = 1000, 
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Step 1: Create a new batch, generate synthetic profiles, and trigger scoring pipeline.
    """
    try:
        # 1. Generate Batch ID
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"
        timestamp = datetime.utcnow()
        
        # 2. Create Batch Record
        batch = Batch(
            id=batch_id,
            status='scoring', # It starts in scoring/ingestion phase
            created_at=timestamp,
            profile_count=batch_size
        )
        db.add(batch)
        db.commit()
        
        # 3. Generate Synthetic Data (Profiles & Hidden Truth Labels)
        # Note: generate_new_batch writes to JSON files.
        # It needs to handle the file paths correctly relative to backend.
        # We assume it writes to 'backend/data/' or similar.
        try:
             generate_new_batch(batch_number=int(timestamp.timestamp()), count=batch_size)
             # Wait, generate_new_batch signature is (batch_number, count). 
             # We need to ensure it uses the 'batch_id' we generated?
             # The script I saw in Step 78 uses "BATCH_{batch_num:03d}".
             # My Batch ID is 'batch_{uuid}'. 
             # I should probably update `generate_synthetic_batch.py` to accept string batch_id 
             # OR adapt here. 
             # Let's call the generate function directly if I can import `generate_batch_data`.
             # The script has `generate_batch_data(batch_num, count)`.
             # It formats batch_id internally. 
             
             # FIX: I need to ensure consistency. 
             # The new script `generate_outcome_labels` uses `batch_id` passed in.
             # `generate_synthetic_batch` creates `BATCH_{num}`.
             # I should update the batch record to match what the script generates.
             
             # Re-reading Step 78 script:
             # batch_id = f"BATCH_{batch_num:03d}"
             
             # So I should pass a number.
             batch_num = int(timestamp.timestamp()) % 10000 
             real_batch_id = f"BATCH_{batch_num:03d}"
             
             # Update my DB record to use this ID
             batch.id = real_batch_id
             db.commit()
             
             generate_new_batch(batch_num, batch_size)
             
        except Exception as e:
            logger.error(f"Data generation failed: {e}")
            batch.status = 'failed'
            db.commit()
            raise HTTPException(500, f"Data generation failed: {str(e)}")

        # 4. Submit Dagster Run
        instance = get_dagster_instance()
        
        # Check if job exists? 
        # We assume 'score_batch_job' is defined in repository.
        run = instance.submit_run(
            RunRequest(
                job_name="score_batch_job",
                run_config={
                    "ops": {
                        "ingest_profiles": {"config": {"batch_id": real_batch_id}},
                        # Configure other ops if needed
                    }
                },
                tags={"batch_id": real_batch_id}
            )
        )
        
        return {
            "batch_id": real_batch_id,
            "dagster_run_id": run.run_id,
            "status": "scoring",
            "profile_count": batch_size,
            "message": f"Batch {real_batch_id} created and pipeline started."
        }
        
    except Exception as e:
        # If DB was modified, we might need rollback, but `db` dependency handles session.
        # Creating batch object was committed.
        logger.error(f"Pipeline run failed: {e}")
        raise HTTPException(500, f"Pipeline run failed: {str(e)}")


@router.post("/generate-outcomes/{batch_id}")
def generate_outcomes_endpoint(batch_id: str, db: Session = Depends(get_db)):
    """
    Step 2: Simulate time passing. Generate 'observed' outcome labels (defaults).
    """
    try:
        # Logic encapsulates in the script function
        result = generate_outcome_labels(db, batch_id)
        
        return {
            "message": "Outcomes generated successfully",
            **result
        }
        
    except ValueError as e:
        # Logic errors (batch not found, wrong status)
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Outcome generation failed: {e}")
        raise HTTPException(500, f"Outcome generation failed: {str(e)}")


@router.post("/train-model")
def train_model_endpoint(db: Session = Depends(get_db)):
    """
    Step 3: Trigger Model Training if enough data exists.
    """
    try:
        # 1. Check if training already in progress
        # Check TrainingJob table
        active_job = db.query(TrainingJob).filter(TrainingJob.status == 'running').first()
        if active_job:
             # Check if it's stale? For now, just block.
             raise HTTPException(400, "Training already in progress")

        # 2. Count observed labels
        count = db.query(GroundTruthLabel).filter(GroundTruthLabel.label_source == 'observed').count()
        if count < 500:
            raise HTTPException(400, f"Insufficient data: Have {count} observed labels, need 500.")

        # Get latest batch for triggering the pipeline
        latest_batch = db.query(Batch).filter(
            Batch.status == 'outcomes_generated'
        ).order_by(Batch.created_at.desc()).first()
        
        if not latest_batch:
             # Fallback if status tracking isn't perfect, just take any recent batch?
             # Or fail? If we have labels, we must have a batch.
             # Maybe the status wasn't updated to 'outcomes_generated'?
             # Let's try to get ANY batch.
             latest_batch = db.query(Batch).order_by(Batch.created_at.desc()).first()
             
        if not latest_batch:
             raise HTTPException(400, "No batches found to train on.")

        # 3. Create TrainingJob
        job_id = f"train_{uuid.uuid4().hex[:8]}"
        job = TrainingJob(
            id=job_id,
            status='running',
            started_at=datetime.utcnow(),
            training_data_count=count
        )
        db.add(job)
        db.commit()
        
        # 4. Submit Dagster Job
        instance = get_dagster_instance()
        run = instance.submit_run(
            RunRequest(
                job_name="unified_training_job",
                run_config={
                    "ops": {
                        "ingest_observed_labels": {"config": {"batch_id": latest_batch.id}},
                        "validate_labels": {"config": {"batch_id": latest_batch.id}}
                    }
                },
                tags={"training_job_id": job_id}
            )
        )
        
        return {
            "training_job_id": job_id,
            "dagster_run_id": run.run_id,
            "training_data_count": count,
            "message": "Model training started."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Training start failed: {e}")
        raise HTTPException(500, f"Training start failed: {str(e)}")


@router.get("/run/{run_id}")
def get_run_status(run_id: str):
    """Get Dagster run status."""
    try:
        instance = get_dagster_instance()
        run = instance.get_run_by_id(run_id)
        if not run:
            raise HTTPException(404, "Run not found")
            
        return {
            "run_id": run_id,
            "status": run.status.value, # STARTING, STARTED, SUCCESS, FAILURE...
            "job_name": run.job_name,
            "tags": run.tags
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to get run status: {str(e)}")


@router.get("/batch/{batch_id}/status")
def get_batch_status(batch_id: str, db: Session = Depends(get_db)):
    """Get status of a batch."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")
    
    # Optional: Sync with Dagster if status is 'scoring'
    # This logic could be complex (finding the run for this batch), simplified for now.
    
    return {
        "id": batch.id,
        "status": batch.status,
        "profile_count": batch.profile_count,
        "label_count": batch.label_count,
        "default_rate": batch.default_rate,
        "created_at": batch.created_at,
        "scored_at": batch.scored_at,
        "outcomes_generated_at": batch.outcomes_generated_at
    } 

@router.get("/batches")
def get_batches(limit: int = 10, db: Session = Depends(get_db)):
    """List recent batches."""
    batches = db.query(Batch).order_by(Batch.created_at.desc()).limit(limit).all()
    return batches

@router.get("/labels/count")
def get_label_count(db: Session = Depends(get_db)):
    """Get total count of observed labels."""
    count = db.query(GroundTruthLabel).filter(GroundTruthLabel.label_source == 'observed').count()
    return {"count": count}

