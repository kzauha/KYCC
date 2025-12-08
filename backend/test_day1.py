from app.db.database import SessionLocal
from app.db.crud import create_party, get_party
from app.schemas.schemas import PartyCreate

# Create a database session
db = SessionLocal()

try:
    # Create a test party
    test_party = PartyCreate(
        name="Test Company",
        party_type="supplier",
        tax_id="TAX001",
        kyc_verified=75
    )
    
    # Save to database
    created = create_party(db, test_party)
    print(f"✅ Created party: {created.name} (ID: {created.id})")
    
    # Retrieve it back
    retrieved = get_party(db, created.id)
    print(f"✅ Retrieved party: {retrieved.name}")
    
    print("\n🎉 Day 1 Complete! Database is working!")
    
finally:
    db.close()