"""Model training service for ML-based credit scoring."""
from typing import Tuple, Dict, Any, Optional
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    average_precision_score
)
import joblib
import io
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
                'solver': 'lbfgs',
                'class_weight': 'balanced'  # FIX #8: Handle Class Imbalance
            }
        
        # Log class distribution
        pos_count = y_train.sum()
        total_count = len(y_train)
        pos_ratio = pos_count / total_count if total_count > 0 else 0
        print(f"Class Distribution: {pos_count}/{total_count} positive ({pos_ratio:.2%})")
        
        if pos_ratio < 0.05 or pos_ratio > 0.95:
             print("WARNING: Severe class imbalance detected!")
        
        # Train model
        model = LogisticRegression(**hyperparams)
        model.fit(X_train, y_train)
        
        # Extract coefficients and metadata
        metrics = {
            'coefficients': model.coef_[0].tolist(),
            'intercept': float(model.intercept_[0]),
            'hyperparams': hyperparams,
            'feature_names': X_train.columns.tolist()
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
            'pr_auc': float(average_precision_score(y_test, y_pred_proba)),  # FIX #8: precise metric for imbalance
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
        set_active: bool = False,
        scaler: Any = None
    ) -> Dict[str, Any]:
        """Save trained model to registry.
        
        Args:
            model: Trained sklearn LogisticRegression model
            metrics: Performance metrics dict from evaluate_model
            model_version: Version string (e.g., 'v1', 'v2')
            training_data_batch_id: Batch ID used for training
            model_name: Model type name (default: 'logistic_regression')
            set_active: Whether to set as active model (default: False)
            scaler: Optional fitted scaler object to persist
            
        Returns:
            Dict with model_version, registry_id, is_active, and metrics
        """
        # Get feature names from model
        feature_names = getattr(model, "feature_names_in_", [])
        if hasattr(feature_names, "tolist"):
             feature_names = feature_names.tolist()
        
        # Build model config (stores weights/coefficients)
        model_config = {
            'coefficients': model.coef_[0].tolist(),
            'hyperparams': {'max_iter': 200}
        }
        
        intercept_val = float(model.intercept_[0])
        
        # Serialize scaler if provided
        scaler_binary = None
        if scaler:
            buffer = io.BytesIO()
            joblib.dump(scaler, buffer)
            scaler_binary = buffer.getvalue()
        
        # Create registry entry
        registry = crud.create_model_registry(
            self.db,
            model_version=model_version,
            model_type='ml_model',  # Raw ML model (not converted to scorecard)
            model_config=model_config,
            feature_list=feature_names,
            intercept=intercept_val,
            performance_metrics=metrics,
            description=f'Logistic regression trained on {training_data_batch_id}',
            scaler_binary=scaler_binary
        )
        
        # Optionally activate
        if set_active:
            crud.update_model_is_active(self.db, registry.model_version, True)
        
        return {
            'model_version': registry.model_version,
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

    def convert_to_scorecard(
        self,
        model: LogisticRegression,
        feature_names: list,
        total_points: int = 100
    ) -> Dict[str, Any]:
        """
        Convert ML model coefficients to scorecard points.
        
        This transforms the learned logistic regression weights into
        an interpretable scorecard format where each feature contributes
        a certain number of "points" to the final score.
        
        Args:
            model: Trained LogisticRegression model
            feature_names: List of feature names in order
            total_points: Total points to distribute (default 100)
            
        Returns:
            Scorecard config dict with format:
            {
                "model_type": "scorecard",
                "weights": {"feature_name": points, ...},
                "intercept": base_points,
                "features": ["feature1", "feature2", ...]
            }
        """
        coefficients = model.coef_[0]
        intercept = float(model.intercept_[0])
        
        # Calculate total absolute weight for normalization
        abs_sum = sum(abs(c) for c in coefficients)
        
        if abs_sum == 0:
            # Edge case: all coefficients are zero
            weights = {name: 0 for name in feature_names}
            base_score = 50  # Default neutral base
        else:
            # Scale coefficients to points, preserving sign
            # Positive coefficients = positive points (increase score)
            # Negative coefficients = negative points (decrease score)
            weights = {}
            for name, coef in zip(feature_names, coefficients):
                # Scale to points based on relative importance
                # FIX #4: Preserve Sign - Positive coef -> Positive points, Negative coef -> Negative points
                # Example: transaction_count weight: +15 (increase score), recent_default weight: -20 (decrease score)
                points = int((coef / abs_sum) * total_points)
                weights[name] = points
            
            # Base score from intercept
            # Positive intercept means higher base score
            base_score = int(50 + (intercept / abs_sum) * 25)  # Range roughly 25-75
            base_score = max(0, min(100, base_score))  # Clamp to 0-100
            
            # Validation: Ensure we have a mix if model is non-trivial
            if len(weights) > 3 and abs_sum > 0.01:
                 has_pos = any(w > 0 for w in weights.values())
                 has_neg = any(w < 0 for w in weights.values())
                 # Just log if suspicious, don't crash as some models might be all positive
                 if not (has_pos and has_neg):
                      print(f"Notice: Scorecard weights are all same sign. Pos: {has_pos}, Neg: {has_neg}")
        
        return {
            "model_type": "scorecard",
            "weights": weights,
            "intercept": base_score,
            "features": feature_names,
            "conversion_method": "ml_coefficient_scaling",
            "total_points_scale": total_points
        }

    def save_as_scorecard(
        self,
        model: LogisticRegression,
        metrics: Dict[str, Any],
        model_version: str,
        training_data_batch_id: str,
        model_name: str = "ml_refined_scorecard",
        set_active: bool = False
    ) -> Dict[str, Any]:
        """
        Convert ML model to scorecard format and save to registry.
        
        This is the recommended way to deploy ML models for credit scoring,
        as the result is:
        - Interpretable (human-readable points per feature)
        - Explainable (can show "you lost 10 points for low transaction count")
        - Compatible with existing scorecard infrastructure
        
        Args:
            model: Trained LogisticRegression model
            metrics: Evaluation metrics from evaluate_model()
            model_version: Version string (e.g., "v1.0")
            training_data_batch_id: Batch ID used for training
            model_name: Name for the scorecard (default: "ml_refined_scorecard")
            set_active: Whether to set as active model
            
        Returns:
            Dict with registry info and scorecard weights
        """
        # Get feature names from model
        feature_names = getattr(model, "feature_names_in_", [])
        if hasattr(feature_names, "tolist"):
            feature_names = feature_names.tolist()
        
        if not feature_names:
            raise ValueError("Model does not have feature_names_in_. Train with DataFrame input.")
        
        # Convert to scorecard format
        scorecard_config = self.convert_to_scorecard(model, feature_names)
        
        # Create registry entry
        registry = crud.create_model_registry(
            self.db,
            model_version=model_version,
            model_type='scorecard',  # ML-refined scorecard
            model_config=scorecard_config,
            feature_list=feature_names,
            intercept=float(scorecard_config['intercept']),
            performance_metrics=metrics,
            description=f'ML-refined scorecard ({model_name}) trained on {training_data_batch_id}'
        )
        
        # Optionally activate
        if set_active:
            crud.update_model_is_active(self.db, registry.model_version, True)
        
        return {
            'model_version': registry.model_version,
            'is_active': bool(registry.is_active),
            'scorecard_weights': scorecard_config['weights'],
            'base_score': scorecard_config['intercept'],
            'features': scorecard_config['features'],
            'metrics': metrics
        }
