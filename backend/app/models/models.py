from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text, JSON, Index, Boolean, LargeBinary
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
    INDIVIDUAL = "individual"
    BUSINESS = "business"

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
    external_id = Column(String, unique=True, index=True)
    batch_id = Column(String, index=True)
    name = Column(String, nullable=False, index=True)
    # Store party_type as plain string to avoid enum value/name mismatches across DB states
    party_type = Column(String, nullable=False)
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
    accounts = relationship(
        "Account",
        back_populates="party",
        foreign_keys="[Account.party_id]",
        cascade="all, delete-orphan"
    )
    # Explicitly specify foreign key to avoid ambiguity with counterparty_id
    # (Transaction has both `party_id` and `counterparty_id` pointing to Party)
    credit_scores = relationship("CreditScore", back_populates="party")
    ground_truth_label = relationship("GroundTruthLabel", back_populates="party", uselist=False)

class Relationship(Base):
    __tablename__ = "relationships"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String, index=True)
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
    batch_id = Column(String, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
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

    account = relationship("Account", foreign_keys=[account_id], back_populates="transactions")


class Account(Base):
    """Bank account tied to a party."""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String, index=True)
    batch_id = Column(String, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    account_number = Column(String, nullable=False)
    account_type = Column(String, default="checking")
    currency = Column(String, default="USD")
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    party = relationship("Party", back_populates="accounts")
    transactions = relationship("Transaction", foreign_keys="[Transaction.account_id]", back_populates="account")


# ============= NEW MODELS FOR CREDIT SCORING =============

class RawDataSource(Base):
    """Store raw data snapshots for reprocessing"""
    __tablename__ = "raw_data_sources"
    
    id = Column(String, primary_key=True)  # UUID
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    source_type = Column(String, nullable=False)  # 'KYC', 'TRANSACTIONS', etc.
    source_subtype = Column(String)
    data_payload = Column(JSON, nullable=False)  # Store raw data as JSON
    ingested_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)  # 0 = false, 1 = true (SQLite compatible)
    processing_version = Column(String)
    
    party = relationship("Party")


class Feature(Base):
    """Central feature store - all computed features"""
    __tablename__ = "features"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    feature_name = Column(String, nullable=False, index=True)
    feature_value = Column(Float)
    value_text = Column(String)  # For categorical features
    confidence_score = Column(Float)  # 0.0-1.0
    computation_timestamp = Column(DateTime, default=datetime.utcnow)
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_to = Column(DateTime, nullable=True)  # NULL = current version
    source_type = Column(String)
    source_data_id = Column(String, ForeignKey("raw_data_sources.id"))
    feature_version = Column(String)
    feature_metadata = Column(JSON)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    
    party = relationship("Party")
    source_data = relationship("RawDataSource")
    
    __table_args__ = (
        Index('idx_party_feature_valid', 'party_id', 'feature_name', 'valid_to'),
    )


class FeatureDefinition(Base):
    """Metadata about each feature"""
    __tablename__ = "feature_definitions"
    
    feature_name = Column(String, primary_key=True)
    category = Column(String)  # 'stability', 'income', 'behavior'
    data_type = Column(String)  # 'numeric', 'categorical', 'boolean'
    description = Column(Text)
    computation_logic = Column(Text)
    required_sources = Column(JSON)  # ['KYC', 'TRANSACTIONS']
    normalization_method = Column(String)  # 'min_max', 'z_score'
    normalization_params = Column(JSON)  # {min: 0, max: 100}
    default_value = Column(Float)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class ScoreRequest(Base):
    """Log of all scoring requests"""
    __tablename__ = "score_requests"
    
    id = Column(String, primary_key=True)  # UUID
    party_id = Column(Integer, ForeignKey("parties.id"), nullable=False)
    request_timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    model_version = Column(String, nullable=False)
    model_type = Column(String, nullable=False)  # 'scorecard', 'ml_model'
    features_snapshot = Column(JSON, nullable=False)  # All features used
    raw_score = Column(Float)
    final_score = Column(Integer)  # 300-900
    score_band = Column(String)  # 'excellent', 'good', 'fair', 'poor'
    confidence_level = Column(Float)
    decision = Column(String)  # 'approved', 'rejected', 'manual_review'
    decision_reasons = Column(JSON)
    processing_time_ms = Column(Integer)
    api_client_id = Column(String)
    scorecard_version_id = Column(Integer, ForeignKey("scorecard_versions.id"), nullable=True)
    
    party = relationship("Party")


