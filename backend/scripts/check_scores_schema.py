"""Check credit_scores schema."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)

if 'credit_scores' in inspector.get_table_names():
    print('Columns in credit_scores table:')
    for col in inspector.get_columns('credit_scores'):
        print(f'  - {col["name"]}: {col["type"]}')
else:
    print('credit_scores table not found!')
