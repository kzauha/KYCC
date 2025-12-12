# backend/app/extractors/kyc_extractor.py

from app.extractors.base_extractor import BaseFeatureExtractor, FeatureExtractorResult
from app.models.models import Party
from datetime import datetime
from typing import List

class KYCFeatureExtractor(BaseFeatureExtractor):
    """Extract features from Party (KYC) data"""
    
    def get_source_type(self) -> str:
        return "KYC"
    
    def extract(self, party_id: int, db) -> List[FeatureExtractorResult]:
        # Fetch the Party from your existing model
        party = db.query(Party).filter(Party.id == party_id).first()
        
        if not party:
            return []
        
        features = []
        
        # Feature 1: KYC Verification Score
        features.append(FeatureExtractorResult(
            feature_name="kyc_verified",
            feature_value=float(party.kyc_verified),
            confidence=1.0
        ))
        
        # Feature 2: Company Age (from created_at)
        if party.created_at:
            years = (datetime.utcnow() - party.created_at).days / 365.25
            features.append(FeatureExtractorResult(
                feature_name="company_age_years",
                feature_value=years,
                confidence=0.9
            ))
        
        # Feature 3: Party Type Score
        party_type_scores = {
            "manufacturer": 10,
            "distributor": 8,
            "supplier": 7,
            "retailer": 6,
            "customer": 5
        }
        features.append(FeatureExtractorResult(
            feature_name="party_type_score",
            feature_value=party_type_scores.get(party.party_type.value, 0),
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