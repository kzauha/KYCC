from sqlalchemy.orm import Session
from app.services.model_registry_service import ModelRegistryService
from app.models.models import ScoreRequest, GroundTruthLabel, Party
from sqlalchemy import func

class TemporalValidationService:
    """Enforces temporal correctness in the iterative learning pipeline"""

    def __init__(self, db: Session):
        self.db = db

    def validate_scoring_request(self, batch_id: str) -> None:
        """
        Ensures a batch can be legally scored.

        Checks:
        1. Batch has not been scored already (Optional warning/block?) -> strict block for now?
           User prompt says "checks... 1. Batch has not been scored already".
        2. Active model was not trained on this batch
        
        Raises:
            ValueError if validation fails
        """
        registry = ModelRegistryService(self.db)
        
        # Check 1: Already scored?
        # Check if any ScoreRequest exists for parties in this batch?
        # Or faster: Check if any Party in batch has credit_scores?
        # We'll check ScoreRequest for any party in this batch.
        # This implies we JOIN Party.
        
        # Simplified: Check if we have ScoreRequests where party.batch_id == batch_id
        # Assuming ScoreRequest join Party
        count = self.db.query(ScoreRequest).join(Party).filter(
            Party.batch_id == batch_id
        ).count()
        
        if count > 0:
             # Already scored. 
             # Is re-scoring allowed? User prompt implies validation check.
             # "Checks: 1. Batch has not been scored already"
             # I will raise Error or Warning. Prompt says "Raise ValueError".
             raise ValueError(f"Batch {batch_id} has already been scored ({count} records).")
        
        # Check 2: Temporal Leakage
        try:
            active = registry.get_active_version()
            trained_on = active.get("trained_on_batch_id")
            
            if trained_on == batch_id:
                raise ValueError(
                    f"TEMPORAL LEAKAGE DETECTED: Cannot score {batch_id} "
                    f"with model {active['version_id']} trained on the same batch!"
                )
        except ValueError:
            # No active model (bootstrap case?)
            # If no active model, cannot check leakage. ModelRegistry raises error if no active.
            # So this catch handles if ModelRegistry raises "No active model".
            pass

    def validate_training_request(self, batch_id: str) -> None:
        """
        Ensures a batch can be legally used for training.

        Checks:
        1. Batch has been scored already
        2. Labels exist for this batch

        Raises:
            ValueError if validation fails
        """
        # Check 1: Scored?
        # We need to know if the batch generated features and scores.
        # Check if ScoreRequest exists for this batch.
        count_scores = self.db.query(ScoreRequest).join(Party).filter(
            Party.batch_id == batch_id
        ).count()
        
        if count_scores == 0:
            # Exception: Bootstrap mode (No models exist yet)
            from app.models.models import ModelRegistry
            model_count = self.db.query(ModelRegistry).count()
            
            if model_count == 0:
                # Bootstrap allowed
                pass
            else:
                raise ValueError(
                    f"Cannot train on {batch_id}: batch has not been scored yet (0 scores found)"
                )
            
        # Check 2: Labels exist?
        count_labels = self.db.query(GroundTruthLabel).filter(
            GroundTruthLabel.dataset_batch == batch_id
        ).count()
        
        if count_labels == 0:
            raise ValueError(
                f"Cannot train on {batch_id}: labels not ingested yet (0 labels found)"
            )
