from app.db.database import SessionLocal
from app.models.models import Party, Relationship, Transaction, CreditScore


def print_rows(label, rows, attrs=None):
    print(f"\n--- {label} ({len(rows)}) ---")
    for r in rows:
        if attrs:
            vals = [str(getattr(r, a, None)) for a in attrs]
            print(" | ".join(vals))
        else:
            # fallback: print common attributes
            if hasattr(r, 'id') and hasattr(r, 'name'):
                print(f"{r.id}: {getattr(r, 'name', '')}")
            else:
                print(r)


def run():
    db = SessionLocal()
    try:
        parties = db.query(Party).all()
        print_rows('Parties', parties, attrs=['id', 'name', 'party_type', 'tax_id', 'kyc_verified', 'created_at'])

        relationships = db.query(Relationship).all()
        print_rows('Relationships', relationships, attrs=['id', 'from_party_id', 'to_party_id', 'relationship_type', 'established_date'])

        transactions = db.query(Transaction).all()
        print_rows('Transactions', transactions, attrs=['id', 'party_id', 'counterparty_id', 'transaction_date', 'amount', 'transaction_type'])

        credits = db.query(CreditScore).all()
        print_rows('CreditScores', credits, attrs=['id', 'party_id', 'overall_score', 'calculated_at'])

    finally:
        db.close()


if __name__ == '__main__':
    run()
