"""Check database schema with primary keys."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)

print('Columns in model_registry (with details):')
for col in inspector.get_columns('model_registry'):
    print(f'  - {col}')

print()
print('Primary keys:')
pk = inspector.get_pk_constraint('model_registry')
print(f'  {pk}')
