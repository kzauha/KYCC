"""
KYCC FastAPI REST API
Combines modular routers with utility endpoints (health, stats)
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import routers from modular structure
from app.api import parties, relationships
from app.api import synthetic
from app.api import scoring_v2
from app.api import pipeline

# Database objects and dependency
from app.db.database import engine, Base, get_db, init_db
from app.api import scoring_v2

# Models used by the stats endpoint
from app.models.models import Party, Relationship, ScoreRequest

# Ensure DB tables exist (safe for dev) - call AFTER all imports to avoid circular deps
init_db()

# Initialize FastAPI app
app = FastAPI(
    title="KYCC MVP API",
    description="Know Your Customer's Customer - Supply Chain Management API",
    version="1.0.0",
)

# CORS config for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:8080",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(parties.router)
app.include_router(relationships.router)
app.include_router(scoring_v2.router)
app.include_router(synthetic.router)
app.include_router(pipeline.router)


@app.get("/")
def root():
    """API health check and basic info"""
    return {
        "message": "KYCC API is running",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "endpoints": {
            "parties": "/api/parties",
            "relationships": "/api/relationships",
            "network": "/api/parties/{id}/network",
            "scoring": "/api/scoring/score/{party_id}",
            "scoring_run": "/api/scoring/run",
            "scoring_history": "/api/scoring/history/{party_id}",
            "scoring_audit": "/api/scoring/audit",
            "stats": "/api/stats",
            "synthetic_ingest": "/synthetic/ingest",
        },
    }


@app.get("/health")
def health_check():
    """Simple health endpoint"""
    return {"status": "healthy", "database": "connected"}


@app.get("/api/stats")
def get_statistics(db: Session = Depends(get_db)):
    """Return system statistics: counts, average KYC, and credit scoring stats"""
    total_parties = db.query(Party).count()
    total_relationships = db.query(Relationship).count()

    # Count by party type
    party_type_counts = {}
    for party_type in ["supplier", "manufacturer", "distributor", "retailer", "customer"]:
        party_type_counts[party_type] = (
            db.query(Party).filter(Party.party_type == party_type).count()
        )

    # Average KYC score
    avg_kyc = 0.0
    if total_parties > 0:
        all_parties = db.query(Party).all()
        avg_kyc = sum(getattr(p, "kyc_verified", 0) or 0 for p in all_parties) / total_parties

    # NEW: Credit scoring statistics
    total_scores = db.query(ScoreRequest).count()
    avg_credit_score = 0.0
    score_distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
    
    if total_scores > 0:
        all_scores = db.query(ScoreRequest).all()
        avg_credit_score = sum(s.final_score for s in all_scores) / total_scores
        
        # Count by score band
        for score in all_scores:
            band = score.score_band or "unknown"
            if band in score_distribution:
                score_distribution[band] += 1

    return {
        "total_parties": total_parties,
        "total_relationships": total_relationships,
        "parties_by_type": party_type_counts,
        "average_kyc_score": round(avg_kyc, 2),
        # NEW: Credit scoring stats
        "credit_scoring": {
            "total_scores_computed": total_scores,
            "average_credit_score": round(avg_credit_score, 0) if avg_credit_score else None,
            "score_distribution": score_distribution,
        }
    }



# Run with:
#   uvicorn main:app --reload --port 8000
# or (if using package layout):
#   uvicorn app.main:app --reload
