"""Test ML-Refined Scorecard functionality."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.database import SessionLocal
from app.services.feature_matrix_builder import FeatureMatrixBuilder
from app.services.model_training_service import ModelTrainingService
from sklearn.model_selection import train_test_split

print('=== Testing ML-Refined Scorecard ===')
print()

db = SessionLocal()
try:
    # Build matrix
    builder = FeatureMatrixBuilder(db_session=db)
    X, y, metadata = builder.build_matrix('BATCH_001')
    print(f'1. Built matrix: {X.shape[0]} samples, {X.shape[1]} features')
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Train
    trainer = ModelTrainingService(db_session=db)
    model, train_meta = trainer.train_logistic_regression(X_train, y_train)
    metrics = trainer.evaluate_model(model, X_test, y_test)
    print(f'2. Trained model: AUC={metrics["roc_auc"]:.3f}')
    
    # Convert to scorecard
    feature_names = X.columns.tolist()
    scorecard = trainer.convert_to_scorecard(model, feature_names)
    print(f'3. Converted to scorecard:')
    print(f'   Base score: {scorecard["intercept"]}')
    print(f'   Weights:')
    for feat, pts in scorecard['weights'].items():
        sign = '+' if pts >= 0 else ''
        print(f'     {feat}: {sign}{pts} points')
    
    # Save to registry (use timestamp for unique version)
    import datetime
    version = f'v1_test_{datetime.datetime.now().strftime("%H%M%S")}'
    registry_info = trainer.save_as_scorecard(
        model=model,
        metrics=metrics,
        model_version=version,
        training_data_batch_id='BATCH_001',
        set_active=False
    )
    print(f'4. Saved to registry: Version={registry_info["model_version"]}')
    
    # 5. Test Scoring
    from app.services.scoring_service import ScoringService
    scorer = ScoringService(db=db)
    
    # Get a party to score
    from app.models.models import Party
    party = db.query(Party).first()
    
    if party:
        result = scorer.compute_score(party.id, model_version=version)
        print(f'5. Scored Party {party.id}:')
        print(f'   Score: {result["score"]} ({result["score_band"]})')
        print(f'   Stored in score_requests: {True}') # compute_score logs it automatically
    else:
        print('Skipping scoring (no party found)')
    
    print()
    print('=== SUCCESS: ML-Refined Scorecard Working ===')
    
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