class DecisionRule(Base):
    """Business rules for credit decisions"""
    __tablename__ = "decision_rules"
    
    rule_id = Column(String, primary_key=True)
    rule_name = Column(String, nullable=False)
    condition_expression = Column(Text, nullable=False)
    action = Column(String, nullable=False)  # 'reject', 'flag', 'manual_review'
    priority = Column(Integer, nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Audit trail for all operations"""
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    party_id = Column(Integer, ForeignKey("parties.id"))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String)
    api_client_id = Column(String)
    model_version = Column(String)
    request_payload = Column(JSON)
    response_payload = Column(JSON)
    ip_address = Column(String)
    
    party = relationship("Party")


# ============= EXTEND YOUR EXISTING CreditScore MODEL =============
# Option 1: Keep your existing CreditScore table for backward compatibility
# Option 2: Deprecate it in favor of ScoreRequest table

# Old ScorecardVersion removed in favor of new implementation at bottom of file
# class ScorecardVersion(Base): ...

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
    
    # Add reference to the detailed score request
    score_request_id = Column(String, ForeignKey("score_requests.id"))
    score_request = relationship("ScoreRequest")

    # Link to the specific scorecard version used
    # Updated to point to new scorecard_versions table
    scored_with_version = Column(String(50), ForeignKey("scorecard_versions.version"))
    scorecard_version = relationship("ScorecardVersion", foreign_keys=[scored_with_version])


class GroundTruthLabel(Base):
    """Ground truth labels for synthetic profiles (training data)."""
    __tablename__ = "ground_truth_labels"

    id = Column(Integer, primary_key=True, index=True)
    party_id = Column(Integer, ForeignKey("parties.id"), unique=True, nullable=False, index=True)
    will_default = Column(Integer, nullable=False)  # 0 or 1
    risk_level = Column(String(20), nullable=False)  # high, medium, low
    label_source = Column(String(50), nullable=False)  # scorecard, observed, mixed
    label_confidence = Column(Float, default=1.0)  # 0-1 (0.5 for scorecard, 1.0 for observed)
    scorecard_version = Column(String(20), nullable=True)  # Which scorecard version generated this
    scorecard_raw_score = Column(Float, nullable=True)  # Underlying scorecard score before threshold
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    dataset_batch = Column(String(100), nullable=False, index=True)  # BATCH_001
    
    # Relationship
    party = relationship("Party", back_populates="ground_truth_label")


# ============= MODEL TRAINING AND REGISTRY =============

class ModelRegistry(Base):
    """Registry of trained ML models with performance metrics.
    
    Note: This model matches the actual database schema.
    The model_version column is the primary key.
    """
    __tablename__ = "model_registry"

    model_version = Column(String(50), primary_key=True)  # v1, v2, etc. (PRIMARY KEY)
    model_type = Column(String(50), nullable=True)  # scorecard, ml_model
    model_config = Column(JSON, nullable=True)  # weights, intercept, hyperparams
    feature_list = Column(JSON, nullable=True)  # list of feature names
    intercept = Column(Float, nullable=True)  # base score
    normalization_method = Column(String(50), nullable=True)  # minmax, standard, etc.
    training_date = Column(DateTime, default=datetime.utcnow, nullable=True)
    deployed_date = Column(DateTime, nullable=True)
    is_active = Column(Integer, default=0)  # 0 or 1
    performance_metrics = Column(JSON, nullable=True)  # auc, precision, recall, f1
    scaler_binary = Column(LargeBinary, nullable=True)  # Serialized scaler
    description = Column(Text, nullable=True)
    created_by = Column(String(100), nullable=True)



class ModelExperiment(Base):
    """Hyperparameter tuning experiments for future use."""
    __tablename__ = "model_experiments"

    id = Column(Integer, primary_key=True, index=True)
    experiment_name = Column(String(100), nullable=False, index=True)
    algorithm = Column(String(50), nullable=False)  # logistic_regression, xgboost
    hyperparameters = Column(JSON, nullable=False)  # {C: 0.1, penalty: l2, ...}
    cv_scores = Column(JSON, nullable=False)  # [0.78, 0.81, 0.79, 0.80, 0.82]
    mean_cv_score = Column(Float, nullable=False)
    std_cv_score = Column(Float, nullable=False)
    training_time_seconds = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    notes = Column(Text, nullable=True)



class Batch(Base):
    """Tracks lifecycle of a data batch."""
    __tablename__ = "batches"

    id = Column(String(50), primary_key=True, index=True)
    status = Column(String(50), nullable=False)  # scoring, scored, outcomes_generated, training_ready
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    scored_at = Column(DateTime, nullable=True)
    outcomes_generated_at = Column(DateTime, nullable=True)
    
    profile_count = Column(Integer, default=0)
    label_count = Column(Integer, default=0)
    default_rate = Column(Float, default=0.0)
    
    __table_args__ = (
        Index('idx_batch_status', 'status'),
    )


class TrainingJob(Base):
    """Tracks ML training jobs."""
    __tablename__ = "training_jobs"
    
    id = Column(String(50), primary_key=True)
    status = Column(String(50), nullable=False)  # running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    training_data_count = Column(Integer, default=0)
    
    # Optional link to the resulting scorecard version
    new_version_id = Column(Integer, ForeignKey("scorecard_versions.id"), nullable=True)


class ScorecardVersion(Base):
    """Versioned scorecard storage for credit scoring.
    
    The scorecard is the source of truth for scoring. ML training
    can create new versions with refined weights when it passes
    quality gates.
    
    Attributes:
        version: Version string (e.g., '1.0', '1.1', '2.0')
        status: Lifecycle status (active, retired, failed)
        weights: JSON dict of feature weights
        source: Origin of weights (expert, ml_refined)
        ml_auc: ROC-AUC if ML-refined
    """
    __tablename__ = "scorecard_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(20), unique=True, nullable=False, index=True)
    version_number = Column(Integer, nullable=True, index=True) # Integer version for sequential ordering
    status = Column(String(20), nullable=False, default='active')  # active, archived, failed, draft
    
    # Scorecard configuration
    weights = Column(JSON, nullable=False)  # Feature weights dict
    base_score = Column(Integer, nullable=False, default=300)
    max_score = Column(Integer, nullable=False, default=900)
    scaling_config = Column(JSON, nullable=True)  # Feature scaling config
    
    # Source tracking
    source = Column(String(20), nullable=False, default='expert')  # expert, ml_refined
    ml_model_id = Column(String(50), nullable=True)  # FK to model_registry (model_version)
    ml_auc = Column(Float, nullable=True) # renamed from auc_score to keep consistent with existing
    auc_score = Column(Float, nullable=True) # Adding this column as per new spec, or map to ml_auc? Let's add it to be explicit if needed, or alias.
    # Actually, let's keep ml_auc as the primary one, but add training_data_count
    training_data_count = Column(Integer, nullable=True)
    ml_f1 = Column(Float, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    activated_at = Column(DateTime, nullable=True)
    retired_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True) # As per spec
    created_by = Column(String(100), default='system')
    notes = Column(Text, nullable=True)
    
    def to_config_dict(self):
        """Convert to config dict for ScorecardEngine."""
        return {
            'id': self.id,
            'version': self.version,
            'base_score': self.base_score,
            'max_score': self.max_score,
            'weights': self.weights,
            'feature_scaling': self.scaling_config or {},
        }


