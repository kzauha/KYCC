# backend/app/extractors/transaction_extractor.py

from app.extractors.base_extractor import BaseFeatureExtractor, FeatureExtractorResult
from app.models.models import Transaction
from datetime import datetime, timedelta
from typing import List
import numpy as np
from sqlalchemy import func

class TransactionFeatureExtractor(BaseFeatureExtractor):
    """Extract features from Transaction history"""
    
    def get_source_type(self) -> str:
        return "TRANSACTIONS"
    
    def extract(self, party_id: int, db, as_of_date: datetime = None) -> List[FeatureExtractorResult]:
        features = []
        
        # Determine reference date
        ref_date = as_of_date or datetime.utcnow()
        
        # Get transactions from last 6 months relative to ref_date
        six_months_ago = ref_date - timedelta(days=180)
        
        # FIX #9: Temporal Validation - Filter by as_of_date
        transactions = db.query(Transaction).filter(
            Transaction.party_id == party_id,
            Transaction.transaction_date >= six_months_ago,
            Transaction.transaction_date <= ref_date
        ).all()
        
        if not transactions:
            # Return default values if no transactions
            return self._get_default_features()
        
        # Feature 1: Transaction Count
        features.append(FeatureExtractorResult(
            feature_name="transaction_count_6m",
            feature_value=float(len(transactions)),
            confidence=1.0
        ))
        
        # Feature 2: Average Transaction Amount
        amounts = [t.amount for t in transactions]
        avg_amount = sum(amounts) / len(amounts)
        features.append(FeatureExtractorResult(
            feature_name="avg_transaction_amount",
            feature_value=avg_amount,
            confidence=1.0
        ))
        
        # Feature 3: Transaction Volume (total)
        total_volume = sum(amounts)
        features.append(FeatureExtractorResult(
            feature_name="total_transaction_volume_6m",
            feature_value=total_volume,
            confidence=1.0
        ))
        
        # Feature 4: Transaction Regularity (FIX #2: Coefficient of Variation)
        # Group by month and sum amounts
        monthly_volumes = {}
        for txn in transactions:
            month_key = txn.transaction_date.strftime("%Y-%m")
            monthly_volumes[month_key] = monthly_volumes.get(month_key, 0.0) + txn.amount
            
        # Calculate CV
        if not monthly_volumes:
            regularity_score = 0.0
        else:
            volumes = list(monthly_volumes.values())
            
            # Handle single month case
            if len(volumes) < 2:
                regularity_score = 50.0
            else:
                mean_vol = np.mean(volumes)
                std_vol = np.std(volumes)
                
                # CV = std / mean
                if mean_vol < 0.01:
                    cv = 1.0  # Treat as irregular if mean is near zero
                else:
                    cv = std_vol / mean_vol
                
                # Regularity score: 100 * (1 - min(cv, 1.0))
                # High CV (irregular) -> Low Score. Low CV (stable) -> High Score.
                regularity_score = 100.0 * (1.0 - min(cv, 1.0))
                
        features.append(FeatureExtractorResult(
            feature_name="transaction_regularity_score",
            feature_value=float(regularity_score),
            confidence=0.8 if len(monthly_volumes) >= 3 else 0.5
        ))
        
        # Feature 5: Payment Types Diversity
        payment_types = set(t.transaction_type.value for t in transactions)
        features.append(FeatureExtractorResult(
            feature_name="payment_type_diversity",
            feature_value=float(len(payment_types)),
            confidence=1.0
        ))
        
        # Feature 6: Has Recent Activity (last 30 days)
        thirty_days_ago = ref_date - timedelta(days=30)
        recent_count = sum(1 for t in transactions if t.transaction_date >= thirty_days_ago)
        features.append(FeatureExtractorResult(
            feature_name="recent_activity_flag",
            feature_value=1.0 if recent_count > 0 else 0.0,
            confidence=1.0
        ))
        
        return features
    
    def _get_default_features(self) -> List[FeatureExtractorResult]:
        """Return default features when no transactions exist"""
        return [
            FeatureExtractorResult("transaction_count_6m", 0.0, 0.3),
            FeatureExtractorResult("avg_transaction_amount", 0.0, 0.3),
            FeatureExtractorResult("total_transaction_volume_6m", 0.0, 0.3),
            FeatureExtractorResult("transaction_regularity_score", 0.0, 0.3),
            FeatureExtractorResult("payment_type_diversity", 0.0, 0.3),
            FeatureExtractorResult("recent_activity_flag", 0.0, 1.0),
        ]