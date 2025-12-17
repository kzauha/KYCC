"""Package init for scorecard module."""

from app.scorecard.scorecard_config import (
    INITIAL_SCORECARD_V1,
    get_scorecard_config,
)
from app.scorecard.scorecard_engine import ScorecardEngine

# Import version service from services
# Note: Circular import protection - import at function level if needed
def get_version_service(db):
    """Get ScorecardVersionService instance.
    
    Args:
        db: SQLAlchemy database session
        
    Returns:
        ScorecardVersionService instance
    """
    from app.services.scorecard_version_service import ScorecardVersionService
    return ScorecardVersionService(db)

__all__ = [
    'INITIAL_SCORECARD_V1',
    'get_scorecard_config', 
    'ScorecardEngine',
    'get_version_service',
]
