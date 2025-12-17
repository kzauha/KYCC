#!/bin/bash
# scripts/run_full_cycle.sh
# Usage: ./scripts/run_full_cycle.sh <BATCH_NUMBER>

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <BATCH_NUMBER>"
    exit 1
fi

BATCH_NUM=$1
BATCH_ID="BATCH_$(printf "%03d" $BATCH_NUM)"

echo "========================================================"
echo "STARTING CYCLE FOR $BATCH_ID"
echo "========================================================"

# 1. Generate Data (Simulates Day 1)
echo ""
echo "Step 1: Generating Synthetic Data..."
python backend/scripts/generate_synthetic_batch.py --batch-number $BATCH_NUM --count 100

# 2. Score Batch (Online Job)
# Note: This will use the ACTIVE model (trained on previous batches)
echo ""
echo "Step 2: Scoring Batch $BATCH_ID..."
dagster job execute -m backend.dagster_home.definitions -j score_batch_job \
    -c "{\"ops\": {\"ingest_synthetic_batch\": {\"config\": {\"batch_id\": \"$BATCH_ID\"}}, \"score_batch\": {\"config\": {\"batch_id\": \"$BATCH_ID\"}}}}"

# 3. Train Model (Offline Job - Simulates Day 2/3)
# Note: This uses the labels just generated to train the NEXT model
echo ""
echo "Step 3: Training Model on $BATCH_ID..."
dagster job execute -m backend.dagster_home.definitions -j train_model_job \
    -c "{\"ops\": {\"ingest_labels\": {\"config\": {\"batch_id\": \"$BATCH_ID\"}}}}"

echo ""
echo "✅ CYCLE COMPLETE FOR $BATCH_ID"
echo "========================================================"
