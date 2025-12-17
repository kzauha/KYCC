import sys
import os
import logging
# Add parent dir to path so we can import app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.services.analytics_service import AnalyticsService

# Setup logging
logging.basicConfig(level=logging.INFO)

def reproduce():
    db = SessionLocal()
    try:
        service = AnalyticsService(db)
        print("Calling get_scorecard_versions...")
        versions = service.get_scorecard_versions()
        print(f"Success! Got {len(versions)} versions.")
        
        # Test serialization (FastAPI simulation)
        from fastapi.encoders import jsonable_encoder
        import json
        
        print("Testing serialization...")
        encoded = jsonable_encoder(versions)
        dumped = json.dumps(encoded) 
        print("Serialization successful.")
        
        import math
        for v in versions:
             auc = v.get('ml_auc')
             if auc is not None and (math.isnan(auc) or math.isinf(auc)):
                 print(f"FOUND INVALID FLOAT: {auc} in version {v['version']}")
    except Exception as e:
        print("Caught exception:")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    reproduce()
