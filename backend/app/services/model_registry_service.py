from sqlalchemy.orm import Session
from app.models.models import ScorecardVersion
from app.db.database import SessionLocal
from datetime import datetime
import json
from typing import Dict, List, Any, Optional

class ModelRegistryService:
    """Manages scorecard versions and model lifecycle"""

    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
        self._own_session = db is None

    def __del__(self):
        if self._own_session:
            self.db.close()

    def get_active_version(self) -> dict:
        """
        Returns the currently active scorecard version.

        Returns:
            dict with keys: version_id, coefficients, trained_on_batch_id, created_at

        Raises:
            ValueError if no active version exists
        """
        active = self.db.query(ScorecardVersion).filter(
            ScorecardVersion.is_active == True
        ).first()

        if not active:
            raise ValueError("No active scorecard version found. Please seed the bootstrap model.")

        return {
            "version_id": active.version_id,
            "coefficients": active.coefficients,
            "trained_on_batch_id": active.trained_on_batch_id,
            "created_at": active.created_at
        }

    def load_scorecard(self, version_id: str) -> dict:
        """
        Loads a specific scorecard version's coefficients.

        Args:
            version_id: Version identifier (e.g., "v001")

        Returns:
            dict containing coefficients and metadata
        """
        version = self.db.query(ScorecardVersion).filter(
            ScorecardVersion.version_id == version_id
        ).first()

        if not version:
            raise ValueError(f"Scorecard version {version_id} not found.")

        return {
            "version_id": version.version_id,
            "coefficients": version.coefficients,
            "trained_on_batch_id": version.trained_on_batch_id,
            "model_metrics": version.model_metrics,
            "is_active": version.is_active
        }

    def register_new_version(
        self,
        trained_on_batch_id: str,
        model: Any,  # sklearn LogisticRegression
        metrics: dict,
        auto_activate: bool = False
    ) -> str:
        """
        Registers a newly trained model as a new version.

        Args:
            trained_on_batch_id: Batch used for training (e.g., "BATCH_001")
            model: Trained sklearn model
            metrics: Dict with AUC, F1, precision, recall
            auto_activate: If True, sets this version as active

        Returns:
            New version_id (e.g., "v003")
        """
        # 1. Generate new version ID
        last_version = self.db.query(ScorecardVersion).order_by(
            ScorecardVersion.created_at.desc()
        ).first()
        
        if last_version:
             # Simple increment logic: 'v001' -> 'v002'
             try:
                 last_num = int(last_version.version_id.replace("v", ""))
                 new_id = f"v{last_num + 1:03d}"
                 parent_id = last_version.version_id
             except ValueError:
                 # Fallback for non-standard IDs
                 new_id = f"v{int(datetime.utcnow().timestamp())}"
                 parent_id = last_version.version_id
        else:
             new_id = "v001"
             parent_id = None

        # 3. Convert sklearn model to scorecard coefficients
        # Coefficients: {feature_name: weight}
        # Intercept is usually added as 'intercept'
        if hasattr(model, "coef_"):
            # Assuming feature_names_in_ matches coef_ columns
            # We need the feature names from the model inputs.
            # Usually passed in metadata or we extract from model if available.
            coefficients = {"intercept": float(model.intercept_[0])}
            if hasattr(model, "feature_names_in_"):
                for name, coef in zip(model.feature_names_in_, model.coef_[0]):
                    coefficients[name] = float(coef)
            else:
                # Fallback if names unavailable (store raw list?)
                # This service assumes we have access to features. 
                # Ideally 'model' object is comprehensive or we pass feature_names separately.
                # For now, store generic 'feature_i'
                for i, coef in enumerate(model.coef_[0]):
                    coefficients[f"feature_{i}"] = float(coef)
        else:
            # Fallback/Dummy logic for non-sklearn inputs
            coefficients = {"intercept": 0.0}

        # 4. Save to scorecard_version table
        new_version = ScorecardVersion(
            version_id=new_id,
            trained_on_batch_id=trained_on_batch_id,
            is_active=False,  # managed by auto_activate logic below
            parent_version_id=parent_id,
            model_metrics=metrics,
            coefficients=coefficients,
            created_at=datetime.utcnow()
        )
        self.db.add(new_version)
        self.db.commit()

        # 5. Optionally activate
        if auto_activate:
            self.activate_version(new_id)
            
        return new_id

    def activate_version(self, version_id: str) -> None:
        """
        Sets a version as active (deactivates all others).

        Args:
            version_id: Version to activate
        """
        # Deactivate all
        self.db.query(ScorecardVersion).update({ScorecardVersion.is_active: False})
        
        # Activate target
        target = self.db.query(ScorecardVersion).filter(
            ScorecardVersion.version_id == version_id
        ).first()
        
        if not target:
            self.db.rollback()
            raise ValueError(f"Version {version_id} not found.")
            
        target.is_active = True
        self.db.commit()

    def get_version_lineage(self, version_id: str) -> List[str]:
        """
        Returns the ancestry chain of a version.

        Args:
            version_id: Starting version

        Returns:
            List of version_ids from oldest ancestor to current
        """
        history = []
        current_id = version_id
        
        while current_id:
            version = self.db.query(ScorecardVersion).filter(
                ScorecardVersion.version_id == current_id
            ).first()
            if not version:
                break
            
            history.insert(0, version.version_id)
            current_id = version.parent_version_id
            
        return history

    def compare_versions(self, version_a: str, version_b: str) -> dict:
        """
        Compares metrics between two versions.

        Returns:
            Dict with metric deltas (e.g., {"auc_delta": 0.05, "better": "v002"})
        """
        v1 = self.load_scorecard(version_a)
        v2 = self.load_scorecard(version_b)
        
        m1 = v1.get("model_metrics", {}) or {}
        m2 = v2.get("model_metrics", {}) or {}
        
        # Assume AUC is main metric
        auc1 = m1.get("roc_auc", 0)
        auc2 = m2.get("roc_auc", 0)
        
        delta = auc2 - auc1
        
        return {
            "auc_delta": float(delta),
            "better": version_b if delta > 0 else version_a,
            "version_a_auc": auc1,
            "version_b_auc": auc2
        }
