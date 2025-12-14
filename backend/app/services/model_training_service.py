"""Model training service for ML-based credit scoring."""
from typing import Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.models import ModelRegistry, ModelExperiment
from app.db import crud


class ModelTrainingService:
    """Train ML models on labeled data."""

    def __init__(self, db_session: Optional[Session] = None):
        """Initialize the training service.
        
        Args:
            db_session: Optional database session. If not provided, creates a new one.
        """
        self.db = db_session or SessionLocal()

    def train_logistic_regression(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        hyperparams: Dict[str, Any] = None
    ) -> Tuple[LogisticRegression, Dict[str, Any]]:
        """Train logistic regression model.
        
        Args:
            X_train: Training features DataFrame
            y_train: Training labels Series
            hyperparams: Optional dict with hyperparameters {C, penalty, max_iter, etc.}
            
        Returns:
            Tuple of (trained_model, metrics_dict) where metrics_dict contains
            coefficients, intercept, and hyperparameters
        """
        # Default hyperparams
        if hyperparams is None:
            hyperparams = {
                'C': 1.0,
                'penalty': 'l2',
                'max_iter': 1000,
                'solver': 'lbfgs'
            }
        
        # Train model
        model = LogisticRegression(**hyperparams)
        model.fit(X_train, y_train)
        
        # Extract coefficients and metadata
        metrics = {
            'coefficients': model.coef_[0].tolist(),
            'intercept': float(model.intercept_[0]),
            'hyperparams': hyperparams
        }
        
        return model, metrics

    def evaluate_model(
        self,
        model: LogisticRegression,
        X_test: pd.DataFrame,
        y_test: pd.Series
    ) -> Dict[str, Any]:
        """Evaluate model on test set.
        
        Args:
            model: Trained sklearn LogisticRegression model
            X_test: Test features DataFrame
            y_test: Test labels Series
            
        Returns:
            Dict with accuracy, precision, recall, f1, roc_auc, confusion_matrix,
            and classification_report
        """
        # Predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # Compute metrics
        metrics = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision': float(precision_score(y_test, y_pred, zero_division=0)),
            'recall': float(recall_score(y_test, y_pred, zero_division=0)),
            'f1': float(f1_score(y_test, y_pred, zero_division=0)),
            'roc_auc': float(roc_auc_score(y_test, y_pred_proba)),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'classification_report': classification_report(y_test, y_pred, output_dict=True)
        }
        
        return metrics

    def save_to_registry(
        self,
        model: LogisticRegression,
        metrics: Dict[str, Any],
        model_version: str,
        training_data_batch_id: str,
        model_name: str = 'logistic_regression',
        set_active: bool = False
    ) -> Dict[str, Any]:
        """Save trained model to registry.
        
        Args:
            model: Trained sklearn LogisticRegression model
            metrics: Performance metrics dict from evaluate_model
            model_version: Version string (e.g., 'v1', 'v2')
            training_data_batch_id: Batch ID used for training
            model_name: Model type name (default: 'logistic_regression')
            set_active: Whether to set as active model (default: False)
            
        Returns:
            Dict with model_name, model_version, registry_id, is_active, and metrics
        """
        # Serialize model configuration
        algorithm_config = {
            'model_type': 'logistic_regression',
            'coefficients': model.coef_[0].tolist(),
            'intercept': float(model.intercept_[0])
        }
        
        # Create registry entry
        registry = crud.create_model_registry(
            self.db,
            model_name=model_name,
            model_version=model_version,
            algorithm_config=algorithm_config,
            training_data_batch_id=training_data_batch_id,
            performance_metrics=metrics
        )
        
        # Optionally activate
        if set_active:
            crud.update_model_is_active(self.db, registry.id, True)
        
        return {
            'model_name': registry.model_name,
            'model_version': registry.model_version,
            'registry_id': registry.id,
            'is_active': bool(registry.is_active),
            'metrics': metrics
        }

    def compare_with_baseline(
        self,
        new_model: LogisticRegression,
        new_metrics: Dict[str, Any],
        baseline_version: str,
        model_name: str = 'logistic_regression',
        improvement_threshold: float = 0.02
    ) -> Dict[str, Any]:
        """Compare new model with baseline (previous version).
        
        Args:
            new_model: Newly trained sklearn model
            new_metrics: New model metrics dict from evaluate_model
            baseline_version: Version to compare against (e.g., 'v1')
            model_name: Model type (default: 'logistic_regression')
            improvement_threshold: Min AUC improvement threshold (default: 0.02 = 2%)
            
        Returns:
            Dict with comparison results including:
            - success: Whether comparison succeeded
            - baseline_version: Baseline version compared against
            - baseline_auc: Baseline AUC score
            - new_auc: New model AUC score
            - auc_improvement: Difference in AUC
            - improvement_threshold: Threshold used
            - is_better: Whether new model meets threshold
            - recommendation: 'PROMOTE' or 'REVIEW'
        """
        # Get baseline from registry
        baseline = self.db.query(ModelRegistry).filter(
            ModelRegistry.model_name == model_name,
            ModelRegistry.model_version == baseline_version
        ).first()
        
        if not baseline:
            return {
                'success': False,
                'error': f'Baseline {model_name} {baseline_version} not found'
            }
        
        baseline_metrics = baseline.performance_metrics
        
        # Compare AUC
        new_auc = new_metrics.get('roc_auc', 0)
        baseline_auc = baseline_metrics.get('roc_auc', 0)
        auc_improvement = new_auc - baseline_auc
        is_better = auc_improvement >= improvement_threshold
        
        return {
            'success': True,
            'baseline_version': baseline_version,
            'baseline_auc': baseline_auc,
            'new_auc': new_auc,
            'auc_improvement': auc_improvement,
            'improvement_threshold': improvement_threshold,
            'is_better': is_better,
            'recommendation': 'PROMOTE' if is_better else 'REVIEW'
        }
