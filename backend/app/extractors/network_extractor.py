# backend/app/extractors/network_extractor.py

from app.extractors.base_extractor import BaseFeatureExtractor, FeatureExtractorResult
from app.models.models import Relationship
from app.services.network_service import get_downstream_network, get_upstream_network
from typing import List

class NetworkFeatureExtractor(BaseFeatureExtractor):
    """Extract features from business network"""
    
    def get_source_type(self) -> str:
        return "RELATIONSHIPS"
    
    def extract(self, party_id: int, db) -> List[FeatureExtractorResult]:
        features = []
        
        # Feature 1: Direct Counterparty Count
        downstream = db.query(Relationship).filter(
            Relationship.from_party_id == party_id
        ).count()
        
        upstream = db.query(Relationship).filter(
            Relationship.to_party_id == party_id
        ).count()
        
        total_direct = downstream + upstream
        
        features.append(FeatureExtractorResult(
            feature_name="direct_counterparty_count",
            feature_value=float(total_direct),
            confidence=1.0
        ))
        
        # Feature 2: Network Depth (downstream)
        downstream_network = get_downstream_network(db, party_id, max_depth=5)
        max_downstream_depth = max([node['depth'] for node in downstream_network['nodes']], default=0)
        
        features.append(FeatureExtractorResult(
            feature_name="network_depth_downstream",
            feature_value=float(max_downstream_depth),
            confidence=0.9
        ))
        
        # Feature 3: Network Size (total unique parties in network)
        network_size = len(downstream_network['nodes'])
        features.append(FeatureExtractorResult(
            feature_name="network_size",
            feature_value=float(network_size),
            confidence=0.9
        ))
        
        # Feature 4: Supplier Count (upstream)
        features.append(FeatureExtractorResult(
            feature_name="supplier_count",
            feature_value=float(upstream),
            confidence=1.0
        ))
        
        # Feature 5: Customer Count (downstream)
        features.append(FeatureExtractorResult(
            feature_name="customer_count",
            feature_value=float(downstream),
            confidence=1.0
        ))
        
        # Feature 6: Network Balance (ratio of customers to suppliers)
        if upstream > 0:
            balance_ratio = downstream / upstream
        else:
            balance_ratio = downstream if downstream > 0 else 1.0
        
        features.append(FeatureExtractorResult(
            feature_name="network_balance_ratio",
            feature_value=balance_ratio,
            confidence=0.8
        ))
        
        return features