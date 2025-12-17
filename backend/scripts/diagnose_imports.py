
import sys
import os
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

print(f"Python: {sys.version}")
print(f"Path: {sys.path[:3]}")

try:
    import pandas
    print("✅ pandas found")
except ImportError as e:
    print(f"❌ pandas MISSING: {e}")

try:
    import sqlalchemy
    print("✅ sqlalchemy found")
except ImportError as e:
    print(f"❌ sqlalchemy MISSING: {e}")

try:
    import numpy
    print("✅ numpy found")
except ImportError as e:
    print(f"❌ numpy MISSING: {e}")

try:
    import joblib
    print("✅ joblib found")
except ImportError as e:
    print(f"❌ joblib MISSING: {e}")

try:
    import sklearn
    from sklearn.linear_model import LogisticRegression
    print("✅ sklearn found")
except ImportError as e:
    print(f"❌ sklearn MISSING: {e}")

try:
    print("Check app imports...")
    from app.services.feature_matrix_builder import FeatureMatrixBuilder
    print("✅ FeatureMatrixBuilder import successful")
except Exception as e:
    print(f"❌ FeatureMatrixBuilder import FAILED: {e}")
    import traceback
    traceback.print_exc()

try:
    from app.services.model_training_service import ModelTrainingService
    print("✅ ModelTrainingService import successful")
except Exception as e:
    print(f"❌ ModelTrainingService import FAILED: {e}")
    import traceback
    traceback.print_exc()
