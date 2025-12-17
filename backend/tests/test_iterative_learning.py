import pytest
from app.db.database import SessionLocal, Base, engine
from app.services.model_registry_service import ModelRegistryService
from app.services.validation_service import TemporalValidationService
from app.services.scoring_service import ScoringService
from app.models.models import Party, ScoreRequest, GroundTruthLabel
import uuid

# Setup DB for tests
@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_temporal_safety_flow(db):
    """
    Test the full Iterative Learning Lifecycle with Safety Checks.
    Flow:
    1. Setup: Register v001 (Bootstrap)
    2. Attempt Score Batch A: Success
    3. Attempt Train Batch A (No Labels): Fail
    4. Ingest Labels Batch A
    5. Train Batch A -> v002
    6. Attempt Score Batch A with v002: Fail (Leakage)
    7. Attempt Score Batch B with v002: Success
    """
    
    # 1. Setup Bootstrap Model
    registry = ModelRegistryService(db)
    bootstrap_version = registry.register_new_version(
        trained_on_batch_id="BOOTSTRAP", 
        model={"intercept": 0.0}, 
        metrics={}, 
        auto_activate=True
    )
    assert bootstrap_version == "v001"
    
    batch_a = "BATCH_A"
    batch_b = "BATCH_B"
    
    # Mock Data for Batch A
    party_a = Party(party_id="P-A1", batch_id=batch_a, name="Test Corp A")
    db.add(party_a)
    db.commit()
    
    # 2. Score Batch A (Online Job Logic)
    validator = TemporalValidationService(db)
    validator.validate_scoring_request(batch_a) # Should pass
    
    svc = ScoringService(db)
    # Mock feature extraction bypassing pipeline
    # We just call compute directly assuming features exist or fallback
    # But compute_batch_scores iterates parties.
    # We need compute_batch_scores to support calling compute_score
    # We might need to mock _ensure_features_exist or insert Feature rows.
    # For this test, we assume features are not strictly required if model allows defaults?
    # Our scoring service implementation handles missing features with 0.
    
    summary = svc.compute_batch_scores(batch_id=batch_a, model_version="v001")
    assert summary["scored"] == 1
    
    # 3. Attempt Train Batch A (Before Labels)
    with pytest.raises(ValueError, match="labels not ingested"):
        validator.validate_training_request(batch_a)
        
    # 4. Ingest Labels
    label = GroundTruthLabel(
        party_id="P-A1", 
        dataset_batch=batch_a,
        label_value=0, # Non-default
        event_timestamp="2023-01-01"
    )
    db.add(label)
    db.commit()
    
    # 5. Validate Training Request (Now Pass)
    validator.validate_training_request(batch_a)
    
    # Train & Register v002
    v_new_id = registry.register_new_version(
        trained_on_batch_id=batch_a,
        model={"intercept": 0.5},
        metrics={"auc": 0.8},
        auto_activate=True
    )
    assert v_new_id == "v002"
    
    # 6. Attempt Score Batch A with v002 (Temporal Leakage)
    # v002 was trained on Batch A.
    # validate_scoring_request should detect this.
    
    with pytest.raises(ValueError, match="TEMPORAL LEAKAGE"):
        validator.validate_scoring_request(batch_a)
        
    # 7. Score Batch B with v002
    party_b = Party(party_id="P-B1", batch_id=batch_b, name="Test Corp B")
    db.add(party_b)
    db.commit()
    
    validator.validate_scoring_request(batch_b) # Should Pass
    summary_b = svc.compute_batch_scores(batch_id=batch_b, model_version="v002")
    assert summary_b["scored"] == 1
    
    print("✅ Full Temporal Safety Test Passed")
