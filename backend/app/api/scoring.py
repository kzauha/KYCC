# backend/app/api/scoring.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.scoring_service import ScoringService
from app.schemas.schemas import ScoreResponse
from typing import Optional

router = APIRouter(prefix="/api/scoring", tags=["scoring"])

@router.post("/score/{party_id}", response_model=ScoreResponse)
def get_credit_score(
    party_id: int,
    model_version: Optional[str] = None,
    include_explanation: bool = True,
    db: Session = Depends(get_db)
):
    """
    Compute credit score for a party.
    
    This uses:
    - Your existing Party data (KYC)
    - Your existing Transaction history
    - Your existing Relationship network
    
    Returns:
    - Credit score (300-900)
    - Score band (excellent/good/fair/poor)
    - Explanation of factors
    """
    scoring_service = ScoringService(db)
    
    try:
        result = scoring_service.compute_score(
            party_id=party_id,
            model_version=model_version,
            include_explanation=include_explanation
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@router.get("/score/{party_id}/history")
def get_score_history(
    party_id: int,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get historical scores for a party"""
    from app.models.models import ScoreRequest as ScoreRequestModel
    
    scores = db.query(ScoreRequestModel).filter(
        ScoreRequestModel.party_id == party_id
    ).order_by(
        ScoreRequestModel.request_timestamp.desc()
    ).limit(limit).all()
    
    return {
        "party_id": party_id,
        "scores": [
            {
                "score": s.final_score,
                "score_band": s.score_band,
                "computed_at": s.request_timestamp.isoformat(),
                "model_version": s.model_version,
                "confidence": s.confidence_level
            }
            for s in scores
        ]
    }


@router.get("/features/{party_id}")
def get_party_features(
    party_id: int,
    db: Session = Depends(get_db)
):
    """
    Get all current features for a party.
    
    Shows what data is being used for scoring.
    """
    from app.models.models import Feature
    
    features = db.query(Feature).filter(
        Feature.party_id == party_id,
        Feature.valid_to == None  # Current version
    ).all()
    
    if not features:
        raise HTTPException(status_code=404, detail="No features found. Run feature extraction first.")
    
    return {
        "party_id": party_id,
        "feature_count": len(features),
        "last_updated": max(f.computation_timestamp for f in features).isoformat(),
        "features": [
            {
                "name": f.feature_name,
                "value": f.feature_value,
                "confidence": f.confidence_score,
                "source": f.source_type,
                "computed_at": f.computation_timestamp.isoformat()
            }
            for f in features
        ]
    }


@router.post("/compute-features/{party_id}")
def compute_features_for_party(
    party_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually trigger feature computation for a party.
    
    This extracts features from:
    - Party (KYC) data
    - Transaction history
    - Business network
    """
    from app.services.feature_pipeline_service import FeaturePipelineService
    
    service = FeaturePipelineService(db)
    
    try:
        result = service.extract_all_features(party_id)
        return {
            "party_id": party_id,
            "status": "completed",
            "features_computed": result["feature_count"],
            "sources_used": result["sources"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))