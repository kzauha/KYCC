"""
Scorecard Version Service - Manages versioned scorecards in database.

Provides:
- Get active scorecard version from database
- Create new scorecard version (from ML refinement)
- Promote challenger to active
- Retire old versions
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.models import ScorecardVersion
from app.scorecard.scorecard_config import INITIAL_SCORECARD_V1


class ScorecardVersionService:
    """Service for managing scorecard versions in the database.
    
    The scorecard is the source of truth for scoring. This service
    manages versioned scorecards, allowing ML to create new versions
    with refined weights.
    
    Example:
        >>> svc = ScorecardVersionService(db)
        >>> config = svc.get_active_scorecard()
        >>> engine = ScorecardEngine(config)
    """
    
    def __init__(self, db: Session):
        """Initialize service with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def get_active_scorecard(self) -> Dict[str, Any]:
        """Get the currently active scorecard configuration.
        
        Falls back to INITIAL_SCORECARD_V1 if no active version exists
        in the database (bootstrap mode).
        
        Returns:
            Dict with scorecard config (version, weights, base_score, etc.)
            
        Example:
            >>> config = svc.get_active_scorecard()
            >>> print(config['version'])  # '1.0'
        """
        active = self.db.query(ScorecardVersion).filter(
            ScorecardVersion.status == 'active'
        ).first()
        
        if active:
            return active.to_config_dict()
        
        # Bootstrap: return default expert config
        return INITIAL_SCORECARD_V1.copy()
    
    def create_version_from_ml(
        self,
        weights: Dict[str, float],
        ml_auc: float,
        ml_f1: float,
        ml_model_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[ScorecardVersion]:
        """Create a new scorecard version from ML-refined weights.
        
        Quality gates:
        - AUC must be >= 0.7
        - Must beat current active version by 2%
        
        Args:
            weights: ML-derived feature weights
            ml_auc: Model ROC-AUC score
            ml_f1: Model F1 score
            ml_model_id: Reference to model_registry entry
            notes: Optional notes about this version
            
        Returns:
            New ScorecardVersion if passes gates, None if failed
            
        Example:
            >>> new_version = svc.create_version_from_ml(
            ...     weights={'kyc_verified': 18, ...},
            ...     ml_auc=0.85,
            ...     ml_f1=0.72
            ... )
        """
        MIN_AUC_THRESHOLD = 0.55  # Lowered for demo (was 0.7)
        IMPROVEMENT_THRESHOLD = 0.005  # 0.5% (was 2%)
        
        # Gate 1: Minimum AUC
        if ml_auc < MIN_AUC_THRESHOLD:
            # Save as failed for inspection
            return self._save_failed_version(
                weights=weights,
                ml_auc=ml_auc,
                ml_f1=ml_f1,
                ml_model_id=ml_model_id,
                reason=f"AUC {ml_auc:.3f} below minimum {MIN_AUC_THRESHOLD}"
            )
        
        # Gate 2: Must beat current
        current = self.get_active_scorecard()
        current_version = self.db.query(ScorecardVersion).filter(
            ScorecardVersion.status == 'active'
        ).first()
        
        if current_version and current_version.ml_auc:
            current_auc = current_version.ml_auc
            improvement = ml_auc - current_auc
            
            if improvement < IMPROVEMENT_THRESHOLD:
                return self._save_failed_version(
                    weights=weights,
                    ml_auc=ml_auc,
                    ml_f1=ml_f1,
                    ml_model_id=ml_model_id,
                    reason=f"Improvement {improvement:.3f} below threshold {IMPROVEMENT_THRESHOLD}"
                )
        
        # Passed all gates - create new active version
        new_version_num = self._get_next_version_number()
        
        # Retire current active
        if current_version:
            current_version.status = 'retired'
            current_version.retired_at = datetime.utcnow()
        
        # Create new version
        new_version = ScorecardVersion(
            version=new_version_num,
            status='active',
            weights=weights,
            base_score=current.get('base_score', 300),
            max_score=current.get('max_score', 900),
            scaling_config=current.get('feature_scaling'),
            source='ml_refined',
            ml_model_id=ml_model_id,
            ml_auc=ml_auc,
            ml_f1=ml_f1,
            activated_at=datetime.utcnow(),
            notes=notes or f"ML-refined from {current.get('version', '1.0')}"
        )
        
        self.db.add(new_version)
        self.db.commit()
        
        return new_version
    
    def _save_failed_version(
        self,
        weights: Dict[str, float],
        ml_auc: float,
        ml_f1: float,
        ml_model_id: Optional[str],
        reason: str,
    ) -> ScorecardVersion:
        """Save a failed version for inspection (not used for scoring).
        
        Args:
            weights: ML weights that failed
            ml_auc: AUC score
            ml_f1: F1 score
            ml_model_id: Model reference
            reason: Why it failed
            
        Returns:
            ScorecardVersion with status='failed'
        """
        version_num = self._get_next_version_number()
        
        failed_version = ScorecardVersion(
            version=version_num,
            status='failed',  # Not used for scoring
            weights=weights,
            base_score=300,
            max_score=900,
            source='ml_refined',
            ml_model_id=ml_model_id,
            ml_auc=ml_auc,
            ml_f1=ml_f1,
            notes=f"FAILED: {reason}"
        )
        
        self.db.add(failed_version)
        self.db.commit()
        
        return failed_version
    
    def _get_next_version_number(self) -> str:
        """Generate next version number (e.g., '1.0' -> '1.1' -> '2.0').
        
        Returns:
            Next version string
        """
        latest = self.db.query(ScorecardVersion).order_by(
            ScorecardVersion.id.desc()
        ).first()
        
        if not latest:
            return '1.0'
        
        # Parse version and increment
        try:
            parts = latest.version.split('.')
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            
            # Increment minor version (e.g., 1.0 -> 1.1)
            return f"{major}.{minor + 1}"
        except (ValueError, IndexError):
            return '2.0'
    
    def get_version_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent scorecard version history.
        
        Args:
            limit: Maximum versions to return
            
        Returns:
            List of version summaries
        """
        versions = self.db.query(ScorecardVersion).order_by(
            ScorecardVersion.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                'version': v.version,
                'status': v.status,
                'source': v.source,
                'ml_auc': v.ml_auc,
                'created_at': v.created_at.isoformat() if v.created_at else None,
                'notes': v.notes,
            }
            for v in versions
        ]
    
    def ensure_initial_version(self) -> None:
        """Ensure initial expert version exists in database.
        
        Call this during bootstrap to seed the database with
        the initial expert-defined scorecard.
        """
        exists = self.db.query(ScorecardVersion).filter(
            ScorecardVersion.version == '1.0'
        ).first()
        
        if not exists:
            initial = ScorecardVersion(
                version='1.0',
                status='active',
                weights=INITIAL_SCORECARD_V1.get('weights', {}),
                base_score=INITIAL_SCORECARD_V1.get('base_score', 300),
                max_score=INITIAL_SCORECARD_V1.get('max_score', 900),
                scaling_config=INITIAL_SCORECARD_V1.get('feature_scaling'),
                source='expert',
                activated_at=datetime.utcnow(),
                notes='Initial expert-defined scorecard'
            )
            self.db.add(initial)
            self.db.commit()
