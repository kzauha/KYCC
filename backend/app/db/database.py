from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
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
try:
    engine = create_engine(DATABASE_URL)
except ModuleNotFoundError as e:
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
try:
    should_create = os.getenv("AUTO_CREATE_TABLES", "1")
    if "sqlite" in str(engine.url) or should_create == "1":
        # Import models so SQLAlchemy knows about them, then create tables
        import app.models.models  # noqa: F401
        Base.metadata.create_all(bind=engine)
except Exception:
    # If creation fails, don't crash on import; let the runtime handle it.
    pass