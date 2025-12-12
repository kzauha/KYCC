from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import PartyCreate, PartyResponse, TransactionResponse
from app.models.models import Party
from app.services.network_service import get_downstream_network, get_upstream_network, get_direct_counterparties
from app.db.crud import get_party_transactions
from typing import List

# Create router for party endpoints
router = APIRouter(prefix="/api/parties", tags=["parties"])


@router.post("/", response_model=PartyResponse, status_code=201)
def create_party(
    party: PartyCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new party (company/entity).
    
    All fields are validated according to PartyCreate schema.
    """
    # Check if tax_id already exists (if provided)
    if party.tax_id:
        existing = db.query(Party).filter(Party.tax_id == party.tax_id).first()
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Party with tax_id '{party.tax_id}' already exists"
            )
    
    # Create new party
    db_party = Party(**party.model_dump())
    db.add(db_party)
    db.commit()
    db.refresh(db_party)
    
    return db_party


@router.get("/", response_model=List[PartyResponse])
def list_parties(
    skip: int = 0,
    limit: int = 100,
    party_type: str = None,
    db: Session = Depends(get_db)
):
    """
    Get a list of all parties.
    
    Query parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum records to return
    - party_type: Filter by party type (supplier, manufacturer, etc.)
    """
    query = db.query(Party)
    
    # Apply filter if party_type provided
    if party_type:
        query = query.filter(Party.party_type == party_type)
    
    parties = query.offset(skip).limit(limit).all()
    return parties


@router.get("/{party_id}", response_model=PartyResponse)
def get_party(
    party_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific party by ID"""
    party = db.query(Party).filter(Party.id == party_id).first()
    
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    return party


@router.get("/{party_id}/network")
def get_party_network(
    party_id: int,
    direction: str = Query("downstream", regex="^(downstream|upstream)$"),
    depth: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get the network tree for a party.
    
    Args:
    - party_id: ID of the root party
    - direction: 'downstream' (who they supply to) or 'upstream' (who supplies to them)
    - depth: How many levels deep to search (1-50)
    
    Returns:
    - root_party: The party at the center
    - nodes: All connected parties with their depth
    - edges: All relationships between the nodes
    """
    # Check if party exists
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Get network based on direction
    if direction == "downstream":
        network_data = get_downstream_network(db, party_id, depth)
    else:  # upstream
        network_data = get_upstream_network(db, party_id, depth)
    
    # Format response
    return {
        "root_party": {
            "id": party.id,
            "name": party.name,
            "party_type": party.party_type
        },
        "direction": direction,
        "max_depth": depth,
        "nodes": network_data["nodes"],
        "edges": [
            {
                "id": edge.id,
                "from_party_id": edge.from_party_id,
                "to_party_id": edge.to_party_id,
                "relationship_type": edge.relationship_type,
                "established_date": edge.established_date.isoformat()
            }
            for edge in network_data["edges"]
        ]
    }


@router.get("/{party_id}/counterparties", response_model=List[PartyResponse])
def get_counterparties(
    party_id: int,
    db: Session = Depends(get_db)
):
    """
    Get direct counterparties (business partners) of a party.
    
    This returns only parties with direct relationships (depth = 1).
    """
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    counterparties = get_direct_counterparties(db, party_id)
    return counterparties


@router.put("/{party_id}", response_model=PartyResponse)
def update_party(
    party_id: int,
    party_update: PartyCreate,
    db: Session = Depends(get_db)
):
    """Update an existing party"""
    db_party = db.query(Party).filter(Party.id == party_id).first()
    
    if not db_party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Update fields
    for key, value in party_update.model_dump().items():
        setattr(db_party, key, value)
    
    db.commit()
    db.refresh(db_party)
    
    return db_party


@router.delete("/{party_id}", status_code=204)
def delete_party(
    party_id: int,
    db: Session = Depends(get_db)
):
    """Delete a party"""
    party = db.query(Party).filter(Party.id == party_id).first()
    
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    db.delete(party)
    db.commit()
    
    return None

# backend/app/api/parties.py (ADD TO EXISTING FILE)

@router.get("/{party_id}/credit-score")
def get_party_with_credit_score(
    party_id: int,
    db: Session = Depends(get_db)
):
    """
    Get party info + latest credit score in one call.
    
    Convenient endpoint that combines your existing Party data
    with credit scoring.
    """
    from app.services.scoring_service import ScoringService
    
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Try to get latest score
    scoring_service = ScoringService(db)
    try:
        score_result = scoring_service.compute_score(party_id)
        credit_score_data = {
            "score": score_result["score"],
            "score_band": score_result["score_band"],
            "confidence": score_result["confidence"],
            "computed_at": score_result["computed_at"]
        }
    except Exception:
        credit_score_data = None
    
    return {
        "party": {
            "id": party.id,
            "name": party.name,
            "party_type": party.party_type,
            "tax_id": party.tax_id,
            "kyc_verified": party.kyc_verified
        },
        "credit_score": credit_score_data
    }


@router.get("/{party_id}/transactions", response_model=List[TransactionResponse])
def get_party_transactions_endpoint(
    party_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get all transactions for a party (both sent and received).
    
    Returns transactions where the party is either the sender or receiver,
    ordered by most recent first.
    
    Query parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum records to return (1-1000)
    """
    # Verify party exists
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    transactions = get_party_transactions(db, party_id, skip=skip, limit=limit)
    return transactions