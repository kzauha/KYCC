# backend/migrations/add_credit_scoring_tables.py

from app.db.database import engine, Base
from app.models import models

def upgrade():
    """Create all new credit scoring tables"""
    Base.metadata.create_all(bind=engine)
    print("✓ Credit scoring tables created")

def seed_initial_data():
    """Add initial scorecard model and feature definitions"""
    from sqlalchemy.orm import Session
    import json
    
    db = Session(bind=engine)
    
    # Add scorecard v1.0
    scorecard = models.ModelRegistry(
        model_version="v1.0",
        model_type="scorecard",
        model_config=json.loads(open("app/models_config/scorecard_v1.json").read()),
        feature_list=["age", "transaction_count", "avg_transaction_amount", ...],
        is_active=1,
        deployed_date=datetime.utcnow(),
        description="Initial scorecard based on KYC + transaction data"
    )
    db.add(scorecard)
    
    # Add feature definitions
    features = [
        models.FeatureDefinition(
            feature_name="transaction_count",
            category="behavior",
            data_type="numeric",
            description="Total number of transactions in last 6 months",
            computation_logic="COUNT(transactions WHERE date > NOW() - 6 months)",
            required_sources=["TRANSACTIONS"],
            normalization_method="min_max",
            normalization_params={"min": 0, "max": 1000},
            is_active=1
        ),
        # ... more features ...
    ]
    db.bulk_save_objects(features)
    
    db.commit()
    print("✓ Initial data seeded")

if __name__ == "__main__":
    upgrade()
    seed_initial_data()