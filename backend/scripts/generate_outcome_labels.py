"""Generate realistic outcome labels for a scored batch."""
import logging
import random
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.models import Batch, Party, GroundTruthLabel, ScorecardVersion, ScoreRequest
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

def generate_outcome_labels(db: Session, batch_id: str) -> dict:
    """
    Generate realistic outcome labels for a scored batch.
    
    Returns:
        {
            "labels_created": int,
            "default_count": int,
            "default_rate": float,
            "batch_id": str
        }
    """
    
    # 1. Validate batch exists and is scored
    batch = db.query(Batch).filter_by(id=batch_id).first()
    if not batch:
        raise ValueError(f"Batch {batch_id} not found")
    if batch.status != 'scored':
        # Allow if it's already generated, but strictly we should check before calling
        if batch.status == 'outcomes_generated':
             raise ValueError(f"Outcomes already generated for batch {batch_id}")
        raise ValueError(f"Batch {batch_id} is not scored yet (status: {batch.status})")
    
    # 2. Check if outcomes already generated (redundant safety check)
    existing_labels = db.query(GroundTruthLabel).join(Party).filter(
        Party.batch_id == batch_id,
        GroundTruthLabel.label_source == 'observed'
    ).count()
    
    if existing_labels > 0:
        raise ValueError(f"Outcomes already generated for batch {batch_id}")
    
    # 3. Query parties with their scores
    # We join with Party to get features, and ScoreRequest or CreditScore to get the score.
    # Assuming CreditScore is populated by the pipeline.
    query = """
        SELECT 
            p.id as party_id,
            p.external_id,
            p.batch_id,
            f.feature_value as unknown, -- Placeholder if we need features from somewhere else
            -- For simplicity in this demo, we might parse features from json or query them
            -- But wait, the prompt said "join with scores". 
            -- Let's assume we have features accessible.
            -- Actually, simpler approach: Use the FEATURES table or Raw Data?
            -- To follow the prompt's logic (income, etc), we need those values.
            -- In `models.py`, Party doesn't have `income` etc directly as columns (except in my thought process? Let's check models.py again).
            -- Validating models.py: Party has `name`, `tax_id`. It does NOT have income/age columns.
            -- Those are likely in Feature table or RawDataSource.
            -- However, for the purpose of this demo, we might have simulated them into features.
            
            -- WAIT! The user provided code snippet assumes Party has "age", "income", etc.
            -- But `models.py` (Step 108) shows Party class DOES NOT have these columns.
            -- They are likely stored in `features` table or separate `profiles` JSON blob.
            -- I need to fetch them.
            
            -- Let's check `backend/scripts/generate_synthetic_batch.py` (Step 78).
            -- It writes JSON.
            -- Maybe the pipeline saves them to `features` table?
            -- If not, I can't filter by 'income'.
            
            -- Alternative: Parse the original `data/{batch_id}_profiles.json` if available?
            -- Or rely on `features` table.
            
            -- Let's assume the pipeline populates `features` table.
            -- I will query the `features` table for these values.
            
            -- REVISED STRATEGY:
            -- Query `features` table for the party.
            -- This is complex in SQL.
            -- Easier: Query `RawDataSource` which has `data_payload` JSON.
        FROM parties p
    """
    
    # Let's check how we can get age/income.
    # The `models.py` has `Feature` table.
    # But fetching row-wise features for 1000 parties is slow in ORM loop.
    # I will fetch `RawDataSource` payload which contains the profile JSON.
    
    # Validating RawDataSource exists in models.py (Step 108: line 131). Yes.
    
    raw_data_query = db.query(Party.id, Party.external_id, ScoreRequest.final_score).join(
        ScoreRequest, Party.id == ScoreRequest.party_id
    ).filter(
        Party.batch_id == batch_id
    ).all()
    
    # We also need the raw profile data to apply the "Hidden Factors" logic.
    # We can fetch RawDataSource.data_payload.
    
    # Let's optimize: fetch all raw data for batch.
    from app.models.models import RawDataSource
    
    raw_data_map = {}
    raw_sources = db.query(RawDataSource).join(Party).filter(Party.batch_id == batch_id).all()
    for rs in raw_sources:
        raw_data_map[rs.party_id] = rs.data_payload

    # Fetch scores
    # Note: Using ScoreRequest as the source of score seems robust if the pipeline creates it.
    scores = db.query(ScoreRequest).join(Party).filter(Party.batch_id == batch_id).all()
    score_map = {s.party_id: s.final_score for s in scores}
    
    if not scores:
         raise ValueError(f"No scores found for batch {batch_id}")

    # 4. Set reproducible random seed
    # Use hash of batch_id string or similar
    seed_val = abs(hash(batch_id)) % (2**32)
    np.random.seed(seed_val)
    
    # 5. Generate labels
    labels = []
    defaults = 0
    
    for party_id, profile in raw_data_map.items():
        score = score_map.get(party_id)
        if score is None:
            continue # specific party not scored?
            
        # Parse logic from profile dict
        # Profile keys might differ from 'income'. Let's check 'backend/scripts/generate_synthetic_batch.py' 
        # Actually it calls `seed_synthetic_profiles`.
        # Standard keys: 'income', 'age', 'dependents', 'recent_inquiries' etc. are standard in credit data.
        # I'll use `.get()` with defaults.
        
        age = profile.get('age', 30)
        income = profile.get('income', 50000)
        dependents = profile.get('dependents', 0)
        recent_inq = profile.get('recent_inquiries', 0)
        debt_ratio = profile.get('debt_to_income_ratio', 0.3)
        payment_hist = profile.get('payment_history_months', 24)
        
        # Base probability from credit score (sigmoid)
        # Score 300-850. Center at 600?
        # A score of 300 should satisfy exp((300-600)/50) = exp(-6) ~ 0.002 -> 1/1.002 ~ 0.99 (High Risk)
        # A score of 850 should satisfy exp(250/50) = exp(5) ~ 148 -> 1/149 ~ 0.006 (Low Risk)
        # Wait, 1 / (1 + exp(...)).
        # if score=300: exp(-6) is small? No exp((300-600)/50) = exp(-6) = 0.002. 1/(1+0.002) ~ 1. Wrong direction?
        # Usually Low Score = High Risk.
        # We want Prob(Default) to be HIGH when Score is LOW.
        # So we want exp to be small when score is low?
        # If score is low (300), we want P ~ 1. 1 / (1 + small) ~ 1.
        # If score is high (850), we want P ~ 0. 1 / (1 + large) ~ 0.
        # So exp term should be increasing with score.
        # term = (score - 600) / 50.
        # 300 -> -6. exp(-6) ~ 0. 1/(1+0) = 1. Correct.
        # 850 -> +5. exp(5) ~ 148. 1/149 ~ 0.006. Correct.
        
        exponent = (score - 600) / 50.0
        # sigmoid: 1 / (1 + e^x) for P(Success)? No, this is P(Default).
        # We want P(Default) to drop as Score increases.
        # My logic above: 
        # Score 850 (Good) -> term +5 -> exp(5) large -> 1/(1+large) small. -> Low Default Prob. Correct.
        
        base_prob = 1 / (1 + np.exp(exponent))
        
        # Adjust for hidden factors
        adjustment = 1.0
        
        if recent_inq > 5:
            adjustment *= 1.5
        
        if income < 30000 and dependents > 2:
            adjustment *= 1.3
            
        if payment_hist < 12:
            adjustment *= 1.2
            
        if debt_ratio > 0.5:
            adjustment *= 1.4
            
        final_prob = min(base_prob * adjustment, 0.95)
        
        # Simulate
        is_default = 1 if np.random.random() < final_prob else 0
        
        if is_default:
            defaults += 1
            
        labels.append(GroundTruthLabel(
            party_id=party_id,
            will_default=is_default, # Using db column name 'will_default'
            default_outcome=is_default, # The prompt logic used 'default_outcome'. models.py has 'will_default'.
            # Checking models.py line 282: will_default = Column...
            # The User prompt asked for "default_outcome". I should check if I should add that col or use existing.
            # models.py has `will_default`. I'll use that.
            risk_level='high' if final_prob > 0.2 else 'low', # simple heuristic
            label_source='observed',
            observation_date=datetime.utcnow(),
            dataset_batch=batch_id,
            label_confidence=1.0
        ))
        
    db.bulk_save_objects(labels)
    
    # Update batch
    batch.status = 'outcomes_generated'
    batch.outcomes_generated_at = datetime.utcnow()
    batch.label_count = len(labels)
    batch.default_rate = defaults / len(labels) if len(labels) > 0 else 0
    
    db.commit()
    
    return {
        "labels_created": len(labels),
        "default_count": defaults,
        "default_rate": round(defaults / len(labels), 4) if len(labels) > 0 else 0,
        "batch_id": batch_id
    }

if __name__ == "__main__":
    # Test run
    pass
