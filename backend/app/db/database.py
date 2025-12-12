from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import sys
import time
import subprocess
import shutil
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database connection string
# Format: postgresql://username:password@host:port/database_name
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://localhost/kycc_db"  # Default if .env not found
)

# Create the database engine (the connection manager)
# If psycopg2 (Postgres driver) is not available in the environment,
# fall back to a local SQLite file so quick scripts/tests can run.


def _test_engine_connection(engine, timeout: float = 2.0) -> bool:
    """Try a lightweight DB operation to confirm connectivity.

    Returns True on success, False on failure.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _attempt_start_docker_container(container_name: str) -> bool:
    """Try to start a Docker container by name. Returns True if started/already running."""
    docker = shutil.which("docker")
    if not docker:
        return False
    try:
        # Try to start the container (idempotent if already running)
        result = subprocess.run([docker, "start", container_name], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def _should_fallback_to_sqlite_interactive() -> bool:
    """Decide whether to allow interactive sqlite fallback.

    - If running interactively (tty), ask the user.
    - Otherwise, respect env var `FORCE_SQLITE_FALLBACK=1` to allow non-interactive fallback.
    """
    if sys.stdin is not None and sys.stdin.isatty():
        try:
            ans = input("Postgres is not reachable. Try to start Docker 'kycc-postgres'? [Y/n]: ")
        except Exception:
            ans = ""
        return ans.strip().lower() in ("y", "", "yes")
    return os.getenv("FORCE_SQLITE_FALLBACK", "0") == "1"


try:
    engine = create_engine(DATABASE_URL)

    # Quick connectivity test; if it fails, try to help start Postgres (docker container),
    # then re-test. If still failing, fall back to SQLite (interactive or via env).
    if not _test_engine_connection(engine):
        # Try common container name from README
        started = _attempt_start_docker_container("kycc-postgres")
        if started:
            # give the DB a moment to become ready
            time.sleep(2)
            if not _test_engine_connection(engine):
                started = False

        if not started:
            # Not able to start docker or DB still not reachable
            if _should_fallback_to_sqlite_interactive():
                print("Postgres not reachable; falling back to SQLite for local testing.")
                sqlite_url = os.getenv("DEV_DATABASE_URL", "sqlite:///./dev.db")
                engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
            else:
                raise RuntimeError(
                    "Postgres is not reachable and automatic fallback to SQLite is disabled."
                )
except ModuleNotFoundError:
    # Likely psycopg2 is not installed or the DB URL refers to Postgres.
    print("Warning: Postgres driver not found. Falling back to SQLite for local testing.")
    sqlite_url = os.getenv("DEV_DATABASE_URL", "sqlite:///./dev.db")
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

# Create a SessionLocal class (we'll use this to talk to the database)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all our database models
Base = declarative_base()

# This function gives us a database session when we need one
def get_db():
    db = SessionLocal()
    try:
        yield db  # Give the database session to whoever needs it
    finally:
        db.close()  # Always close the connection when done


# Developer convenience: auto-create tables when using SQLite or when explicitly enabled.
# This ensures quick scripts (like `test_day1.py`) work without manual migrations.
# NOTE: This is called from main.py AFTER all imports, not here, to avoid circular imports.

def init_db():
    """Initialize database tables. Call this after all models are imported."""
    try:
        should_create = os.getenv("AUTO_CREATE_TABLES", "1")
        if "sqlite" in str(engine.url) or should_create == "1":
            Base.metadata.create_all(bind=engine)
    except Exception:
        # If creation fails, don't crash on import; let the runtime handle it.
        pass