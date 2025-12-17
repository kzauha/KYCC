from sqlalchemy.orm import Session
from app.extractors.kyc_extractor import KYCFeatureExtractor
from app.extractors.transaction_extractor import TransactionFeatureExtractor
from app.extractors.network_extractor import NetworkFeatureExtractor
from app.models.models import Feature, Party
from datetime import datetime
from typing import List, Optional

class FeaturePipelineService:
    """Orchestrates feature extraction from all sources"""
    
    def __init__(self, db: Session):
        self.db = db
        self.extractors = [
            KYCFeatureExtractor(),
            TransactionFeatureExtractor(),
            NetworkFeatureExtractor()
        ]
        
        # Map external source names (like in Dagster) to internal source types
        self.source_name_map = {
            "kyc": "KYC",
            "transaction": "TRANSACTIONS",
            "network": "RELATIONSHIPS"
        }
    
    def extract_all_features(self, party_id: int, as_of_date: datetime = None) -> dict:
        """
        Extract features from all sources for a party.
        """
        return self.extract_features(party_id, as_of_date=as_of_date)

    def extract_features(self, party_id: int, source_types: Optional[List[str]] = None, as_of_date: datetime = None) -> dict:
        """
        Extract features for a party, optionally filtering by source type.
        
        source_types: List of internal source types (e.g. ["KYC", "TRANSACTIONS"]). 
                      If None, runs all extractors.
        as_of_date:   If provided, extracts features as they would have been on this date.
                      Results are NOT stored in DB if date is provided.
        """
        all_features = []
        sources_used = []
        
        # Identify which extractors to run
        target_extractors = self.extractors
        if source_types:
            target_extractors = [e for e in self.extractors if e.get_source_type() in source_types]

        for extractor in target_extractors:
            try:
                # Pass as_of_date to extractor
                features = extractor.extract(party_id, self.db, as_of_date=as_of_date)
                # Tag each feature with its source extractor
                for feat in features:
                    feat.metadata["source_type"] = extractor.get_source_type()
                all_features.extend(features)
                sources_used.append(extractor.get_source_type())
            except Exception as e:
                print(f"Error extracting from {extractor.get_source_type()}: {e}")
        
        # Store features ONLY if running for current state (no custom date)
        if as_of_date is None:
            affected_sources = source_types if source_types else None
            self._store_features(party_id, all_features, affected_sources=affected_sources)
        
        return {
            "party_id": party_id,
            "feature_count": len(all_features),
            "sources": sources_used,
            "features_list": all_features  # Helper to get raw objects if needed
        }

    def run(self, batch_id: str) -> dict:
        """Run feature extraction for all parties in a batch (all sources)."""
        parties = self.db.query(Party).filter(Party.batch_id == batch_id).all()
        processed_count = 0
        
        for party in parties:
            self.extract_all_features(party.id)
            processed_count += 1
            
        return {
            "batch_id": batch_id,
            "processed_parties": processed_count,
            "status": "completed"
        }

    def run_single(self, batch_id: str, source: str) -> dict:
        """
        Run feature extraction for a specific source for all parties in a batch.
        
        source: 'kyc', 'transaction', or 'network'
        """
        internal_source = self.source_name_map.get(source.lower())
        if not internal_source:
             raise ValueError(f"Unknown source: {source}. Valid options: {list(self.source_name_map.keys())}")
             
        parties = self.db.query(Party).filter(Party.batch_id == batch_id).all()
        processed_count = 0
        
        for party in parties:
            self.extract_features(party.id, source_types=[internal_source])
            processed_count += 1
            
        return {
            "batch_id": batch_id,
            "source": source,
            "processed_parties": processed_count,
            "status": "completed"
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
    
    def _store_features(self, party_id: int, features: list, affected_sources: Optional[List[str]] = None):
        """
        Store features in database.
        
        affected_sources: If provided, only expire previous features of these types.
                          If None, expire ALL previous features (assumes full re-run).
        """
        
        # Build expiry query
        query = self.db.query(Feature).filter(
            Feature.party_id == party_id,
            Feature.valid_to == None
        )
        
        if affected_sources:
            query = query.filter(Feature.source_type.in_(affected_sources))
            
        # Mark old features as expired
        query.update({Feature.valid_to: datetime.utcnow()}, synchronize_session=False)
        
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