from dagster import sensor, RunRequest, SensorEvaluationContext, SkipReason
import os
import re
# Removed import to avoid circular dependency
# from .definitions import score_batch_job, train_model_job

@sensor(
    job_name="score_batch_job", # Default job (string reference to avoid import loop)
    minimum_interval_seconds=30
)
def iterative_learning_sensor(context: SensorEvaluationContext):
    """
    Monitors data directory for new batches.
    - {id}_profiles.json -> Trigger Score Job
    - {id}_labels.json   -> Trigger Train Job
    """
    data_dir = os.path.join(os.getcwd(), "data")
    if not os.path.exists(data_dir):
        return SkipReason(f"Data directory {data_dir} not found")

    # Get processed files from cursor
    cursor = context.cursor or ""
    processed_files = set(cursor.split(",")) if cursor else set()

    new_files = []
    run_requests = []
    
    # Scan directory
    for filename in os.listdir(data_dir):
        if filename in processed_files:
            continue
            
        filepath = os.path.join(data_dir, filename)
        if not os.path.isfile(filepath):
            continue
            
        # Check patterns
        # Pattern 1: Profiles -> Score
        profiles_match = re.match(r"(BATCH_\d+)_profiles\.json", filename)
        if profiles_match:
            batch_id = profiles_match.group(1)
            run_requests.append(RunRequest(
                run_key=f"score_{batch_id}",
                job_name="score_batch_job",
                run_config={"ops": {"ingest_synthetic_batch": {"config": {"batch_id": batch_id}}, "score_batch": {"config": {"batch_id": batch_id}}}}
            ))
            new_files.append(filename)
            continue
            
        # Pattern 2: Labels -> Train
        labels_match = re.match(r"(BATCH_\d+)_labels\.json", filename)
        if labels_match:
            batch_id = labels_match.group(1)
            run_requests.append(RunRequest(
                run_key=f"train_{batch_id}",
                job_name="train_model_job",
                run_config={"ops": {"ingest_labels": {"config": {"batch_id": batch_id}}}}
            ))
            new_files.append(filename)
            continue
            
    # Update cursor
    if new_files:
        updated_cursor = ",".join(list(processed_files) + new_files)
        context.update_cursor(updated_cursor)
        return run_requests
    else:
        return SkipReason("No new files found")
