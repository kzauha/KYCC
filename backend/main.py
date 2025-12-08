# main.py
"""
KYCC FastAPI REST API
Provides HTTP endpoints for party and relationship management
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import date

# Import from their app structure
from app.db.database import SessionLocal
from app.models.models import Party, Relationship, Transaction, CreditScore
from app.schemas.schemas import PartyCreate, PartyResponse

# Initialize FastAPI app
app = FastAPI(
    title="KYCC MVP API",
    description="Know Your Customer's Customer - Supply Chain Management API",
    version="1.0.0"
)

# CORS Configuration - Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # React default
        "http://localhost:5173",      # Vite default
        "http://localhost:5174",      # Vite alternative
        "http://localhost:8080",      # Vue default
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database session dependency
def get_db():
    """
    Creates a new database session for each request
    Automatically closes after request completes
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# ROOT ENDPOINTS
# ============================================

@app.get("/")
def root():
    """API health check and information"""
    return {
        "message": "KYCC API is running",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "endpoints": {
            "parties": "/api/parties",
            "relationships": "/api/relationships"
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "database": "connected"}


# ============================================
# PARTY ENDPOINTS
# ============================================

@app.post("/api/parties", response_model=PartyResponse, status_code=201)
def create_party(party: PartyCreate, db: Session = Depends(get_db)):
    """
    Create a new party in the system
    
    - **name**: Company name
    - **party_type**: Type (supplier/manufacturer/distributor/retailer/customer)
    - **tax_id**: Unique tax identifier
    - **kyc_verified**: KYC score (0-100)
    """
    # Check if tax_id already exists
    existing = db.query(Party).filter(Party.tax_id == party.tax_id).first()
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Party with tax_id '{party.tax_id}' already exists"
        )
    
    # Create new party
    db_party = Party(
        name=party.name,
        party_type=party.party_type,
        tax_id=party.tax_id,
        kyc_verified=party.kyc_verified
    )
    
    db.add(db_party)
    db.commit()
    db.refresh(db_party)
    
    return db_party


@app.get("/api/parties/{party_id}", response_model=PartyResponse)
def get_party(party_id: int, db: Session = Depends(get_db)):
    """
    Get a specific party by ID
    
    - **party_id**: Numeric ID of the party
    """
    party = db.query(Party).filter(Party.id == party_id).first()
    
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    return party


@app.get("/api/parties", response_model=List[PartyResponse])
def list_parties(
    skip: int = 0, 
    limit: int = 100,
    party_type: str = None,
    db: Session = Depends(get_db)
):
    """
    List all parties with optional filtering
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **party_type**: Filter by party type (optional)
    """
    query = db.query(Party)
    
    # Apply filter if party_type specified
    if party_type:
        query = query.filter(Party.party_type == party_type)
    
    parties = query.offset(skip).limit(limit).all()
    return parties


@app.get("/api/parties/search/tax/{tax_id}", response_model=PartyResponse)
def get_party_by_tax_id(tax_id: str, db: Session = Depends(get_db)):
    """
    Search for a party by their tax ID
    
    - **tax_id**: Tax identifier to search for
    """
    party = db.query(Party).filter(Party.tax_id == tax_id).first()
    
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    return party


@app.put("/api/parties/{party_id}", response_model=PartyResponse)
def update_party(
    party_id: int, 
    party_update: PartyCreate, 
    db: Session = Depends(get_db)
):
    """
    Update an existing party
    
    - **party_id**: ID of party to update
    - **party_update**: Updated party data
    """
    party = db.query(Party).filter(Party.id == party_id).first()
    
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Check if new tax_id conflicts with another party
    if party_update.tax_id != party.tax_id:
        existing = db.query(Party).filter(Party.tax_id == party_update.tax_id).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Another party with tax_id '{party_update.tax_id}' already exists"
            )
    
    # Update fields
    party.name = party_update.name
    party.party_type = party_update.party_type
    party.tax_id = party_update.tax_id
    party.kyc_verified = party_update.kyc_verified
    
    db.commit()
    db.refresh(party)
    
    return party


@app.delete("/api/parties/{party_id}")
def delete_party(party_id: int, db: Session = Depends(get_db)):
    """
    Delete a party from the system
    
    - **party_id**: ID of party to delete
    """
    party = db.query(Party).filter(Party.id == party_id).first()
    
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    db.delete(party)
    db.commit()
    
    return {
        "message": "Party deleted successfully",
        "deleted_party_id": party_id
    }


