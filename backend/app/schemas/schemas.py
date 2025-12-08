from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.models import PartyType, RelationshipType, TransactionType

# Party Schemas
class PartyBase(BaseModel):
    """Base schema with common fields"""
    name: str
    party_type: PartyType
    tax_id: Optional[str] = None  # Optional means it can be null
    registration_number: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    kyc_verified: int = 0  # Default value

class PartyCreate(PartyBase):
    """Schema for creating a new party (what the API accepts)"""
    pass  # Inherits everything from PartyBase

class PartyResponse(PartyBase):
    """Schema for returning party data (what the API sends back)"""
    id: int  # Includes the ID (which doesn't exist until saved)
    created_at: datetime
    updated_at: datetime
    
    # Pydantic v2: use `model_config` to allow creating models from ORM/attributes
    model_config = {"from_attributes": True}

# Relationship Schemas
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

# Transaction Schemas
class TransactionCreate(BaseModel):
    party_id: int
    counterparty_id: Optional[int] = None
    transaction_date: datetime
    amount: float
    transaction_type: TransactionType
    reference: Optional[str] = None

class TransactionResponse(TransactionCreate):
    id: int
    created_at: datetime
    
    model_config = {"from_attributes": True}

# Credit Score Schemas
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