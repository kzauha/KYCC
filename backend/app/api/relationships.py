from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import RelationshipCreate, RelationshipResponse
from app.models.models import Relationship, Party
from typing import List

# Create router for relationship endpoints
router = APIRouter(prefix="/api/relationships", tags=["relationships"])


@router.post("/", response_model=RelationshipResponse, status_code=201)
def create_relationship(
    relationship: RelationshipCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new relationship between two parties.
    
    Example: Company A supplies to Company B
    
    Validations:
    - Both parties must exist
    - Cannot link a party to itself
    - Cannot create duplicate relationships
    """
    # Check if both parties exist
    from_party = db.query(Party).filter(Party.id == relationship.from_party_id).first()
    to_party = db.query(Party).filter(Party.id == relationship.to_party_id).first()
    
    if not from_party:
        raise HTTPException(
            status_code=404, 
            detail=f"Party with ID {relationship.from_party_id} not found"
        )
    
    if not to_party:
        raise HTTPException(
            status_code=404, 
            detail=f"Party with ID {relationship.to_party_id} not found"
        )
    
    # Prevent self-linking (a party can't have relationship with itself)
    if relationship.from_party_id == relationship.to_party_id:
        raise HTTPException(
            status_code=400, 
            detail="Cannot create relationship with the same party"
        )
    
    # Check for duplicate relationship
    existing = db.query(Relationship).filter(
        Relationship.from_party_id == relationship.from_party_id,
        Relationship.to_party_id == relationship.to_party_id,
        Relationship.relationship_type == relationship.relationship_type
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Relationship already exists between {from_party.name} and {to_party.name}"
        )
    
    # Create the relationship
    db_relationship = Relationship(**relationship.model_dump())
    db.add(db_relationship)
    db.commit()
    db.refresh(db_relationship)
    
    return db_relationship


@router.get("/", response_model=List[RelationshipResponse])
def list_relationships(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get a list of all relationships.
    
    Query parameters:
    - skip: Number of records to skip (for pagination)
    - limit: Maximum number of records to return
    """
    relationships = db.query(Relationship).offset(skip).limit(limit).all()
    return relationships


@router.get("/{relationship_id}", response_model=RelationshipResponse)
def get_relationship(
    relationship_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific relationship by ID"""
    relationship = db.query(Relationship).filter(Relationship.id == relationship_id).first()
    
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    return relationship


@router.delete("/{relationship_id}", status_code=204)
def delete_relationship(
    relationship_id: int,
    db: Session = Depends(get_db)
):
    """Delete a relationship"""
    relationship = db.query(Relationship).filter(Relationship.id == relationship_id).first()
    
    if not relationship:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    db.delete(relationship)
    db.commit()
    
    return None