# ============================================
# RELATIONSHIP ENDPOINTS
# ============================================

@app.post("/api/relationships", status_code=201)
def create_relationship(
    from_party_id: int,
    to_party_id: int,
    relationship_type: str,
    db: Session = Depends(get_db)
):
    """
    Create a relationship between two parties
    
    - **from_party_id**: Source party ID
    - **to_party_id**: Target party ID
    - **relationship_type**: Type of relationship (e.g., "supplies_to", "distributes_for")
    """
    # Validate parties exist
    from_party = db.query(Party).filter(Party.id == from_party_id).first()
    to_party = db.query(Party).filter(Party.id == to_party_id).first()
    
    if not from_party:
        raise HTTPException(status_code=404, detail=f"Party with id {from_party_id} not found")
    
    if not to_party:
        raise HTTPException(status_code=404, detail=f"Party with id {to_party_id} not found")
    
    # Prevent self-referencing relationships
    if from_party_id == to_party_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot create relationship from a party to itself"
        )
    
    # Check for duplicate relationship
    existing = db.query(Relationship).filter(
        Relationship.from_party_id == from_party_id,
        Relationship.to_party_id == to_party_id,
        Relationship.relationship_type == relationship_type
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Relationship already exists between these parties"
        )
    
    # Create relationship
    db_relationship = Relationship(
        from_party_id=from_party_id,
        to_party_id=to_party_id,
        relationship_type=relationship_type,
        established_date=date.today()
    )
    
    db.add(db_relationship)
    db.commit()
    db.refresh(db_relationship)
    
    return {
        "id": db_relationship.id,
        "from_party_id": db_relationship.from_party_id,
        "from_party_name": from_party.name,
        "to_party_id": db_relationship.to_party_id,
        "to_party_name": to_party.name,
        "relationship_type": db_relationship.relationship_type,
        "established_date": db_relationship.established_date
    }


