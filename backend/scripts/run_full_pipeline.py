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
    features_all, validate_features, score_batch,
    generate_scorecard_labels,
    validate_labels, validate_feature_label_alignment,
    build_training_matrix, train_model_asset, 
    refine_scorecard, evaluate_model,
    ingest_observed_labels
)

def run_pipeline():
    print("Starting Unified KYCC Pipeline (Scorecard-Based)")
    print("-" * 50)
    
    import glob
    import re
    
    # scan for latest batch
    data_dir = BACKEND_DIR / "data"
    files = glob.glob(str(data_dir / "BATCH_*_profiles.json"))
    
    if not files:
        print("No BATCH_*_profiles.json files found. Please generate one first.")
        return

    # Sort by batch number
    def get_batch_num(f):
        match = re.search(r'BATCH_(\d+)_', f)
        return int(match.group(1)) if match else 0
        
    latest_file = max(files, key=get_batch_num)
    # Extract ID "BATCH_XXX" from filename
    filename = Path(latest_file).name
    partition_key = filename.replace("_profiles.json", "")
    
    print(f"Detected latest batch: {partition_key}")

    result = None 
    
    try:
        instance = DagsterInstance.ephemeral()

        all_assets = [
            ingest_synthetic_batch,
            validate_ingestion, kyc_features, transaction_features, network_features,
            features_all, validate_features, score_batch,
            generate_scorecard_labels,
            ingest_observed_labels,
            validate_labels, validate_feature_label_alignment,
            build_training_matrix, train_model_asset, 
            refine_scorecard, evaluate_model
        ]
        
        print(f"DEBUG: Total assets found: {len(all_assets)}")
        
        # Prepare Run Config
        # Note: validate_ingestion does NOT take config (inherits from upstream)
        run_config = {
            "ops": {
                "ingest_synthetic_batch": {"config": {"batch_id": partition_key}},
                "score_batch": {"config": {"batch_id": partition_key}},
                "generate_scorecard_labels": {"config": {"batch_id": partition_key}},
                "validate_labels": {"config": {"batch_id": partition_key}},
                "ingest_observed_labels": {"config": {"batch_id": partition_key}}
            }
        }
        
        # Separate partitioned and unpartitioned assets
        # Mixed execution with partition_key fails in Dagster
        partitioned_assets = [a for a in all_assets if a.partitions_def is not None]
        unpartitioned_assets = [a for a in all_assets if a.partitions_def is None]

        print(f"Found {len(unpartitioned_assets)} global assets and {len(partitioned_assets)} partitioned assets.")

        # 1. Run Global Assets (e.g. checks for files)
        if unpartitioned_assets:
            # SPLIT EXECUTION: Scoring vs Training
            # Because we decoupled generate_scorecard_labels from validate_features,
            # we must ensure Scoring (which populates DB features) runs BEFORE Labeling.
            
            # Separate unpartitioned assets for unified execution
            # With deps restored in definitions.py, we have a full DAG.
            # Running all assets together satisfies Dagster validation.
            
            # Helper to get asset name safely
            def get_asset_name(asset):
                return asset.key.to_user_string() if hasattr(asset, 'key') else str(asset)
            
            # Use stage1_assets filtering just for logging if needed, but we run everything
            print(f"Executing Unified Pipeline with {len(unpartitioned_assets)} global assets")
            
            # We already defined run_config above correctly
            
            print("\n--- Executing Unified Pipeline ---")
            result = materialize(
                assets=unpartitioned_assets,
                instance=instance,
                run_config=run_config
            )
            
            pass
        
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
        # Direct access (score_out is the dict returned by asset)
        print(f"  - Total Scored: {score_out.get('scored')}")
        print(f"  - Failed:       {score_out.get('failed', 0)}")
        print(f"  - Avg Score:    {score_out.get('avg_score', 'N/A')}")
    except Exception:
         print("  - Scoring summary not available.")

    print("\n" + "-" * 50)
    print("Full audit trace available in 'score_requests' table.")

if __name__ == "__main__":
    run_pipeline()
