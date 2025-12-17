from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas.schemas import PartyCreate, PartyResponse, TransactionResponse
from app.models.models import Party
from app.services.network_service import (
    get_downstream_network,
    get_upstream_network,
    get_direct_counterparties,
)
from app.db.crud import get_party_transactions

# Router
router = APIRouter(prefix="/api/parties", tags=["parties"])


# =========================
# CREATE PARTY
# =========================
@router.post("/", response_model=PartyResponse, status_code=201)
def create_party(
    party: PartyCreate,
    db: Session = Depends(get_db),
):
    if party.tax_id:
        existing = db.query(Party).filter(Party.tax_id == party.tax_id).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Party with tax_id '{party.tax_id}' already exists",
            )

    db_party = Party(**party.model_dump())
    db.add(db_party)
    db.commit()
    db.refresh(db_party)
    return db_party


# =========================
# LIST PARTIES
# =========================
@router.get("/", response_model=List[PartyResponse])
def list_parties(
    skip: int = 0,
    limit: int = 100,
    party_type: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Party)

    if party_type:
        query = query.filter(Party.party_type == party_type)

    parties = query.offset(skip).limit(limit).all()

    for p in parties:
        if isinstance(p.party_type, str):
            p.party_type = p.party_type.lower()

    return parties


# =========================
# GET PARTY
# =========================
@router.get("/{party_id}", response_model=PartyResponse)
def get_party(
    party_id: int,
    db: Session = Depends(get_db),
):
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    if isinstance(party.party_type, str):
        party.party_type = party.party_type.lower()

    return party


# =========================
# PARTY NETWORK
# =========================
@router.get("/{party_id}/network")
def get_party_network(
    party_id: int,
    direction: str = Query("downstream", pattern="^(downstream|upstream)$"),
    depth: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    if direction == "downstream":
        network_data = get_downstream_network(db, party_id, depth)
    else:
        network_data = get_upstream_network(db, party_id, depth)

    return {
        "root_party": {
            "id": party.id,
            "name": party.name,
            "party_type": party.party_type.lower()
            if isinstance(party.party_type, str)
            else party.party_type,
        },
        "direction": direction,
        "max_depth": depth,
        "nodes": network_data["nodes"],
        "edges": [
            {
                "id": e.id,
                "from_party_id": e.from_party_id,
                "to_party_id": e.to_party_id,
                "relationship_type": e.relationship_type,
                "established_date": e.established_date.isoformat(),
            }
            for e in network_data["edges"]
        ],
    }


# =========================
# COUNTERPARTIES
# =========================
@router.get("/{party_id}/counterparties", response_model=List[PartyResponse])
def get_counterparties(
    party_id: int,
    db: Session = Depends(get_db),
):
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    counterparties = get_direct_counterparties(db, party_id)

    for cp in counterparties:
        if isinstance(cp.party_type, str):
            cp.party_type = cp.party_type.lower()

    return counterparties


# =========================
# UPDATE PARTY
# =========================
@router.put("/{party_id}", response_model=PartyResponse)
def update_party(
    party_id: int,
    party_update: PartyCreate,
    db: Session = Depends(get_db),
):
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    for key, value in party_update.model_dump().items():
        setattr(party, key, value)

    db.commit()
    db.refresh(party)

    if isinstance(party.party_type, str):
        party.party_type = party.party_type.lower()

    return party


# =========================
# DELETE PARTY
# =========================
@router.delete("/{party_id}", status_code=204)
def delete_party(
    party_id: int,
    db: Session = Depends(get_db),
):
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    db.delete(party)
    db.commit()
    return None


# =========================
# CREDIT SCORE
# =========================
@router.get("/{party_id}/credit-score")
def get_party_with_credit_score(
    party_id: int,
    db: Session = Depends(get_db),
):
    from app.services.scoring_service import ScoringService

    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    scoring_service = ScoringService(db)

    try:
        score_result = scoring_service.compute_score(party_id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"SCORING ERROR: {e}")
        score_result = None

    return {
        "party": {
            "id": party.id,
            "name": party.name,
            "party_type": party.party_type.lower()
            if isinstance(party.party_type, str)
            else party.party_type,
            "tax_id": party.tax_id,
            "kyc_verified": party.kyc_verified,
        },
        "credit_score": score_result,
    }


# =========================
# TRANSACTIONS (IMPORTANT)
# =========================
@router.get("/{party_id}/transactions", response_model=List[TransactionResponse])
def get_party_transactions_endpoint(
    party_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    party = db.query(Party).filter(Party.id == party_id).first()
    if not party:
        raise HTTPException(status_code=404, detail="Party not found")

    return get_party_transactions(db, party_id, skip=skip, limit=limit)
