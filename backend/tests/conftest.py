import os
import sys
from pathlib import Path

# Ensure project root is on sys.path for `import app`
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force SQLite for tests to avoid Postgres schema drift
test_db_path = ROOT / "test_run.db"
if test_db_path.exists():
    test_db_path.unlink()

os.environ.setdefault("DATABASE_URL", f"sqlite:///{test_db_path}")
os.environ.setdefault("AUTO_CREATE_TABLES", "1")

# Create tables if needed
from app.db.database import engine, Base
import app.models.models  # noqa: F401 ensures models are registered

Base.metadata.create_all(bind=engine)
