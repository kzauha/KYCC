# backend/app/extractors/kyc_extractor.py

from app.extractors.base_extractor import BaseFeatureExtractor, FeatureExtractorResult
from app.models.models import Party
from datetime import datetime
from typing import List

class KYCFeatureExtractor(BaseFeatureExtractor):
    """Extract features from Party (KYC) data"""
    
    def get_source_type(self) -> str:
        return "KYC"
    
    def extract(self, party_id: int, db, as_of_date: datetime = None) -> List[FeatureExtractorResult]:
        # Fetch the Party from your existing model
        party = db.query(Party).filter(Party.id == party_id).first()
        
        if not party:
            return []
        
        ref_date = as_of_date or datetime.utcnow()
        
        features = []
        
        # Feature 1: KYC Verification Score
        features.append(FeatureExtractorResult(
            feature_name="kyc_verified",
            feature_value=float(party.kyc_verified),
            confidence=1.0
        ))
        
        # Feature 2: Company Age (from created_at)
        if party.created_at:
            # FIX #9: Calculate age relative to ref_date
            years = (ref_date - party.created_at).days / 365.25
            features.append(FeatureExtractorResult(
                feature_name="company_age_years",
                feature_value=max(0.0, years), # Prevent negative age if created after ref_date (data error usually)
                confidence=0.9
            ))
        
        # Feature 3: Party Type Score
        # Note: party_type is stored as a String in the database, not an Enum
        party_type_scores = {
            "manufacturer": 10,
            "distributor": 8,
            "supplier": 7,
            "retailer": 6,
            "customer": 5
        }
        # Handle both uppercase (from DB) and lowercase party types
        party_type_key = party.party_type.lower() if party.party_type else "customer"
        features.append(FeatureExtractorResult(
            feature_name="party_type_score",
            feature_value=party_type_scores.get(party_type_key, 5),
            confidence=1.0
        ))
        
        # Feature 4: Contact Completeness
        contact_fields = [party.contact_person, party.email, party.phone, party.address]
        completeness = sum(1 for f in contact_fields if f) / len(contact_fields)
        features.append(FeatureExtractorResult(
            feature_name="contact_completeness",
            feature_value=completeness * 100,
            confidence=1.0
        ))
        
        # Feature 5: Has Tax ID (binary)
        features.append(FeatureExtractorResult(
            feature_name="has_tax_id",
            feature_value=1.0 if party.tax_id else 0.0,
            confidence=1.0
        ))
        
        return features