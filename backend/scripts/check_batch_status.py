from app.db.database import SessionLocal
from app.models.models import Batch
import sys

def check_batch(batch_id):
    db = SessionLocal()
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if batch:
        print(f"Batch: {batch.id}")
        print(f"Status: {batch.status}")
        print(f"Label Count: {batch.label_count}")
        print(f"Def Rate: {batch.default_rate}")
    else:
        print(f"Batch {batch_id} not found.")
    db.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_batch(sys.argv[1])
    else:
        print("Provide batch ID")
