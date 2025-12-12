import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.scorecard_service import compute_score
from app.db.database import SessionLocal
from app.models.models import ScoreRequest, Feature, AuditLog


def test_compute_score_persists_to_database():
    """Test that compute_score saves to database when persist=True."""
    db = SessionLocal()
    try:
        # Create test party if it doesn't exist
        from app.models.models import Party, PartyType
        party = db.query(Party).filter(Party.id == 999).first()
        if not party:
            party = Party(id=999, name="Test Party 999", party_type=PartyType.SUPPLIER)
            db.add(party)
            db.commit()
        
        # Clear existing test data
        db.query(ScoreRequest).filter(ScoreRequest.party_id == 999).delete()
        db.query(Feature).filter(Feature.party_id == 999).delete()
        db.query(AuditLog).filter(AuditLog.party_id == 999, AuditLog.event_type == "COMPUTE_SCORE").delete()
        db.commit()
        
        # Compute score with persistence
        result = compute_score(
            "synthetic",
            {"party_id": "P-999", "name": "Persist Test", "accounts": 1, "transactions_per_account": 2},
            db=db,
            persist=True
        )
        
        assert result["party_id"] == "P-999"
        assert "total_score" in result
        
        # Verify score request was saved
        score_req = db.query(ScoreRequest).filter(ScoreRequest.party_id == 999).first()
        assert score_req is not None
        assert score_req.final_score == result["total_score"]
        assert score_req.score_band == result["band"]
        
        # Verify features were saved
        features = db.query(Feature).filter(Feature.party_id == 999).all()
        assert len(features) > 0
        
        # Verify audit log
        audit = db.query(AuditLog).filter(AuditLog.party_id == 999, AuditLog.event_type == "COMPUTE_SCORE").first()
        assert audit is not None
        
    finally:
        # Cleanup
        db.query(ScoreRequest).filter(ScoreRequest.party_id == 999).delete()
        db.query(Feature).filter(Feature.party_id == 999).delete()
        db.query(AuditLog).filter(AuditLog.party_id == 999, AuditLog.event_type == "COMPUTE_SCORE").delete()
        db.commit()
        db.close()


def test_compute_score_without_persistence():
    """Test that compute_score works without database when persist=False."""
    result = compute_score(
        "synthetic",
        {"party_id": "P-888", "name": "No Persist", "accounts": 1, "transactions_per_account": 2},
        db=None,
        persist=False
    )
    
    assert result["party_id"] == "P-888"
    assert "total_score" in result
    assert "band" in result
