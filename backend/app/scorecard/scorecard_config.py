"""
Scorecard Configuration - Expert-Defined Weights

This module contains the initial scorecard configuration based on domain knowledge.
The scorecard represents human expert understanding of credit risk factors.
ML will initially learn to reproduce these weights, then refine them over time.
"""

from typing import Dict, Any

# Initial expert-defined scorecard (Version 1.0)
# These weights represent domain knowledge about credit risk factors
INITIAL_SCORECARD_V1: Dict[str, Any] = {
    'version': '1.0',
    'base_score': 300,
    'max_score': 900,
    'target_default_rate': 0.05,  # Bottom 5% classified as defaults
    
    'weights': {
        # KYC Features - Identity & Verification (max ~50 points)
        'kyc_verified': 15,           # Boolean: verified adds 15 points
        'has_tax_id': 10,             # Boolean: has tax ID adds 10 points
        'contact_completeness': 5,    # 0-100 scale, normalized contribution
        
        # Company Profile (max ~60 points)
        'company_age_years': 10,      # Per year, capped at 5 years = 50 max
        'party_type_score': 10,       # Based on party type stability
        
        # Transaction Features - Behavioral (max ~75 points)
        'transaction_count_6m': 20,   # Scaled: more transactions = better
        'avg_transaction_amount': 15, # Scaled contribution
        'recent_activity_flag': 25,   # Boolean: active in 30d adds 25 points
        'transaction_regularity_score': 15,  # 0-100 scale
        
        # Network Features - Business Relationships (max ~40 points)
        'network_size': 10,                  # Total connections
        'direct_counterparty_count': 10,     # Direct business partners
        'network_balance_ratio': 10,         # Customer/supplier balance
        'network_depth_downstream': 10,      # Supply chain depth
    },
    
    # Feature scaling configuration
    'feature_scaling': {
        'company_age_years': {'max_value': 5, 'method': 'cap'},
        'transaction_count_6m': {'max_value': 50, 'method': 'cap'},
        'avg_transaction_amount': {'max_value': 100000, 'method': 'log_scale'},
        'network_size': {'max_value': 20, 'method': 'cap'},
        'direct_counterparty_count': {'max_value': 10, 'method': 'cap'},
        'network_depth_downstream': {'max_value': 5, 'method': 'cap'},
    },
    
    'description': 'Initial expert-defined scorecard based on domain knowledge for KYCC credit scoring'
}

# Scorecard version history for audit trail
SCORECARD_VERSIONS = {
    '1.0': INITIAL_SCORECARD_V1,
}


def get_scorecard_config(version: str = '1.0') -> Dict[str, Any]:
    """Get scorecard configuration by version."""
    if version not in SCORECARD_VERSIONS:
        raise ValueError(f"Unknown scorecard version: {version}. Available: {list(SCORECARD_VERSIONS.keys())}")
    return SCORECARD_VERSIONS[version]
