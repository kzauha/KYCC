from __future__ import annotations

from typing import Any, Dict, Optional

from typing import List
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session

from app.services.scorecard_service import compute_score
from app.db.database import get_db
from app.models.models import ScoreRequest, AuditLog
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/scoring", tags=["scoring"])


@router.get("/run")
def run_scoring(
    party_id: str = Query(..., description="Party identifier"),
    source_type: str = Query("synthetic", description="Data source adapter type"),
    name: str = Query("Test Party"),
    accounts: int = Query(2, ge=1, le=20),
    transactions_per_account: int = Query(5, ge=1, le=100),
    start_days_ago: int = Query(30, ge=1, le=365),
    currency: str = Query("USD"),
    persist: bool = Query(True, description="Save results to database"),
    db: Session = Depends(get_db),
):
    """Run scorecard-based scoring for a party using specified data source."""
    params = {
        "party_id": party_id,
        "name": name,
        "accounts": accounts,
        "transactions_per_account": transactions_per_account,
        "start_days_ago": start_days_ago,
        "currency": currency,
    }

    result = compute_score(source_type, params, db=db, persist=persist)
    return result


@router.get("/history/{party_id}")
def get_score_history(
    party_id: int,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get scoring history for a party."""
    scores = (
        db.query(ScoreRequest)
        .filter(ScoreRequest.party_id == party_id)
        .order_by(ScoreRequest.computed_at.desc())
        .limit(limit)
        .all()
    )
    
    return {
        "party_id": party_id,
        "count": len(scores),
        "scores": [
            {
                "score": s.final_score,
                "band": s.score_band,
                "decision": s.decision,
                "confidence": s.confidence,
                "computed_at": s.computed_at.isoformat(),
                "model_version": s.model_version,
            }
            for s in scores
        ],
    }


@router.get("/audit")
def get_audit_log(
    party_id: int = Query(None, description="Filter by party ID"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get audit log of scoring operations."""
    query = db.query(AuditLog).filter(AuditLog.action == "COMPUTE_SCORE")
    
    if party_id:
        query = query.filter(AuditLog.party_id == party_id)
    
    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    
    return {
        "count": len(logs),
        "logs": [
            {
                "party_id": log.party_id,
                "action": log.action,
                "timestamp": log.timestamp.isoformat(),
                "details": log.details,
            }
            for log in logs
        ],
    }


@router.get("/versions")
def get_versions(db: Session = Depends(get_db)):
    """Get all scorecard versions."""
    svc = AnalyticsService(db)
    return svc.get_scorecard_versions()


@router.get("/active")
def get_active_scorecard(db: Session = Depends(get_db)):
    """Get currently active scorecard with weights."""
    from app.services.scorecard_version_service import ScorecardVersionService
    svc = ScorecardVersionService(db)
    config = svc.get_active_scorecard()
    return {
        "version": config.get("version"),
        "source": config.get("source", "expert"),
        "ml_auc": config.get("ml_auc"),
        "base_score": config.get("base_score"),
        "weights": config.get("weights", {})
    }



@router.get("/weights/evolution")
def get_weights_evolution(top_n: int = 5, db: Session = Depends(get_db)):
    """Get weight evolution analytics."""
    svc = AnalyticsService(db)
    return svc.get_weights_evolution(top_n)


@router.get("/impact/{version_id}")
def get_impact_analysis(version_id: int, compare_to: int = None, db: Session = Depends(get_db)):
    """Compare a version against previous version."""
    svc = AnalyticsService(db)
    try:
        return svc.get_score_impact(version_id, compare_to)
    except Exception as e:
        return {"error": str(e)}
