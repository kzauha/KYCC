"""Feature matrix builder for ML training.

Converts raw features + ground truth labels into training-ready format:
- Extract features for all parties in batch
- Normalize/transform features
- Stratified train/test split
- Export as pandas DataFrames or CSV

Decouples feature extraction from model training.
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

from app.db.database import SessionLocal
from app.db import crud
from app.models.models import Party, GroundTruthLabel
from app.services.feature_pipeline_service import FeaturePipelineService


@dataclass
class FeatureMatrixMetadata:
    """Metadata about feature matrix."""
    batch_id: str
    total_parties: int
    features: List[str]
    label_distribution: Dict[int, int]  # {0: count, 1: count}
    transformation_applied: str


class FeatureMatrixBuilder:
    """Build training-ready feature matrices."""

    # Features to extract (must match extractors output)
    FEATURE_NAMES = [
        'kyc_verified',
        'company_age_years',
        'party_type_score',
        'contact_completeness',
        'has_tax_id',
        'transaction_count_6m',
        'avg_transaction_amount',
        'transaction_regularity_score',
        'network_size'
    ]

    def __init__(self, db_session=None, feature_pipeline_service=None):
        """Initialize builder.
        
        Args:
            db_session: Optional database session
            feature_pipeline_service: Optional FeaturePipelineService instance
        """
        self.db = db_session or SessionLocal()
        self.feature_pipeline = feature_pipeline_service or FeaturePipelineService(self.db)
        self.scaler = MinMaxScaler()

    def build_matrix(self, batch_id: str) -> Tuple[pd.DataFrame, pd.Series, FeatureMatrixMetadata]:
        """Build feature matrix with labels for a batch.
        
        Args:
            batch_id: Batch ID (e.g., 'LABELED_TRAIN_001')
            
        Returns:
            (X DataFrame, y Series, metadata)
            
        Raises:
            ValueError: If no parties found in batch
        """
        # Get all parties with ground truth labels in batch
        parties = self.db.query(Party).filter(
            Party.batch_id == batch_id
        ).all()
        
        if not parties:
            raise ValueError(f'No parties found for batch {batch_id}')
        
        X_data = []
        y_data = []
        valid_party_ids = []
        
        for party in parties:
            # Extract features
            try:
                features = self.feature_pipeline.get_features_for_party(party.id)
                feature_dict = {f.feature_name: f.feature_value for f in features}
                
                # Get ground truth label
                label = self.db.query(GroundTruthLabel).filter(
                    GroundTruthLabel.party_id == party.id
                ).first()
                
                if label is None:
                    continue  # Skip parties without labels
                
                # Build row: fill missing features with 0.0 to avoid over-strict filtering
                row = []
                for feature_name in self.FEATURE_NAMES:
                    value = feature_dict.get(feature_name)
                    row.append(0.0 if value is None else value)

                X_data.append(row)
                y_data.append(label.will_default)
                valid_party_ids.append(party.id)
                    
            except Exception as e:
                # Log and skip parties with extraction errors
                print(f"Warning: Could not extract features for party {party.id}: {str(e)}")
                continue
        
        if len(X_data) == 0:
            raise ValueError('No parties with features and labels found')
        
        # Create DataFrames
        X = pd.DataFrame(X_data, columns=self.FEATURE_NAMES)
        y = pd.Series(y_data, name='will_default')
        
        # Metadata
        label_dist = {
            0: int((y == 0).sum()),
            1: int((y == 1).sum())
        }
        
        metadata = FeatureMatrixMetadata(
            batch_id=batch_id,
            total_parties=len(valid_party_ids),
            features=self.FEATURE_NAMES,
            label_distribution=label_dist,
            transformation_applied='none'
        )
        
        return X, y, metadata

    def apply_feature_transformations(self, X: pd.DataFrame) -> pd.DataFrame:
        """Normalize and transform features.
        
        - Min-Max scaling to [0, 1]
        - Simple imputation for any remaining NaNs
        
        Args:
            X: Feature DataFrame
            
        Returns:
            Transformed DataFrame
        """
        X_copy = X.copy()
        
        # Impute NaNs with 0 (assuming 0 is safe default)
        X_copy = X_copy.fillna(0)
        
        # Min-Max scale to [0, 1]
        X_scaled = self.scaler.fit_transform(X_copy)
        X_transformed = pd.DataFrame(
            X_scaled,
            columns=X_copy.columns,
            index=X_copy.index
        )
        
        return X_transformed

    def split_train_test(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Stratified train/test split preserving class balance.
        
        Args:
            X: Feature DataFrame
            y: Label Series
            test_size: Test set fraction (default 0.2)
            random_state: Random seed for reproducibility
            
        Returns:
            (X_train, X_test, y_train, y_test)
        """
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=random_state,
            stratify=y  # Preserve class distribution
        )
        
        return X_train, X_test, y_train, y_test

    def export_matrix(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        filepath: str,
        include_labels: bool = True
    ) -> Dict[str, Any]:
        """Export feature matrix to CSV.
        
        Args:
            X: Feature DataFrame
            y: Label Series (optional)
            filepath: Output CSV path
            include_labels: Include y column (default True)
            
        Returns:
            Export metadata
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if include_labels:
            df = X.copy()
            df['will_default'] = y
        else:
            df = X.copy()
        
        df.to_csv(path, index=False)
        
        return {
            'success': True,
            'filepath': str(path),
            'rows': len(df),
            'columns': len(df.columns)
        }

    def build_and_split(
        self,
        batch_id: str,
        test_size: float = 0.2,
        apply_transformations: bool = False,
        random_state: int = 42
    ) -> Dict[str, Any]:
        """Convenient all-in-one method: build matrix, split, optionally transform.
        
        Args:
            batch_id: Batch to build from
            test_size: Test set fraction
            apply_transformations: Apply normalization
            random_state: Random seed
            
        Returns:
            Dictionary with train/test sets and metadata
        """
        # Build matrix
        X, y, metadata = self.build_matrix(batch_id)
        
        # Transform if requested
        if apply_transformations:
            X = self.apply_feature_transformations(X)
            metadata.transformation_applied = 'minmax_scaling'
        
        # Split
        X_train, X_test, y_train, y_test = self.split_train_test(
            X, y,
            test_size=test_size,
            random_state=random_state
        )
        
        return {
            'X_train': X_train,
            'X_test': X_test,
            'y_train': y_train,
            'y_test': y_test,
            'metadata': {
                'batch_id': metadata.batch_id,
                'total_parties': metadata.total_parties,
                'features': metadata.features,
                'label_distribution': metadata.label_distribution,
                'transformation_applied': metadata.transformation_applied,
                'train_size': len(X_train),
                'test_size': len(X_test),
                'test_ratio': test_size
            }
        }
