"""Quick seed script to create sample data for frontend testing."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.models.models import Party, GroundTruthLabel, Batch
from datetime import datetime
import random
import uuid

def seed_data():
    db = SessionLocal()
    
    batch_id = 'BATCH_DEMO'
    
    try:
        # Check existing labels count
        existing_labels = db.query(GroundTruthLabel).filter(
            GroundTruthLabel.label_source == 'observed'
        ).count()
        print(f"Existing observed labels: {existing_labels}")
        
        if existing_labels >= 500:
            print("Already have enough labels for training!")
            db.close()
            return
        
        # Get existing parties that don't have labels
        parties_with_labels = db.query(GroundTruthLabel.party_id).all()
        parties_with_labels_ids = [p[0] for p in parties_with_labels]
        
        parties_without_labels = db.query(Party).filter(
            Party.id.notin_(parties_with_labels_ids)
        ).limit(600 - existing_labels).all()
        
        print(f"Found {len(parties_without_labels)} parties without labels")
        
        if len(parties_without_labels) < 100:
            # Create new parties
            print("Creating new parties...")
            for i in range(600):
                uid = uuid.uuid4().hex[:8]
                party = Party(
                    external_id=f'EXT-DEMO-{uid}',
                    name=f'Demo Company {i+1}',
                    party_type=random.choice(['supplier', 'manufacturer', 'distributor', 'retailer', 'customer']),
                    tax_id=f'TAX-DEMO-{uid}',
                    batch_id=batch_id,
                    kyc_verified=1 if random.random() > 0.2 else 0
                )
                db.add(party)
            db.commit()
            
            # Get all parties
            parties_without_labels = db.query(Party).filter(
                Party.batch_id == batch_id
            ).all()
            print(f"Created {len(parties_without_labels)} new parties")
        
        # Create observed labels
        labels_created = 0
        defaults = 0
        for party in parties_without_labels:
            will_default = 1 if random.random() < 0.05 else 0
            if will_default:
                defaults += 1
                risk_level = 'high'
            else:
                risk_level = random.choice(['low', 'medium'])
            
            label = GroundTruthLabel(
                party_id=party.id,
                will_default=will_default,
                risk_level=risk_level,
                label_source='observed',
                label_confidence=1.0,
                dataset_batch=party.batch_id or batch_id,
                created_at=datetime.utcnow()
            )
            db.add(label)
            labels_created += 1
        
        db.commit()
        print(f"Created {labels_created} observed labels ({defaults} defaults)")
        
        # Ensure batch exists with proper status
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            batch = Batch(
                id=batch_id,
                status='outcomes_generated',
                created_at=datetime.utcnow(),
                scored_at=datetime.utcnow(),
                outcomes_generated_at=datetime.utcnow(),
                profile_count=labels_created,
                label_count=labels_created,
                default_rate=0.05
            )
            db.add(batch)
        else:
            batch.status = 'outcomes_generated'
            batch.outcomes_generated_at = datetime.utcnow()
            batch.label_count = labels_created
        
        db.commit()
        
        # Verify counts
        total_labels = db.query(GroundTruthLabel).filter(
            GroundTruthLabel.label_source == 'observed'
        ).count()
        
        print(f"Total observed labels: {total_labels}")
        print(f"Training should now work!" if total_labels >= 500 else f"Need {500 - total_labels} more labels")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
