# backend/app/extractors/base_extractor.py

from typing import List, Dict, Any
from abc import ABC, abstractmethod
from datetime import datetime

class FeatureExtractorResult:
    def __init__(self, feature_name: str, feature_value: float, 
                 confidence: float = 1.0, metadata: dict = None):
        self.feature_name = feature_name
        self.feature_value = feature_value
        self.confidence = confidence
        self.metadata = metadata or {}

class BaseFeatureExtractor(ABC):
    """All extractors inherit from this"""
    
    @abstractmethod
    def extract(self, party_id: int, db, as_of_date: datetime = None) -> List[FeatureExtractorResult]:
        """Extract features for a party"""
        pass
    
    @abstractmethod
    def get_source_type(self) -> str:
        """Return 'KYC', 'TRANSACTIONS', 'RELATIONSHIPS', etc."""
        pass