"""
Scorecard Engine - Expert Rules Score Computation

This engine computes credit scores using expert-defined scorecard weights.
It serves as the human knowledge baseline that ML will learn and refine.
"""

from typing import Dict, Any, Optional, List
import math
import numpy as np
from datetime import datetime

from app.scorecard.scorecard_config import get_scorecard_config, INITIAL_SCORECARD_V1


class ScorecardEngine:
    """
    Engine for computing credit scores using expert-defined scorecard rules.
    
    The scorecard represents domain expertise and serves as:
    1. Initial ground truth generator for ML training
    2. Fallback scorer for edge cases without historical data
    3. Baseline for A/B testing against ML-refined models
    """
    
    def __init__(self, version: str = '1.0', config: Optional[Dict[str, Any]] = None):
        """Initialize scorecard engine.
        
        Args:
            version: Version string to lookup (if config not provided)
            config: Optional explicit config dict (overrides version lookup)
        """
        if config:
            self.config = config
            self.version = config.get('version', version)
        else:
            self.config = get_scorecard_config(version)
            self.version = version
            
        self.base_score = self.config['base_score']
        self.max_score = self.config['max_score']
        self.weights = self.config['weights']
        self.scaling = self.config.get('feature_scaling', {})
    
    def compute_scorecard_score(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute credit score for a party using scorecard rules.
        
        Args:
            features: Dictionary of feature name -> value
            
        Returns:
            Dictionary with:
                - score: Final credit score (300-900)
                - raw_score: Unclipped score
                - contributions: Per-feature score contributions
                - missing_features: Features not found in input
        """
        contributions = {}
        missing_features = []
        total_points = 0
        
        for feature_name, weight in self.weights.items():
            if feature_name not in features or features[feature_name] is None:
                missing_features.append(feature_name)
                contributions[feature_name] = 0
                continue
            
            value = features[feature_name]
            contribution = self._compute_feature_contribution(feature_name, value, weight)
            contributions[feature_name] = contribution
            total_points += contribution
        
        raw_score = self.base_score + total_points
        final_score = max(self.base_score, min(self.max_score, raw_score))
        
        return {
            'score': final_score,
            'raw_score': raw_score,
            'contributions': contributions,
            'missing_features': missing_features,
            'scorecard_version': self.version,
            'computed_at': datetime.utcnow().isoformat(),
        }
    
    def _compute_feature_contribution(
        self, 
        feature_name: str, 
        value: Any, 
        weight: float
    ) -> float:
        """Compute the score contribution of a single feature."""
        
        # Handle boolean features
        if feature_name in ['kyc_verified', 'has_tax_id', 'recent_activity_flag']:
            return weight if value else 0
        
        # Handle scaled features
        scaling_config = self.scaling.get(feature_name, {})
        method = scaling_config.get('method', 'linear')
        max_value = scaling_config.get('max_value', 1)
        
        if method == 'cap':
            # Cap value at max, then scale weight proportionally
            capped = min(float(value), max_value)
            return (capped / max_value) * weight
        
        elif method == 'log_scale':
            # Logarithmic scaling for large value ranges
            if value <= 0:
                return 0
            log_value = math.log10(float(value) + 1)
            log_max = math.log10(max_value + 1)
            return min(log_value / log_max, 1.0) * weight
        
        else:  # linear
            # Assume value is already 0-100 or 0-1 scale
            if value > 1:
                normalized = min(float(value) / 100, 1.0)
            else:
                normalized = float(value)
            return normalized * weight
    
    def get_scorecard_weights(self) -> Dict[str, float]:
        """Return the current expert-defined feature weights."""
        return self.weights.copy()
    
    def compute_batch_scores(
        self, 
        features_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Compute scorecard scores for multiple parties."""
        return [self.compute_scorecard_score(f) for f in features_list]
    
    def compare_with_ml_weights(
        self, 
        ml_coefficients: Dict[str, float],
        feature_names: List[str]
    ) -> Dict[str, Any]:
        """
        Compare scorecard weights against ML-learned coefficients.
        
        Returns analysis of where ML agrees/disagrees with expert rules.
        """
        comparison = []
        
        for feature in feature_names:
            scorecard_weight = self.weights.get(feature, 0)
            ml_weight = ml_coefficients.get(feature, 0)
            
            # Normalize for comparison (both to relative scale)
            sc_total = sum(abs(w) for w in self.weights.values())
            ml_total = sum(abs(w) for w in ml_coefficients.values()) or 1
            
            sc_relative = scorecard_weight / sc_total if sc_total else 0
            ml_relative = ml_weight / ml_total
            
            # Calculate difference
            diff = abs(sc_relative - ml_relative)
            agreement = 'high' if diff < 0.1 else 'medium' if diff < 0.3 else 'low'
            
            comparison.append({
                'feature': feature,
                'scorecard_weight': scorecard_weight,
                'ml_coefficient': ml_weight,
                'scorecard_relative': sc_relative,
                'ml_relative': ml_relative,
                'difference': diff,
                'agreement': agreement,
                'sign_match': (scorecard_weight > 0) == (ml_weight > 0) if ml_weight != 0 else True,
            })
        
        # Sort by disagreement level
        comparison.sort(key=lambda x: -x['difference'])
        
        return {
            'comparison': comparison,
            'high_agreement_count': sum(1 for c in comparison if c['agreement'] == 'high'),
            'low_agreement_count': sum(1 for c in comparison if c['agreement'] == 'low'),
            'sign_mismatches': [c['feature'] for c in comparison if not c['sign_match']],
        }
