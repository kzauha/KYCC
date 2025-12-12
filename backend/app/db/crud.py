from sqlalchemy.orm import Session
from app.models.models import Party, Transaction
from app.schemas.schemas import PartyCreate
from typing import Optional, List

def create_party(db: Session, party: PartyCreate) -> Party:
    """
    Create a new party in the database
    
    Args:
        db: Database session
        party: PartyCreate schema with party data
    
    Returns:
        The created Party model
    """
    # Convert Pydantic schema to dictionary
    party_dict = party.model_dump()
    
    # Create SQLAlchemy model from dictionary
    db_party = Party(**party_dict)
    
    # Add to database session (like staging a Git commit)
    db.add(db_party)
    
    # Commit the transaction (like pushing to Git - makes it permanent)
    db.commit()
    
    # Refresh to get the ID that was auto-generated
    db.refresh(db_party)
    
    return db_party


def get_party(db: Session, party_id: int) -> Optional[Party]:
    """
    Get a single party by ID
    
    Returns None if not found
    """
    return db.query(Party).filter(Party.id == party_id).first()


def get_parties(db: Session, skip: int = 0, limit: int = 100) -> List[Party]:
    """
    Get a list of parties
    
    Args:
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
    """
    return db.query(Party).offset(skip).limit(limit).all()


def get_party_by_tax_id(db: Session, tax_id: str) -> Optional[Party]:
    """Get a party by their tax ID"""
    return db.query(Party).filter(Party.tax_id == tax_id).first()


def update_party(db: Session, party_id: int, updates: dict) -> Optional[Party]:
    """
    Update an existing party by ID. `updates` is a dict of column names -> values.

    Returns the updated Party or None if not found.
    """
    db_party = db.query(Party).filter(Party.id == party_id).first()
    if not db_party:
        return None

    # Apply updates (only attributes that exist on the model should be set)
    for key, value in updates.items():
        if hasattr(db_party, key):
            setattr(db_party, key, value)

    db.add(db_party)
    db.commit()
    db.refresh(db_party)
    return db_party


def delete_party(db: Session, party_id: int) -> bool:
    """
    Delete a party by ID. Returns True if deleted, False if not found.
    """
    db_party = db.query(Party).filter(Party.id == party_id).first()
    if not db_party:
        return False
    db.delete(db_party)
    db.commit()
    return True


def get_party_transactions(db: Session, party_id: int, skip: int = 0, limit: int = 100) -> List[Transaction]:
    """
    Get all transactions for a party (both as sender and receiver).
    
    Args:
        db: Database session
        party_id: ID of the party
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
    
    Returns:
        List of Transaction records where party is either from_party or to_party
    """
    from sqlalchemy import or_
    
    transactions = db.query(Transaction).filter(
        or_(
            Transaction.from_party_id == party_id,
            Transaction.to_party_id == party_id
        )
    ).order_by(Transaction.timestamp.desc()).offset(skip).limit(limit).all()
    
    return transactions