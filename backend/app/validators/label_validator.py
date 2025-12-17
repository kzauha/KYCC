"""
Label Validator - Validates ground truth labels before ingestion.

Ensures labels meet quality requirements:
- Completeness (no nulls in required fields)
- Format (binary values only)
- Date validity (not future, not too old)
- Class distribution (minimum samples per class)
- Duplicate detection
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import pandas as pd
from sqlalchemy.orm import Session

from app.models.models import GroundTruthLabel, Party


@dataclass
class ValidationResult:
    """Result of a validation check."""
    passed: bool
    error_count: int = 0
    warning_count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class LabelValidator:
    """
    Validates ground truth labels for quality and consistency.
    
    Run validations before label ingestion to ensure data quality.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_label_completeness(self, labels_df: pd.DataFrame) -> ValidationResult:
        """Check for null values in required columns."""
        required_cols = ['party_id', 'will_default']
        errors = []
        
        for col in required_cols:
            if col not in labels_df.columns:
                errors.append(f"Missing required column: {col}")
            elif labels_df[col].isnull().any():
                null_count = labels_df[col].isnull().sum()
                errors.append(f"Column '{col}' has {null_count} null values")
        
        return ValidationResult(
            passed=len(errors) == 0,
            error_count=len(errors),
            errors=errors,
            details={'checked_columns': required_cols}
        )
    
    def validate_label_format(self, labels_df: pd.DataFrame) -> ValidationResult:
        """Ensure will_default contains only binary values (0 or 1)."""
        errors = []
        
        if 'will_default' not in labels_df.columns:
            errors.append("Column 'will_default' not found")
            return ValidationResult(passed=False, error_count=1, errors=errors)
        
        unique_values = set(labels_df['will_default'].unique())
        valid_values = {0, 1}
        invalid_values = unique_values - valid_values
        
        if invalid_values:
            errors.append(f"Invalid values in 'will_default': {invalid_values}. Expected only 0 or 1.")
        
        return ValidationResult(
            passed=len(errors) == 0,
            error_count=len(errors),
            errors=errors,
            details={'unique_values': list(unique_values)}
        )
    
    def validate_label_dates(
        self, 
        labels_df: pd.DataFrame,
        max_age_years: int = 5
    ) -> ValidationResult:
        """Check label dates are not in future and not older than max_age_years."""
        errors = []
        warnings = []
        
        if 'label_date' not in labels_df.columns:
            # Optional column - just warn
            warnings.append("No 'label_date' column found. Date validation skipped.")
            return ValidationResult(passed=True, warning_count=1, warnings=warnings)
        
        now = datetime.utcnow()
        max_age = now - timedelta(days=365 * max_age_years)
        
        future_count = (labels_df['label_date'] > now).sum()
        if future_count > 0:
            errors.append(f"{future_count} labels have future dates")
        
        old_count = (labels_df['label_date'] < max_age).sum()
        if old_count > 0:
            warnings.append(f"{old_count} labels are older than {max_age_years} years")
        
        return ValidationResult(
            passed=len(errors) == 0,
            error_count=len(errors),
            warning_count=len(warnings),
            errors=errors,
            warnings=warnings
        )
    
    def validate_class_distribution(
        self,
        labels_df: pd.DataFrame,
        min_positive_samples: int = 50,
        min_minority_ratio: float = 0.01
    ) -> ValidationResult:
        """Ensure sufficient positive samples and minimum class ratio."""
        errors = []
        warnings = []
        
        if 'will_default' not in labels_df.columns:
            errors.append("Column 'will_default' not found")
            return ValidationResult(passed=False, error_count=1, errors=errors)
        
        total = len(labels_df)
        positive_count = (labels_df['will_default'] == 1).sum()
        negative_count = total - positive_count
        
        minority_count = min(positive_count, negative_count)
        minority_ratio = minority_count / total if total > 0 else 0
        
        # Check minimum positive samples
        if positive_count < min_positive_samples:
            # Warning only (not blocking) for small batches
            warnings.append(
                f"Only {positive_count} positive samples (defaults). "
                f"Recommended minimum: {min_positive_samples}"
            )
        
        # Check minimum ratio
        if minority_ratio < min_minority_ratio:
            errors.append(
                f"Minority class ratio ({minority_ratio:.2%}) is below minimum "
                f"({min_minority_ratio:.2%}). Cannot train meaningful model."
            )
        
        return ValidationResult(
            passed=len(errors) == 0,
            error_count=len(errors),
            warning_count=len(warnings),
            errors=errors,
            warnings=warnings,
            details={
                'total_samples': total,
                'positive_count': int(positive_count),
                'negative_count': int(negative_count),
                'minority_ratio': minority_ratio
            }
        )
    
    def check_duplicate_labels(self, labels_df: pd.DataFrame) -> ValidationResult:
        """Flag if same party_id has multiple labels."""
        warnings = []
        
        if 'party_id' not in labels_df.columns:
            return ValidationResult(
                passed=True,
                warnings=["No 'party_id' column for dedup check"]
            )
        
        duplicates = labels_df[labels_df.duplicated(subset=['party_id'], keep=False)]
        if len(duplicates) > 0:
            dup_party_ids = duplicates['party_id'].unique()
            warnings.append(
                f"Found {len(dup_party_ids)} parties with duplicate labels: "
                f"{list(dup_party_ids)[:10]}{'...' if len(dup_party_ids) > 10 else ''}"
            )
        
        return ValidationResult(
            passed=True,  # Duplicates are warnings, not errors
            warning_count=len(warnings),
            warnings=warnings,
            details={'duplicate_count': len(duplicates)}
        )
    
    def validate_batch(self, labels_df: pd.DataFrame) -> Dict[str, ValidationResult]:
        """Run all validations and return combined report."""
        report = {
            'completeness': self.validate_label_completeness(labels_df),
            'format': self.validate_label_format(labels_df),
            'dates': self.validate_label_dates(labels_df),
            'class_distribution': self.validate_class_distribution(labels_df),
            'duplicates': self.check_duplicate_labels(labels_df),
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
                'checks_run': list(report.keys()),
                'checks_passed': sum(1 for r in report.values() if r.passed)
            }
        )
        
        return report
