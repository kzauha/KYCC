# backend/app/extractors/transaction_extractor.py

from app.extractors.base_extractor import BaseFeatureExtractor, FeatureExtractorResult
from app.models.models import Transaction
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import func

class TransactionFeatureExtractor(BaseFeatureExtractor):
    """Extract features from Transaction history"""
    
    def get_source_type(self) -> str:
        return "TRANSACTIONS"
    
    def extract(self, party_id: int, db) -> List[FeatureExtractorResult]:
        features = []
        
        # Get transactions from last 6 months
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        transactions = db.query(Transaction).filter(
            Transaction.party_id == party_id,
            Transaction.transaction_date >= six_months_ago
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
        
        # Feature 4: Transaction Regularity
        # Group by month
        monthly_counts = {}
        for txn in transactions:
            month_key = txn.transaction_date.strftime("%Y-%m")
            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
        
        # Standard deviation of monthly counts (lower = more regular)
        if len(monthly_counts) > 1:
            monthly_values = list(monthly_counts.values())
            mean = sum(monthly_values) / len(monthly_values)
            variance = sum((x - mean) ** 2 for x in monthly_values) / len(monthly_values)
            std_dev = variance ** 0.5
            regularity_score = max(0, 100 - (std_dev * 10))  # Higher = more regular
        else:
            regularity_score = 50.0  # Neutral if not enough data
        
        features.append(FeatureExtractorResult(
            feature_name="transaction_regularity_score",
            feature_value=regularity_score,
            confidence=0.8 if len(monthly_counts) >= 3 else 0.5
        ))
        
        # Feature 5: Payment Types Diversity
        payment_types = set(t.transaction_type.value for t in transactions)
        features.append(FeatureExtractorResult(
            feature_name="payment_type_diversity",
            feature_value=float(len(payment_types)),
            confidence=1.0
        ))
        
        # Feature 6: Has Recent Activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
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