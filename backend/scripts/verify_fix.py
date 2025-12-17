import sys
from pathlib import Path
import json

# Setup path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.scoring_service import ScoringService
from app.services.model_training_service import ModelTrainingService
from app.db.database import SessionLocal
from app.models.models import Party

def check_imports():
    print("Imports successful.")

def verify_integration():
    db = SessionLocal()
    try:
        # 1. Test ModelTrainingService signatures (mock)
        svc_train = ModelTrainingService(db)
        if hasattr(svc_train, 'save_to_registry'):
            print("ModelTrainingService.save_to_registry found.")
        
        # 2. Test ScoringService methods
        svc_score = ScoringService(db)
        if hasattr(svc_score, 'compute_batch_scores'):
             print("ScoringService.compute_batch_scores found.")
        
        if hasattr(svc_score, '_compute_ml_model'):
             print("ScoringService._compute_ml_model logic present.")
             
        # Optional: dry run logic
        # Mock config
        mock_config = {
            "coefficients": [0.5, 0.2],
            "intercept": -1.0,
            "features": ["f1", "f2"]
        }
        mock_feats = {"f1": 1.0, "f2": 0.5}
        
        score_val = svc_score._compute_ml_model(mock_feats, mock_config)
        print(f"Test inference score: {score_val} (Expected success)")

    except Exception as e:
        print(f"Verification FAILED: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_imports()
    verify_integration()
