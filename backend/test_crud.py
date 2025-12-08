from app.db.database import SessionLocal
from app.db.crud import create_party, get_party, get_parties, get_party_by_tax_id
from app.schemas.schemas import PartyCreate


def run():
    db = SessionLocal()
    try:
        print("Running CRUD test...")

        p1 = PartyCreate(
            name="CRUD Company A",
            party_type="manufacturer",
            tax_id="CRUD001",
            kyc_verified=80,
        )
        # Avoid duplicate inserts: check tax_id first
        existing = get_party_by_tax_id(db, p1.tax_id)
        if existing:
            created1 = existing
            print(f"Skipped create (exists): {created1.id} {created1.name}")
        else:
            created1 = create_party(db, p1)
            print(f"Created: {created1.id} {created1.name}")

        p2 = PartyCreate(
            name="CRUD Company B",
            party_type="distributor",
            tax_id="CRUD002",
            kyc_verified=60,
        )
        existing2 = get_party_by_tax_id(db, p2.tax_id)
        if existing2:
            created2 = existing2
            print(f"Skipped create (exists): {created2.id} {created2.name}")
        else:
            created2 = create_party(db, p2)
            print(f"Created: {created2.id} {created2.name}")

        allp = get_parties(db)
        print(f"Total parties: {len(allp)}")
        for pr in allp:
            print(f"- {pr.id}: {pr.name} | {pr.party_type} | tax={pr.tax_id} | kyc={pr.kyc_verified}")

        by_tax = get_party_by_tax_id(db, "CRUD001")
        if by_tax:
            print("Found by tax:", by_tax.id, by_tax.name)
        else:
            print("Party by tax not found")

    finally:
        db.close()


if __name__ == '__main__':
    run()
