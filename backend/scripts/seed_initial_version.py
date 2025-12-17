
from app.db.database import SessionLocal
from app.services.scorecard_version_service import ScorecardVersionService

def seed():
    db = SessionLocal()
    try:
        svc = ScorecardVersionService(db)
        svc.ensure_initial_version()
        print("Initial scorecard version ensured.")
    except Exception as e:
        print(f"Error seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
