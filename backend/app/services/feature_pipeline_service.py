# backend/app/services/feature_pipeline_service.py

from sqlalchemy.orm import Session
from app.extractors.kyc_extractor import KYCFeatureExtractor
from app.extractors.transaction_extractor import TransactionFeatureExtractor
from app.extractors.network_extractor import NetworkFeatureExtractor
from app.models.models import Feature
from datetime import datetime

class FeaturePipelineService:
    """Orchestrates feature extraction from all sources"""
    
    def __init__(self, db: Session):
        self.db = db
        self.extractors = [
            KYCFeatureExtractor(),
            TransactionFeatureExtractor(),
            NetworkFeatureExtractor()
        ]
    
    def extract_all_features(self, party_id: int) -> dict:
        """
        Extract features from all sources for a party.
        
        Uses your existing data:
        - Party table (KYC)
        - Transaction table
        - Relationship table
        """
        
        all_features = []
        sources_used = []
        
        for extractor in self.extractors:
            try:
                features = extractor.extract(party_id, self.db)
                # Tag each feature with its source extractor
                for feat in features:
                    feat.metadata["source_type"] = extractor.get_source_type()
                all_features.extend(features)
                sources_used.append(extractor.get_source_type())
            except Exception as e:
                print(f"Error extracting from {extractor.get_source_type()}: {e}")
        
        # Store features
        self._store_features(party_id, all_features)
        
        return {
            "party_id": party_id,
            "feature_count": len(all_features),
            "sources": sources_used
        }

    def get_features_for_party(self, party_id: int, db: Session | None = None):
        """Return current (non-expired) features for a party.

        If no current features exist, trigger extraction and refetch.
        """
        session = db or self.db
        features = session.query(Feature).filter(
            Feature.party_id == party_id,
            Feature.valid_to == None
        ).all()

        if not features:
            # Attempt to extract features then refetch
            self.extract_all_features(party_id)
            features = session.query(Feature).filter(
                Feature.party_id == party_id,
                Feature.valid_to == None
            ).all()

        return features
    
    def _store_features(self, party_id: int, features: list):
        """Store features in database"""
        
        # Mark old features as expired
        self.db.query(Feature).filter(
            Feature.party_id == party_id,
            Feature.valid_to == None
        ).update({Feature.valid_to: datetime.utcnow()})
        
        # Insert new features
        for feat in features:
            db_feature = Feature(
                party_id=party_id,
                feature_name=feat.feature_name,
                feature_value=feat.feature_value,
                confidence_score=feat.confidence,
                source_type=feat.metadata.get("source_type", "unknown")
            )
            self.db.add(db_feature)
        
        self.db.commit()