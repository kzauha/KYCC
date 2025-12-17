"""Check database schema."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)

# Check if table exists
tables = inspector.get_table_names()
print('Tables in database:')
for t in tables:
    print(f'  - {t}')

if 'model_registry' in tables:
    print()
    print('Columns in model_registry:')
    for col in inspector.get_columns('model_registry'):
        print(f'  - {col["name"]}: {col["type"]}')
else:
    print()
    print('model_registry table does not exist!')
    print('Run migrations or create tables with Base.metadata.create_all()')
