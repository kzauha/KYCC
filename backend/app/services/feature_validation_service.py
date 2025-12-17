"""Feature validation service for ML pipeline.

Validates that features extracted for parties meet quality standards:
- Completeness: all expected features exist
- Range: values within acceptable bounds
- Consistency: cross-feature validation

Used before training to ensure data quality.
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from app.db.database import SessionLocal
from app.db import crud
from app.services.feature_pipeline_service import FeaturePipelineService


class FeatureValidationStatus(str, Enum):
    """Validation result status."""
    VALID = "valid"
    INCOMPLETE = "incomplete"
    OUT_OF_RANGE = "out_of_range"
    INCONSISTENT = "inconsistent"


@dataclass
class FeatureValidationIssue:
    """Single validation issue."""
    party_id: int
    issue_type: str  # Missing, OutOfRange, Inconsistent
    feature_name: str
    expected_condition: str
    actual_value: Any
    severity: str = "warning"  # warning or error


class FeatureValidationService:
    """Validate features before model training."""

    # Expected features that must exist (must match extractor output names)
    REQUIRED_FEATURES = [
        'kyc_verified',              # From KYCFeatureExtractor
        'company_age_years',         # From KYCFeatureExtractor
        'party_type_score',          # From KYCFeatureExtractor
        'contact_completeness',      # From KYCFeatureExtractor
        'has_tax_id',                # From KYCFeatureExtractor
        'transaction_count_6m',      # From TransactionFeatureExtractor
        'avg_transaction_amount',    # From TransactionFeatureExtractor
        'transaction_regularity_score',  # From TransactionFeatureExtractor
        'network_size'               # From NetworkFeatureExtractor
    ]

    # Feature ranges: (min, max) or None for no limit
    FEATURE_RANGES = {
        'kyc_verified': (0, 1),              # Binary: 0 or 1
        'company_age_years': (0, 150),
        'party_type_score': (0, 10),
        'contact_completeness': (0, 100),
        'has_tax_id': (0, 1),
        'transaction_count_6m': (0, 100000),
        'avg_transaction_amount': (0, 10000000),
        'transaction_regularity_score': (0, 100),
        'network_size': (0, 10000)
    }

    def __init__(self, db_session=None, feature_pipeline_service=None):
        """Initialize validation service.
        
        Args:
            db_session: Optional database session
            feature_pipeline_service: Optional FeaturePipelineService instance
        """
        self.db = db_session or SessionLocal()
        self.feature_pipeline = feature_pipeline_service or FeaturePipelineService(self.db)
        self.validation_issues: List[FeatureValidationIssue] = []

    def validate_feature_completeness(self, party_id: int) -> Tuple[bool, List[str]]:
        """Check that all required features exist and are not NULL.
        
        Args:
            party_id: Party ID to validate
            
        Returns:
            (is_valid, missing_features_list)
        """
        try:
            features = self.feature_pipeline.get_features_for_party(
                party_id, 
                self.db
            )
            
            # Convert to dict keyed by feature name
            feature_dict = {f.feature_name: f.feature_value for f in features}
            
            missing = []
            for required_feature in self.REQUIRED_FEATURES:
                if required_feature not in feature_dict:
                    missing.append(required_feature)
                elif feature_dict[required_feature] is None:
                    missing.append(f"{required_feature} (NULL)")
            
            return len(missing) == 0, missing
            
        except Exception as e:
            return False, [f"Exception during validation: {str(e)}"]

    def validate_feature_ranges(self, party_id: int) -> Tuple[bool, List[FeatureValidationIssue]]:
        """Check that feature values are within acceptable ranges.
        
        Args:
            party_id: Party ID to validate
            
        Returns:
            (is_valid, issues_list)
        """
        issues = []
        
        try:
            features = self.feature_pipeline.get_features_for_party(party_id, self.db)
            feature_dict = {f.feature_name: f.feature_value for f in features}
            
            for feature_name, (min_val, max_val) in self.FEATURE_RANGES.items():
                if feature_name not in feature_dict:
                    continue
                
                value = feature_dict[feature_name]
                
                if value is None:
                    continue
                
                if value < min_val or value > max_val:
                    issues.append(FeatureValidationIssue(
                        party_id=party_id,
                        issue_type='OutOfRange',
                        feature_name=feature_name,
                        expected_condition=f"[{min_val}, {max_val}]",
                        actual_value=value,
                        severity='error'
                    ))
            
            return len(issues) == 0, issues
            
        except Exception as e:
            return False, [FeatureValidationIssue(
                party_id=party_id,
                issue_type='Exception',
                feature_name='all',
                expected_condition='valid',
                actual_value=str(e),
                severity='error'
            )]

    def validate_feature_consistency(self, party_id: int) -> Tuple[bool, List[FeatureValidationIssue]]:
        """Cross-validate features for logical consistency.
        
        Examples:
        - If txn_count=0, then avg_amount should be 0
        - If balance_total=0, then regularity should be 0
        
        Args:
            party_id: Party ID to validate
            
        Returns:
            (is_valid, issues_list)
        """
        issues = []
        
        try:
            features = self.feature_pipeline.get_features_for_party(party_id, self.db)
            feature_dict = {f.feature_name: f.feature_value for f in features}
            
            # Consistency check 1: txn_count=0 → avg_amount should be 0
            if feature_dict.get('txn_count') == 0 and feature_dict.get('avg_amount', 0) > 0:
                issues.append(FeatureValidationIssue(
                    party_id=party_id,
                    issue_type='Inconsistent',
                    feature_name='txn_count/avg_amount',
                    expected_condition='if txn_count=0, then avg_amount=0',
                    actual_value=f"txn_count={feature_dict['txn_count']}, avg_amount={feature_dict.get('avg_amount')}",
                    severity='warning'
                ))
            
            # Consistency check 2: regularity > 0 requires txn_count > 0
            if feature_dict.get('regularity', 0) > 0 and feature_dict.get('txn_count', 0) == 0:
                issues.append(FeatureValidationIssue(
                    party_id=party_id,
                    issue_type='Inconsistent',
                    feature_name='regularity/txn_count',
                    expected_condition='if regularity>0, then txn_count>0',
                    actual_value=f"regularity={feature_dict.get('regularity')}, txn_count={feature_dict['txn_count']}",
                    severity='warning'
                ))
            
            return len(issues) == 0, issues
            
        except Exception as e:
            return False, [FeatureValidationIssue(
                party_id=party_id,
                issue_type='Exception',
                feature_name='all',
                expected_condition='consistent',
                actual_value=str(e),
                severity='error'
            )]

    def validate_party(self, party_id: int) -> Dict[str, Any]:
        """Validate a single party's features across all dimensions.
        
        Args:
            party_id: Party ID to validate
            
        Returns:
            Validation report for party
        """
        completeness_valid, missing = self.validate_feature_completeness(party_id)
        range_valid, range_issues = self.validate_feature_ranges(party_id)
        consistency_valid, consistency_issues = self.validate_feature_consistency(party_id)
        
        all_issues = range_issues + consistency_issues
        
        return {
            'party_id': party_id,
            'is_valid': completeness_valid and range_valid and consistency_valid,
            'completeness_valid': completeness_valid,
            'range_valid': range_valid,
            'consistency_valid': consistency_valid,
            'missing_features': missing,
            'issues': [asdict(issue) for issue in all_issues]
        }

    def generate_validation_report(self, batch_id: str) -> Dict[str, Any]:
        """Validate all parties in a batch and generate report.
        
        Args:
            batch_id: Batch identifier (e.g., 'LABELED_TRAIN_001')
            
        Returns:
            Validation report with statistics
        """
        # Get all parties in batch
        parties = self.db.query(crud.Party).filter(
            crud.Party.batch_id == batch_id
        ).all()
        
        if not parties:
            return {
                'success': False,
                'error': f'No parties found for batch {batch_id}',
                'batch_id': batch_id
            }
        
        party_reports = []
        valid_count = 0
        total_issues = []
        
        for party in parties:
            report = self.validate_party(party.id)
            party_reports.append(report)
            
            if report['is_valid']:
                valid_count += 1
            
            if report['issues']:
                total_issues.extend(report['issues'])
        
        # Summary statistics
        completion_rate = valid_count / len(parties) * 100
        
        return {
            'success': True,
            'batch_id': batch_id,
            'total_parties': len(parties),
            'valid_parties': valid_count,
            'invalid_parties': len(parties) - valid_count,
            'completion_rate': completion_rate,
            'total_issues': len(total_issues),
            'issues': total_issues[:100],  # First 100 issues
            'detailed_reports': party_reports if len(parties) <= 50 else None,  # Only if small batch
            'recommendation': 'READY' if completion_rate > 95 else 'REVIEW'
        }
