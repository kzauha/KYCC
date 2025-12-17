from sqlalchemy.orm import Session
from app.models.models import Party, Transaction, GroundTruthLabel, ModelRegistry, ModelExperiment
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
            Transaction.party_id == party_id,
            Transaction.counterparty_id == party_id
        )
    ).order_by(Transaction.transaction_date.desc()).offset(skip).limit(limit).all()
    
    return transactions


# ============= GROUND TRUTH LABEL CRUD OPERATIONS =============

def create_ground_truth_label(
    db: Session,
    party_id: int,
    will_default: int,
    risk_level: str,
    label_source: str,
    reason: str = None,
    label_confidence: float = 1.0,
    dataset_batch: str = "LABELED_TRAIN_001"
) -> GroundTruthLabel:
    """Create ground truth label for a party.
    
    Args:
        db: Database session
        party_id: ID of the party
        will_default: 0 or 1 (binary label)
        risk_level: One of 'high', 'medium', 'low'
        label_source: Source of the label ('synthetic', 'manual', 'historical')
        reason: Optional explanation for the label
        label_confidence: Confidence score (0-1), defaults to 1.0
        dataset_batch: Batch identifier for the dataset
    
    Returns:
        The created GroundTruthLabel record
    """
    db_label = GroundTruthLabel(
        party_id=party_id,
        will_default=will_default,
        risk_level=risk_level,
        label_source=label_source,
        reason=reason,
        label_confidence=label_confidence,
        dataset_batch=dataset_batch
    )
    db.add(db_label)
    db.commit()
    db.refresh(db_label)
    return db_label


def get_ground_truth_label(db: Session, label_id: int) -> Optional[GroundTruthLabel]:
    """Get ground truth label by ID.
    
    Args:
        db: Database session
        label_id: ID of the label
    
    Returns:
        GroundTruthLabel or None if not found
    """
    return db.query(GroundTruthLabel).filter(GroundTruthLabel.id == label_id).first()


def get_ground_truth_by_party_id(db: Session, party_id: int) -> Optional[GroundTruthLabel]:
    """Get ground truth label by party ID.
    
    Args:
        db: Database session
        party_id: ID of the party
    
    Returns:
        GroundTruthLabel or None if not found
    """
    return db.query(GroundTruthLabel).filter(GroundTruthLabel.party_id == party_id).first()


def get_ground_truth_by_batch(db: Session, dataset_batch: str) -> List[GroundTruthLabel]:
    """Get all ground truth labels in a batch.
    
    Args:
        db: Database session
        dataset_batch: Batch identifier
    
    Returns:
        List of GroundTruthLabel records
    """
    return db.query(GroundTruthLabel).filter(GroundTruthLabel.dataset_batch == dataset_batch).all()


def delete_ground_truth_label(db: Session, label_id: int) -> bool:
    """Delete ground truth label by ID.
    
    Args:
        db: Database session
        label_id: ID of the label to delete
    
    Returns:
        True if deleted, False if not found
    """
    label = db.query(GroundTruthLabel).filter(GroundTruthLabel.id == label_id).first()
    if label:
        db.delete(label)
        db.commit()
        return True
    return False


# ============= MODEL REGISTRY CRUD OPERATIONS =============

def create_model_registry(
    db: Session,
    model_version: str,
    model_type: str,
    model_config: dict,
    feature_list: list = None,
    intercept: float = None,
    performance_metrics: dict = None,
    description: str = None,
    scaler_binary: bytes = None
) -> ModelRegistry:
    """Create model registry entry.
    
    Args:
        db: Database session
        model_version: Version string (e.g., 'v1', 'v2')
        model_type: Type of model ('scorecard', 'ml_model')
        model_config: Dict with model config (weights, hyperparams)
        feature_list: List of feature names used by the model
        intercept: Base score / intercept value
        performance_metrics: Dict with performance metrics (auc, precision, recall, f1)
        description: Optional description of the model
        scaler_binary: Serialized scaler object
    
    Returns:
        The created ModelRegistry record
    """
    db_model = ModelRegistry(
        model_version=model_version,
        model_type=model_type,
        model_config=model_config,
        feature_list=feature_list,
        intercept=intercept,
        performance_metrics=performance_metrics,
        description=description,
        scaler_binary=scaler_binary
    )
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