@app.get("/api/relationships")
def list_relationships(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all relationships in the system
    
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    relationships = db.query(Relationship).offset(skip).limit(limit).all()
    
    # Enrich with party names
    result = []
    for rel in relationships:
        from_party = db.query(Party).filter(Party.id == rel.from_party_id).first()
        to_party = db.query(Party).filter(Party.id == rel.to_party_id).first()
        
        result.append({
            "id": rel.id,
            "from_party_id": rel.from_party_id,
            "from_party_name": from_party.name if from_party else None,
            "to_party_id": rel.to_party_id,
            "to_party_name": to_party.name if to_party else None,
            "relationship_type": rel.relationship_type,
            "established_date": rel.established_date
        })
    
    return result


@app.get("/api/relationships/{relationship_id}")
def get_relationship(relationship_id: int, db: Session = Depends(get_db)):
    """
    Get a specific relationship by ID
    
    - **relationship_id**: ID of the relationship
    """
    rel = db.query(Relationship).filter(Relationship.id == relationship_id).first()
    
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    from_party = db.query(Party).filter(Party.id == rel.from_party_id).first()
    to_party = db.query(Party).filter(Party.id == rel.to_party_id).first()
    
    return {
        "id": rel.id,
        "from_party_id": rel.from_party_id,
        "from_party_name": from_party.name if from_party else None,
        "to_party_id": rel.to_party_id,
        "to_party_name": to_party.name if to_party else None,
        "relationship_type": rel.relationship_type,
        "established_date": rel.established_date
    }


@app.delete("/api/relationships/{relationship_id}")
def delete_relationship(relationship_id: int, db: Session = Depends(get_db)):
    """
    Delete a relationship
    
    - **relationship_id**: ID of relationship to delete
    """
    rel = db.query(Relationship).filter(Relationship.id == relationship_id).first()
    
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found")
    
    db.delete(rel)
    db.commit()
    
    return {
        "message": "Relationship deleted successfully",
        "deleted_relationship_id": relationship_id
    }


@app.get("/api/parties/{party_id}/relationships")
def get_party_relationships(party_id: int, db: Session = Depends(get_db)):
    """
    Get all relationships for a specific party (network view)
    
    Shows both upstream (suppliers) and downstream (customers) relationships
    
    - **party_id**: ID of the party to query
    """
    # Verify party exists
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Get outgoing relationships (this party supplies to others)
    outgoing = db.query(Relationship).filter(
        Relationship.from_party_id == party_id
    ).all()
    
    # Get incoming relationships (others supply to this party)
    incoming = db.query(Relationship).filter(
        Relationship.to_party_id == party_id
    ).all()
    
    # Format outgoing with party names
    outgoing_formatted = []
    for rel in outgoing:
        to_party = db.query(Party).filter(Party.id == rel.to_party_id).first()
        outgoing_formatted.append({
            "relationship_id": rel.id,
            "to_party_id": rel.to_party_id,
            "to_party_name": to_party.name if to_party else None,
            "to_party_type": to_party.party_type if to_party else None,
            "relationship_type": rel.relationship_type,
            "established_date": rel.established_date
        })
    
    # Format incoming with party names
    incoming_formatted = []
    for rel in incoming:
        from_party = db.query(Party).filter(Party.id == rel.from_party_id).first()
        incoming_formatted.append({
            "relationship_id": rel.id,
            "from_party_id": rel.from_party_id,
            "from_party_name": from_party.name if from_party else None,
            "from_party_type": from_party.party_type if from_party else None,
            "relationship_type": rel.relationship_type,
            "established_date": rel.established_date
        })
    
    return {
        "party_id": party_id,
        "party_name": party.name,
        "party_type": party.party_type,
        "outgoing_relationships": outgoing_formatted,
        "incoming_relationships": incoming_formatted,
        "total_outgoing": len(outgoing_formatted),
        "total_incoming": len(incoming_formatted)
    }


@app.get("/api/parties/{party_id}/network")
def get_party_network(
    party_id: int,
    depth: int = 2,
    direction: str = "both",
    db: Session = Depends(get_db)
):
    """
    Get the full supply chain network for a party (recursive)
    
    - **party_id**: Root party to start from
    - **depth**: How many levels deep to traverse (1-5)
    - **direction**: "upstream", "downstream", or "both"
    """
    # Validate party exists
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")
    
    # Limit depth for performance
    if depth < 1 or depth > 5:
        raise HTTPException(
            status_code=400,
            detail="Depth must be between 1 and 5"
        )
    
    # Validate direction
    if direction not in ["upstream", "downstream", "both"]:
        raise HTTPException(
            status_code=400,
            detail="Direction must be 'upstream', 'downstream', or 'both'"
        )
    
    network = {
        "root_party": {
            "id": party.id,
            "name": party.name,
            "party_type": party.party_type
        },
        "depth": depth,
        "direction": direction,
        "network_map": []
    }
    
    # Note: Full recursive network traversal would go here
    # For now, return first level
    if direction in ["downstream", "both"]:
        downstream = db.query(Relationship).filter(
            Relationship.from_party_id == party_id
        ).all()
        
        for rel in downstream:
            to_party = db.query(Party).filter(Party.id == rel.to_party_id).first()
            if to_party:
                network["network_map"].append({
                    "level": 1,
                    "direction": "downstream",
                    "party_id": to_party.id,
                    "party_name": to_party.name,
                    "party_type": to_party.party_type,
                    "relationship_type": rel.relationship_type
                })
    
    if direction in ["upstream", "both"]:
        upstream = db.query(Relationship).filter(
            Relationship.to_party_id == party_id
        ).all()
        
        for rel in upstream:
            from_party = db.query(Party).filter(Party.id == rel.from_party_id).first()
            if from_party:
                network["network_map"].append({
                    "level": 1,
                    "direction": "upstream",
                    "party_id": from_party.id,
                    "party_name": from_party.name,
                    "party_type": from_party.party_type,
                    "relationship_type": rel.relationship_type
                })
    
    return network


# ============================================
# STATISTICS ENDPOINTS
# ============================================

@app.get("/api/stats")
def get_statistics(db: Session = Depends(get_db)):
    """
    Get overall system statistics
    """
    total_parties = db.query(Party).count()
    total_relationships = db.query(Relationship).count()
    
    # Count by party type
    party_type_counts = {}
    for party_type in ["supplier", "manufacturer", "distributor", "retailer", "customer"]:
        count = db.query(Party).filter(Party.party_type == party_type).count()
        party_type_counts[party_type] = count
    
    return {
        "total_parties": total_parties,
        "total_relationships": total_relationships,
        "parties_by_type": party_type_counts,
        "average_kyc_score": db.query(Party).all() and 
            sum(p.kyc_verified for p in db.query(Party).all()) / total_parties if total_parties > 0 else 0
    }


# Run with: python -m uvicorn main:app --reload --port 8000
# API Docs: http://localhost:8000/docs
# ReDoc: http://localhost:8000/redoc