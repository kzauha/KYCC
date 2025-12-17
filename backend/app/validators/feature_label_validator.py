"""
Feature-Label Validator - Ensures feature-label alignment.

Validates:
- Party ID alignment (all labels have features)
- Temporal consistency (features computed before label date)
- Feature completeness (all parties have required features)
- Data leakage detection (features not computed after labels)
"""

from typing import Dict, Any, List, Set
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd
from sqlalchemy.orm import Session

from app.models.models import Feature, GroundTruthLabel, Party
from app.validators.label_validator import ValidationResult


class FeatureLabelValidator:
    """
    Validates alignment between features and labels.
    
    Ensures:
    1. Every labeled party has computed features
    2. Features were computed before label date (no leakage)
    3. Required features exist for all parties
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_party_id_alignment(
        self,
        batch_id: str,
    ) -> ValidationResult:
        """Ensure every label has corresponding features."""
        errors = []
        warnings = []
        
        # Get party IDs with labels
        label_party_ids = set(
            r[0] for r in self.db.query(GroundTruthLabel.party_id)
            .join(Party)
            .filter(Party.batch_id == batch_id)
            .all()
        )
        
        # Get party IDs with features
        feature_party_ids = set(
            r[0] for r in self.db.query(Feature.party_id)
            .distinct()
            .join(Party)
            .filter(Party.batch_id == batch_id)
            .all()
        )
        
        # Find misalignment
        labels_without_features = label_party_ids - feature_party_ids
        features_without_labels = feature_party_ids - label_party_ids
        
        if labels_without_features:
            errors.append(
                f"{len(labels_without_features)} labeled parties missing features: "
                f"{list(labels_without_features)[:5]}..."
            )
        
        if features_without_labels:
            warnings.append(
                f"{len(features_without_labels)} parties have features but no labels"
            )
        
        return ValidationResult(
            passed=len(errors) == 0,
            error_count=len(errors),
            warning_count=len(warnings),
            errors=errors,
            warnings=warnings,
            details={
                'labeled_parties': len(label_party_ids),
                'parties_with_features': len(feature_party_ids),
                'missing_features': len(labels_without_features),
                'missing_labels': len(features_without_labels),
            }
        )
    
    def validate_temporal_consistency(
        self,
        batch_id: str,
    ) -> ValidationResult:
        """Verify features were computed before label date (no future leakage)."""
        warnings = []
        
        # Query features with their computation timestamps and label dates
        results = self.db.query(
            Feature.party_id,
            Feature.feature_name,
            Feature.computation_timestamp,
            GroundTruthLabel.created_at.label('label_date')
        ).join(
            GroundTruthLabel, Feature.party_id == GroundTruthLabel.party_id
        ).join(
            Party, Feature.party_id == Party.id
        ).filter(
            Party.batch_id == batch_id
        ).all()
        
        leakage_count = 0
        leakage_examples = []
        
        for r in results:
            if r.computation_timestamp and r.label_date:
                if r.computation_timestamp > r.label_date:
                    leakage_count += 1
                    if len(leakage_examples) < 3:
                        leakage_examples.append({
                            'party_id': r.party_id,
                            'feature': r.feature_name,
                            'computed': str(r.computation_timestamp),
                            'labeled': str(r.label_date)
                        })
        
        if leakage_count > 0:
            warnings.append(
                f"{leakage_count} features computed after label date (potential leakage)"
            )
        
        return ValidationResult(
            passed=True,  # Temporal issues are warnings, not errors
            warning_count=len(warnings),
            warnings=warnings,
            details={
                'total_checked': len(results),
                'potential_leakage': leakage_count,
                'examples': leakage_examples
            }
        )
    
    def validate_feature_completeness(
        self,
        batch_id: str,
        required_features: List[str] = None,
    ) -> ValidationResult:
        """Check if all parties have required features."""
        errors = []
        warnings = []
        
        # Default required features
        if required_features is None:
            required_features = [
                'kyc_verified',
                'transaction_count_6m',
                'company_age_years',
            ]
        
        # Get all parties in batch
        parties = self.db.query(Party.id).filter(Party.batch_id == batch_id).all()
        party_ids = [p[0] for p in parties]
        
        if not party_ids:
            errors.append(f"No parties found for batch {batch_id}")
            return ValidationResult(passed=False, error_count=1, errors=errors)
        
        # Check each required feature
        missing_summary = {}
        for feature_name in required_features:
            parties_with_feature = set(
                r[0] for r in self.db.query(Feature.party_id)
                .filter(
                    Feature.feature_name == feature_name,
                    Feature.party_id.in_(party_ids),
                    Feature.valid_to == None  # Current features only
                ).all()
            )
            
            missing_count = len(party_ids) - len(parties_with_feature)
            if missing_count > 0:
                missing_summary[feature_name] = missing_count
                if missing_count > len(party_ids) * 0.5:  # >50% missing
                    errors.append(
                        f"Feature '{feature_name}' missing for {missing_count}/{len(party_ids)} parties"
                    )
                else:
                    warnings.append(
                        f"Feature '{feature_name}' missing for {missing_count} parties"
                    )
        
        return ValidationResult(
            passed=len(errors) == 0,
            error_count=len(errors),
            warning_count=len(warnings),
            errors=errors,
            warnings=warnings,
            details={
                'total_parties': len(party_ids),
                'required_features': required_features,
                'missing_summary': missing_summary
            }
        )
    
    def validate_alignment(self, batch_id: str) -> Dict[str, ValidationResult]:
        """Run all feature-label alignment validations."""
        report = {
            'party_alignment': self.validate_party_id_alignment(batch_id),
            'temporal_consistency': self.validate_temporal_consistency(batch_id),
            'feature_completeness': self.validate_feature_completeness(batch_id),
        }
        
        # Summary
        all_passed = all(r.passed for r in report.values())
        total_errors = sum(r.error_count for r in report.values())
        total_warnings = sum(r.warning_count for r in report.values())
        
        report['summary'] = ValidationResult(
            passed=all_passed,
            error_count=total_errors,
            warning_count=total_warnings,
            details={
                'batch_id': batch_id,
                'checks_run': len(report) - 1,  # Exclude summary
                'all_passed': all_passed
            }
        )
        
        return report