def get_model_registry(db: Session, registry_id: int) -> Optional[ModelRegistry]:
    """Get model by registry ID.
    
    Args:
        db: Database session
        registry_id: ID of the model registry entry
    
    Returns:
        ModelRegistry or None if not found
    """
    return db.query(ModelRegistry).filter(ModelRegistry.id == registry_id).first()


def get_active_model(db: Session, model_name: str) -> Optional[ModelRegistry]:
    """Get currently active model by name.
    
    Args:
        db: Database session
        model_name: Name of the model
    
    Returns:
        ModelRegistry or None if no active model found
    """
    return db.query(ModelRegistry).filter(
        ModelRegistry.model_name == model_name,
        ModelRegistry.is_active == 1
    ).first()


def update_model_is_active(
    db: Session,
    model_version: str,
    is_active: bool
) -> Optional[ModelRegistry]:
    """Update is_active flag for a model.
    
    Args:
        db: Database session
        model_version: Version of the model
        is_active: True to activate, False to deactivate
    
    Returns:
        Updated ModelRegistry or None if not found
    """
    db_model = db.query(ModelRegistry).filter(ModelRegistry.model_version == model_version).first()
    if not db_model:
        return None
    
    db_model.is_active = 1 if is_active else 0
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


def get_all_models_for_name(db: Session, model_name: str) -> List[ModelRegistry]:
    """Get all versions of a model.
    
    Args:
        db: Database session
        model_name: Name of the model
    
    Returns:
        List of ModelRegistry records for the model name
    """
    return db.query(ModelRegistry).filter(
        ModelRegistry.model_name == model_name
    ).order_by(ModelRegistry.created_at.desc()).all()


def list_all_active_models(db: Session) -> List[ModelRegistry]:
    """List all currently active models.
    
    Args:
        db: Database session
    
    Returns:
        List of active ModelRegistry records
    """
    return db.query(ModelRegistry).filter(
        ModelRegistry.is_active == 1
    ).order_by(ModelRegistry.created_at.desc()).all()


# ============= MODEL EXPERIMENT CRUD OPERATIONS =============

def create_model_experiment(
    db: Session,
    experiment_name: str,
    algorithm: str,
    hyperparameters: dict,
    cv_scores: list,
    mean_cv_score: float,
    std_cv_score: float,
    training_time_seconds: float,
    notes: str = None
) -> ModelExperiment:
    """Create experiment record.
    
    Args:
        db: Database session
        experiment_name: Name of the experiment
        algorithm: Algorithm name (e.g., 'logistic_regression', 'xgboost')
        hyperparameters: Dict of hyperparameters
        cv_scores: List of cross-validation scores
        mean_cv_score: Mean cross-validation score
        std_cv_score: Standard deviation of CV scores
        training_time_seconds: Training time in seconds
        notes: Optional notes about the experiment
    
    Returns:
        The created ModelExperiment record
    """
    db_experiment = ModelExperiment(
        experiment_name=experiment_name,
        algorithm=algorithm,
        hyperparameters=hyperparameters,
        cv_scores=cv_scores,
        mean_cv_score=mean_cv_score,
        std_cv_score=std_cv_score,
        training_time_seconds=training_time_seconds,
        notes=notes
    )
    db.add(db_experiment)
    db.commit()
    db.refresh(db_experiment)
    return db_experiment


def get_model_experiment(db: Session, experiment_id: int) -> Optional[ModelExperiment]:
    """Get experiment by ID.
    
    Args:
        db: Database session
        experiment_id: ID of the experiment
    
    Returns:
        ModelExperiment or None if not found
    """
    return db.query(ModelExperiment).filter(ModelExperiment.id == experiment_id).first()


def list_experiments(db: Session, algorithm: str = None) -> List[ModelExperiment]:
    """List experiments, optionally filtered by algorithm.
    
    Args:
        db: Database session
        algorithm: Optional algorithm name to filter by
    
    Returns:
        List of ModelExperiment records
    """
    query = db.query(ModelExperiment)
    if algorithm:
        query = query.filter(ModelExperiment.algorithm == algorithm)
    return query.order_by(ModelExperiment.created_at.desc()).all()


def count_parties(db: Session, batch_id: str) -> int:
    """Count parties in a specific batch."""
    return db.query(Party).filter(Party.batch_id == batch_id).count()


def count_transactions(db: Session, batch_id: str) -> int:
    """Count transactions in a specific batch."""
    return db.query(Transaction).filter(Transaction.batch_id == batch_id).count()
