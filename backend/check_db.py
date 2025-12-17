from app.models.models import Party
from app.db.database import SessionLocal

db = SessionLocal()
print(f"Total Parties: {db.query(Party).count()}")
parties = db.query(Party.external_id, Party.batch_id).order_by(Party.created_at.desc()).limit(20).all()
for p in parties:
    print(f"Party: {p.external_id}, Batch: {p.batch_id}")
db.close()
