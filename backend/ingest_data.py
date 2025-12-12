from app.services.synthetic_seed_service import ingest_seed_file
from app.db.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # First, clean up existing batch data manually to avoid relationship loading
    print('🧹 Cleaning existing batch data...')
    db.execute(text("DELETE FROM relationships WHERE batch_id = 'BATCH_001'"))
    db.execute(text("DELETE FROM transactions WHERE batch_id = 'BATCH_001'"))
    db.execute(text("DELETE FROM accounts WHERE batch_id = 'BATCH_001'"))
    db.execute(text("DELETE FROM parties WHERE batch_id = 'BATCH_001'"))
    db.commit()
    
    result = ingest_seed_file(db, 'data/synthetic_profiles.json', batch_id='BATCH_001', overwrite=False)
    print('✅ Ingestion Complete!')
    print(f'   Parties: {result["parties"]}')
    print(f'   Accounts: {result["accounts"]}')
    print(f'   Transactions: {result["transactions"]}')
    print(f'   Relationships: {result["relationships"]}')
finally:
    db.close()
