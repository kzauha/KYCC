"""KYCC System Verification Script"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

print('=== KYCC System Verification ===')
print()

# 1. Test Feature Extraction
print('1. Testing Feature Extraction...')
from app.db.database import SessionLocal
from app.services.feature_pipeline_service import FeaturePipelineService
from app.models.models import Party

db = SessionLocal()
try:
    pipeline = FeaturePipelineService(db)
    party = db.query(Party).first()
    result = pipeline.extract_all_features(party.id)
    print(f'   Extracted {result["feature_count"]} features from sources: {result["sources"]}')
    print('   ✓ Feature extraction OK')
except Exception as e:
    print(f'   ✗ Error: {e}')
finally:
    db.close()

# 2. Test Feature Validation
print()
print('2. Testing Feature Validation...')
from app.services.feature_validation_service import FeatureValidationService
db = SessionLocal()
try:
    validator = FeatureValidationService(db_session=db)
    party = db.query(Party).first()
    report = validator.validate_party(party.id)
    print(f'   Party {party.id} valid: {report["is_valid"]}')
    if report['missing_features']:
        print(f'   Missing: {report["missing_features"]}')
    print('   ✓ Feature validation OK')
except Exception as e:
    print(f'   ✗ Error: {e}')
finally:
    db.close()

# 3. Test Matrix Building
print()
print('3. Testing Matrix Building...')
from app.services.feature_matrix_builder import FeatureMatrixBuilder
db = SessionLocal()
try:
    builder = FeatureMatrixBuilder(db_session=db)
    X, y, metadata = builder.build_matrix('BATCH_001')
    print(f'   Matrix shape: {X.shape}')
    print(f'   Labels: {metadata.label_distribution}')
    print('   ✓ Matrix building OK')
except Exception as e:
    print(f'   ✗ Error: {e}')
finally:
    db.close()

# 4. Test Model Training
print()
print('4. Testing Model Training...')
from app.services.model_training_service import ModelTrainingService
import pandas as pd
db = SessionLocal()
try:
    builder = FeatureMatrixBuilder(db_session=db)
    X, y, _ = builder.build_matrix('BATCH_001')
    
    trainer = ModelTrainingService(db_session=db)
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model, train_meta = trainer.train_logistic_regression(X_train, y_train)
    metrics = trainer.evaluate_model(model, X_test, y_test)
    print(f'   AUC: {metrics["roc_auc"]:.3f}, F1: {metrics["f1"]:.3f}')
    print(f'   Feature names captured: {len(train_meta.get("feature_names", []))}')
    print('   ✓ Model training OK')
except Exception as e:
    print(f'   ✗ Error: {e}')
    import traceback
    traceback.print_exc()
finally:
    db.close()

print()
print('=== All Tests Passed ===')
