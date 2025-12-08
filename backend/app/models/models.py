from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base

# Define enum types (like dropdown options)
class PartyType(str, enum.Enum):
    SUPPLIER = "supplier"
    MANUFACTURER = "manufacturer"
    DISTRIBUTOR = "distributor"
    RETAILER = "retailer"
    CUSTOMER = "customer"

class RelationshipType(str, enum.Enum):
    SUPPLIES_TO = "supplies_to"
    MANUFACTURES_FOR = "manufactures_for"
    DISTRIBUTES_FOR = "distributes_for"
    SELLS_TO = "sells_to"

class TransactionType(str, enum.Enum):
    INVOICE = "invoice"
    PAYMENT = "payment"
    CREDIT_NOTE = "credit_note"

class Party(Base):
    __tablename__ = "parties"
    
    # Columns (each line is a column in the database)
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    party_type = Column(Enum(PartyType), nullable=False)
    tax_id = Column(String, unique=True, index=True)
    registration_number = Column(String)
    address = Column(Text)
    contact_person = Column(String)
    email = Column(String)
    phone = Column(String)
    kyc_verified = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships (connections to other tables)
    relationships_from = relationship("Relationship", foreign_keys="Relationship.from_party_id", back_populates="from_party")
    relationships_to = relationship("Relationship", foreign_keys="Relationship.to_party_id", back_populates="to_party")
    transactions = relationship(
        "Transaction",
        back_populates="party",
        foreign_keys="[Transaction.party_id]"
    )
    # Explicitly specify foreign key to avoid ambiguity with counterparty_id
    # (Transaction has both `party_id` and `counterparty_id` pointing to Party)
    credit_scores = relationship("CreditScore", back_populates="party")

class Relationship(Base):
    __tablename__ = "relationships"
    
    id = Column(Integer, primary_key=True, index=True)
    from_party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    to_party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    relationship_type = Column(Enum(RelationshipType), nullable=False)
    established_date = Column(DateTime, default=datetime.utcnow)
    
    # These create the reverse links
    from_party = relationship("Party", foreign_keys=[from_party_id], back_populates="relationships_from")
    to_party = relationship("Party", foreign_keys=[to_party_id], back_populates="relationships_to")

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    counterparty_id = Column(Integer, ForeignKey("parties.id"))
    transaction_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    reference = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Main party relationship
    party = relationship(
        "Party", 
        foreign_keys=[party_id], 
        back_populates="transactions"
    )
    
    # Counterparty relationship (optional - the other party in the transaction)
    counterparty = relationship(
        "Party", 
        foreign_keys=[counterparty_id]
    )

class CreditScore(Base):
    __tablename__ = "credit_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    overall_score = Column(Float, nullable=False)
    payment_regularity_score = Column(Float)
    transaction_volume_score = Column(Float)
    kyc_score = Column(Float)
    network_score = Column(Float)
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    party = relationship("Party", back_populates="credit_scores")