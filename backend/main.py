"""
KYCC FastAPI REST API
Combines modular routers with utility endpoints (health, stats)
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import routers from modular structure
from app.api import parties, relationships

# Database objects and dependency
from app.db.database import engine, Base, get_db

# Models used by the stats endpoint
from app.models.models import Party, Relationship

# Ensure DB tables exist (safe for dev)
Base.metadata.create_all(bind=engine)

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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(parties.router)
app.include_router(relationships.router)


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
            "stats": "/api/stats",
        },
    }


@app.get("/health")
def health_check():
    """Simple health endpoint"""
    return {"status": "healthy", "database": "connected"}


@app.get("/api/stats")
def get_statistics(db: Session = Depends(get_db)):
    """Return simple system statistics: counts and average KYC"""
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

    return {
        "total_parties": total_parties,
        "total_relationships": total_relationships,
        "parties_by_type": party_type_counts,
        "average_kyc_score": round(avg_kyc, 2),
    }


# Run with:
#   uvicorn main:app --reload --port 8000
# or (if using package layout):
#   uvicorn app.main:app --reload
