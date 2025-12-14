from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List

from app.models.models import Party, Transaction
from app.schemas.schemas import PartyCreate


def create_party(db: Session, party: PartyCreate) -> Party:
    party_dict = party.model_dump()
    db_party = Party(**party_dict)

    db.add(db_party)
    db.commit()
    db.refresh(db_party)
    return db_party


def get_party(db: Session, party_id: int) -> Optional[Party]:
    return db.query(Party).filter(Party.id == party_id).first()


def get_parties(db: Session, skip: int = 0, limit: int = 100) -> List[Party]:
    return db.query(Party).offset(skip).limit(limit).all()


def get_party_by_tax_id(db: Session, tax_id: str) -> Optional[Party]:
    return db.query(Party).filter(Party.tax_id == tax_id).first()


def update_party(db: Session, party_id: int, updates: dict) -> Optional[Party]:
    db_party = db.query(Party).filter(Party.id == party_id).first()
    if not db_party:
        return None

    for key, value in updates.items():
        if hasattr(db_party, key):
            setattr(db_party, key, value)

    db.add(db_party)
    db.commit()
    db.refresh(db_party)
    return db_party


def delete_party(db: Session, party_id: int) -> bool:
    db_party = db.query(Party).filter(Party.id == party_id).first()
    if not db_party:
        return False

    db.delete(db_party)
    db.commit()
    return True


def get_party_transactions(
    db: Session,
    party_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Transaction]:
    """
    Returns transactions where party is either:
    - Transaction.party_id == party_id
    - Transaction.counterparty_id == party_id
    Ordered by newest first.
    """
    return (
        db.query(Transaction)
        .filter(
            or_(
                Transaction.party_id == party_id,
                Transaction.counterparty_id == party_id
            )
        )
        .order_by(Transaction.transaction_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
