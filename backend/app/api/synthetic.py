from __future__ import annotations

import os
from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.orm import Session

from app.services.feature_pipeline import get_feature_pipeline
from app.services.synthetic_seed_service import ingest_seed_file, SeedIngestError
from app.db.database import get_db


router = APIRouter(prefix="/synthetic", tags=["synthetic"])


@router.get("/ingest")
def ingest_synthetic(
    party_id: str = Query("P-0001"),
    name: str = Query("Test Party"),
    accounts: int = Query(2, ge=1, le=20),
    transactions_per_account: int = Query(5, ge=1, le=100),
    start_days_ago: int = Query(30, ge=1, le=365),
    currency: str = Query("USD"),
):
    pipeline = get_feature_pipeline(ttl_seconds=300)
    payload = pipeline.ingest(
        "synthetic",
        {
            "party_id": party_id,
            "name": name,
            "accounts": accounts,
            "transactions_per_account": transactions_per_account,
            "start_days_ago": start_days_ago,
            "currency": currency,
        },
    )
    return payload


@router.post("/seed")
def seed_synthetic_batch(
    batch_id: str = Query(..., description="Required batch id for seed run"),
    overwrite: bool = Query(False, description="If true, replace existing parties for this batch/external ids"),
    file_path: str = Query("backend/data/synthetic_profiles.json", description="Path to seed JSON produced by generator"),
    db: Session = Depends(get_db),
):
    if os.getenv("ENABLE_SYNTHETIC_SEED", "0") != "1":
        raise HTTPException(status_code=403, detail="Synthetic seed ingest is disabled")
    try:
        stats = ingest_seed_file(db=db, file_path=file_path, batch_id=batch_id, overwrite=overwrite)
    except SeedIngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"batch_id": batch_id, "overwrite": overwrite, "stats": stats}
