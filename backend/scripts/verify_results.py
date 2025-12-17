
import sys
import os
from pathlib import Path
import joblib
import io
import pandas as pd
from sqlalchemy import text

# Add backend
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal
from app.models.models import ModelRegistry, CreditScore, ScorecardVersion

def verify():
    print("🔍 VERIFYING PIPELINE RESULTS")
    print("="*40)
    db = SessionLocal()
    
    try:
        # 0. Check Data
        print("\n[0. Data Ingestion]")
        from app.models.models import Party, GroundTruthLabel
        p_count = db.query(Party).count()
        l_count = db.query(GroundTruthLabel).count()
        print(f"   Parties: {p_count}")
        print(f"   Labels:  {l_count}")
        
        # 1. Check Model Registry
        print("\n[1. Model Registry]")
        models = db.query(ModelRegistry).all()
        if not models:
            print("❌ NO MODELS FOUND!")
        else:
            for m in models:
                print(f"✅ Version: {m.model_version}")
                print(f"   Created: {m.training_date}")
                print(f"   Metrics: {m.performance_metrics}")
                
                # Check Scaler
                if m.scaler_binary:
                    print("   ✅ Scaler Binary: PRESENT")
                    try:
                        scaler = joblib.load(io.BytesIO(m.scaler_binary))
                        print(f"      Scaler Type: {type(scaler)}")
                        print(f"      Scale samples: {scaler.scale_[:3]}...")
                    except Exception as e:
                        print(f"      ❌ Scaler Load Error: {e}")
                else:
                    print("   ❌ Scaler Binary: MISSING")

        # 2. Check Scorecard Weights (Sign Preservation)
        print("\n[2. Scorecard Weights]")
        # Assuming ScorecardVersion is populated or weights are in Registry?
        # run_full_pipeline registers model with "scorecard_weights" in output? 
        # Actually ModelRegistry has validation_metrics or similar?
        # Wait, ModelRegistry.model_config usually stores weights for ML model.
        # But convert_to_scorecard might save to ScorecardVersion?
        # Let's check ScorecardVersion table.
        scorecards = db.query(ScorecardVersion).all()
        if not scorecards:
            print("⚠️ No ScorecardVersion entries found (This might be expected if only ML model registered initially).")
            # Check ModelRegistry.model_config for ML weights
            if models:
                m = models[0]
                cfg = m.model_config
                if cfg:
                    print("   ML Config found:")
                    coefs = cfg.get("coefficients", {})
                    if coefs:
                        print("   Coefficients (Top 5):")
                        for k, v in list(coefs.items())[:5]:
                            print(f"     {k}: {v}")
        else:
            for sc in scorecards:
                print(f"✅ Scorecard Ver: {sc.version_id}")
                weights = sc.coefficients
                if weights:
                    print("   Weights (Check Signs):")
                    # Check for "transaction_count" or similar
                    for k, v in list(weights.items())[:10]:
                        print(f"     {k}: {v}")
                        
        # 3. Check Scores
        print("\n[3. Credit Scores]")
        scores = db.query(CreditScore).all()
        if not scores:
            print("❌ NO SCORES FOUND!")
        else:
            df = pd.DataFrame([s.overall_score for s in scores], columns=["score"])
            print(f"   Count: {len(df)}")
            print(f"   Min:   {df['score'].min()}")
            print(f"   Max:   {df['score'].max()}")
            print(f"   Mean:  {df['score'].mean():.1f}")
            
    finally:
        db.close()

if __name__ == "__main__":
    verify()
