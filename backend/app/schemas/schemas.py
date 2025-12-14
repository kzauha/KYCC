from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.models import PartyType, RelationshipType, TransactionType


# =========================
# PARTY SCHEMAS
# =========================
class PartyBase(BaseModel):
    name: str
    party_type: PartyType
    tax_id: Optional[str] = None
    registration_number: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    kyc_verified: int = 0


class PartyCreate(PartyBase):
    pass


class PartyResponse(PartyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# =========================
# RELATIONSHIP SCHEMAS
# =========================
class RelationshipCreate(BaseModel):
    from_party_id: int
    to_party_id: int
    relationship_type: RelationshipType


class RelationshipResponse(BaseModel):
    id: int
    from_party_id: int
    to_party_id: int
    relationship_type: RelationshipType
    established_date: datetime

    model_config = {"from_attributes": True}


# =========================
# TRANSACTION SCHEMAS
# =========================
class TransactionCreate(BaseModel):
    party_id: int
    counterparty_id: Optional[int] = None
    account_id: Optional[int] = None
    transaction_date: datetime
    amount: float
    transaction_type: TransactionType
    reference: Optional[str] = None


class TransactionResponse(TransactionCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# =========================
# CREDIT SCORE SCHEMAS
# =========================
class CreditScoreResponse(BaseModel):
    id: int
    party_id: int
    overall_score: float
    payment_regularity_score: Optional[float]
    transaction_volume_score: Optional[float]
    kyc_score: Optional[float]
    network_score: Optional[float]
    calculated_at: datetime

    model_config = {"from_attributes": True}


# =========================
# SCORING RESPONSE
# =========================
class ScoreResponse(BaseModel):
    party_id: int
    score: int
    score_band: str
    confidence: float
    decision: str
    decision_reasons: Optional[List[str]] = None
    explanation: Optional[dict] = None
    computed_at: datetime
    model_version: Optional[str] = None

    model_config = {
        "from_attributes": True,
        "protected_namespaces": (),
    }
