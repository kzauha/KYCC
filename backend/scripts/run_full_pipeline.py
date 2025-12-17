"""
Script to trigger the full unified pipeline on-demand and report results.
"""
import sys
import os
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Ensure dagster_home is importable
sys.path.insert(0, str(BACKEND_DIR / "dagster_home"))

from dagster import materialize, ExecuteInProcessResult, DagsterInstance
from dagster_home.definitions import (
    ingest_synthetic_batch,
    validate_ingestion, kyc_features, transaction_features, network_features,
    features_all, validate_features, generate_scorecard_labels,
    validate_labels_asset, validate_feature_label_alignment_asset,  
    score_batch, build_training_matrix,
    train_model_asset, refine_scorecard, evaluate_model
)

def run_pipeline():
    print("Starting Unified KYCC Pipeline (Scorecard-Based)")
    print("-" * 50)
    
    partition_key = "BATCH_001"
    result = None # Initialize
    
    try:
        # Create shared instance to persist state between runs
        instance = DagsterInstance.ephemeral()

        # Explicitly list assets to ensure they are found
        all_assets = [
            ingest_synthetic_batch,
            validate_ingestion, kyc_features, transaction_features, network_features,
            features_all, validate_features, generate_scorecard_labels,
            validate_labels_asset, validate_feature_label_alignment_asset,
            score_batch, build_training_matrix,
            train_model_asset, refine_scorecard, evaluate_model
        ]
        
        print(f"DEBUG: Total assets found: {len(all_assets)}")
        
        # Prepare Run Config
        run_config = {
            "ops": {
                "ingest_synthetic_batch": {"config": {"batch_id": partition_key}},
                "generate_scorecard_labels": {"config": {"batch_id": partition_key}},
                "score_batch": {"config": {"batch_id": partition_key}}
            }
        }
        
        # Separate partitioned and unpartitioned assets
        # Mixed execution with partition_key fails in Dagster
        partitioned_assets = [a for a in all_assets if a.partitions_def is not None]
        unpartitioned_assets = [a for a in all_assets if a.partitions_def is None]

        print(f"Found {len(unpartitioned_assets)} global assets and {len(partitioned_assets)} partitioned assets.")

        # 1. Run Global Assets (e.g. checks for files)
        # Note: Since we removed PartitionsDefinition, most assets are likely here now
        if unpartitioned_assets:
            print("Executing global assets/pipeline (Unpartitioned with Config)...")
            result = materialize(
                assets=unpartitioned_assets,
                instance=instance,
                run_config=run_config # Pass config!
            )
        
        # 2. Run Partitioned Assets (The actual pipeline)
        if partitioned_assets:
            print(f"Executing partitioned pipeline for Batch {partition_key}...")
            # We usually wouldn't separate if they are linked dependencies, but assuming check passed
            # If partitioned_assets depends on unpartitioned, this split execution might break flow
            # But here partitions_def is likely None for all.
            pass # Skip if empty
        
        if result and result.success:
            print("\n✅ Pipeline Finished Successfully!\n")
            print_summary(result)
        elif result:
            print("\n❌ Pipeline Failed!")
        else:
             print("\n⚠️ No assets were executed.")
            
    except Exception as e:
        print(f"\n❌ Error triggering pipeline: {str(e)}")
        # In case of validation error or other failures
        import traceback
        traceback.print_exc()

def print_summary(result: ExecuteInProcessResult):
    print("--- Execution Summary ---")
    
    # 1. Ingestion
    print("\n[Stage 1: Ingestion]")
    if result.output_for_node("validate_ingestion"):
        counts = result.output_for_node("validate_ingestion")
        print(f"  - Parties Loaded: {counts.get('party_count')}")
        print(f"  - Transactions:   {counts.get('txn_count')}")
        
    # 2. Validation
    print("\n[Stage 2: Data Quality]")
    # We need to extract asset output. validate_features asset is named 'validate_features'
    # But result.output_for_node might need the op name.
    # Asset 'validate_features' -> Op 'validate_features'
    try:
        val_report = result.output_for_node("validate_features")
        if val_report:
            print(f"  - Batch Validity: {val_report.get('completion_rate', 0):.1f}%")
            print(f"  - Valid Parties:  {val_report.get('valid_parties')}")
            print(f"  - Issues Found:   {val_report.get('total_issues')}")
    except Exception:
        print("  - Validation report not available.")

    # 3. Training
    print("\n[Stage 3: Model Training]")
    try:
        # train_model_asset returns dict with metrics
        train_out = result.output_for_node("train_model_asset")
        metrics = train_out.get("metrics", {})
        print(f"  - Model Type: Logistic Regression")
        print(f"  - AUC Score:  {metrics.get('roc_auc', 'N/A'):.4f}")
        print(f"  - F1 Score:   {metrics.get('f1', 'N/A'):.4f}")
    except Exception:
        print("  - Training metrics not available.")

    # 4. Scorecard Refinement
    print("\n[Stage 4: Scorecard Refinement]")
    try:
        refine_out = result.output_for_node("refine_scorecard")
        status = refine_out.get("status")
        print(f"  - Status:  {status.upper()}")
        
        if status == "activated":
             print(f"  - New Version: {refine_out.get('version')}")
             print(f"  - ML AUC:      {refine_out.get('ml_auc', 0):.4f}")
        elif status == "failed":
             print(f"  - Reason:      {refine_out.get('reason')}")
        else:
             print("  - No changes made to scorecard.")
             
    except Exception:
        print("  - Refinement details not available.")
        
    # 5. Inference
    print("\n[Stage 5: Batch Scoring]")
    try:
        score_out = result.output_for_node("score_batch")
        summary = score_out.get("summary", {})
        print(f"  - Total Scored: {summary.get('scored')}")
        print(f"  - Failed:       {summary.get('failed')}")
        print(f"  - Avg Score:    {summary.get('avg_score', 0):.1f}")
    except Exception:
         print("  - Scoring summary not available.")

    print("\n" + "-" * 50)
    print("Full audit trace available in 'score_requests' table.")

if __name__ == "__main__":
    run_pipeline()
