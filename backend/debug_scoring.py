import sys
import os
sys.path.append(os.getcwd())

from app.db.database import SessionLocal
from app.services.scoring_service import ScoringService
import traceback

def debug_score(party_id):
    db = SessionLocal()
    try:
        service = ScoringService(db)
        print(f"Attempting to score party {party_id}...")
        result = service.compute_score(party_id)
        print("Scoring successful:", result)
    except Exception as e:
        print("Scoring FAILED:")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_score(1)
