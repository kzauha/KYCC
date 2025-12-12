from sqlalchemy import inspect
from app.db.database import engine, SessionLocal
from app.models.models import Party, Relationship, Transaction, Feature, ScoreRequest, Account

inspector = inspect(engine)

# Get all tables
print("=== DATABASE TABLES ===")
tables = inspector.get_table_names()
for table in tables:
    print(f"  - {table}")

# Show table schemas
table_list = ['parties', 'relationships', 'transactions', 'features', 'score_requests', 'accounts']

for table_name in table_list:
    print(f"\n=== {table_name.upper()} TABLE SCHEMA ===")
    columns = inspector.get_columns(table_name)
    for col in columns:
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        col_type = str(col['type'])
        print(f"  {col['name']:<25} {col_type:<20} {nullable}")

# Get sample data if records exist
db = SessionLocal()
print("\n=== SAMPLE DATA ===")

parties = db.query(Party).limit(5).all()
if parties:
    print("\nPARTIES (first 5):")
    for p in parties:
        print(f"  {p.external_id} | {p.name} | {p.party_type} | KYC Verified: {p.kyc_verified}")
else:
    print("\nPARTIES: No records")

relationships = db.query(Relationship).limit(5).all()
if relationships:
    print("\nRELATIONSHIPS (first 5):")
    for r in relationships:
        print(f"  ID:{r.id} | {r.from_party_id} → {r.to_party_id} | Type: {r.relationship_type}")
else:
    print("\nRELATIONSHIPS: No records")

transactions = db.query(Transaction).limit(5).all()
if transactions:
    print("\nTRANSACTIONS (first 5):")
    for t in transactions:
        print(f"  ID:{t.id} | Party:{t.party_id} → CP:{t.counterparty_id} | Amount: ${t.amount:,.2f} | Type: {t.transaction_type}")
else:
    print("\nTRANSACTIONS: No records")

features = db.query(Feature).limit(5).all()
if features:
    print("\nFEATURES (first 5):")
    for f in features:
        print(f"  ID:{f.id} | Party: {f.party_id} | {f.feature_name}: {f.feature_value}")
else:
    print("\nFEATURES: No records")

score_requests = db.query(ScoreRequest).limit(5).all()
if score_requests:
    print("\nSCORE REQUESTS (first 5):")
    for s in score_requests:
        print(f"  {s.id} | Party: {s.party_id} | Score: {s.final_score} | Band: {s.score_band}")
else:
    print("\nSCORE REQUESTS: No records")

accounts = db.query(Account).limit(5).all()
if accounts:
    print("\nACCOUNTS (first 5):")
    for a in accounts:
        print(f"  {a.external_id} | Party: {a.party_id} | Type: {a.account_type} | Balance: ${a.balance:,.2f}")
else:
    print("\nACCOUNTS: No records")

db.close()
