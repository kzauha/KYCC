
import sys
import os
import shutil
from pathlib import Path
from sqlalchemy import text

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal, engine, Base
# Import models to ensure they are registered for create_all
from app.models import models

def cleanup_db():
    print("🧹 Starting Database Cleanup (Drop & Recreate)...")
    db = SessionLocal()
    try:
        # DROP ALL TABLES to ensure schema update
        print("   Dropping all tables...")
        # Need to close session before dropping? SQLAlchemy handles it usually but connection might be open
        db.close() 
        
        try:
           Base.metadata.drop_all(bind=engine)
           print("   ✅ Tables dropped.")
        except Exception as e:
           print(f"   ⚠️ Drop failed (might be locked?): {e}")

        print("   Recreating tables...")
        Base.metadata.create_all(bind=engine)
        print("   ✅ Tables created (Schema Updated).")
            
        print("✅ Database Reset Successfully!")
    except Exception as e:
        print(f"❌ Database reset failed: {e}")

def cleanup_dagster():
    print("🧹 Cleaning Dagster Local State...")
    dagster_home = BACKEND_DIR / "dagster_home"
    
    # Clean history
    history_dir = dagster_home / "history"
    if history_dir.exists():
        for item in history_dir.iterdir():
            if item.is_file() and item.suffix == ".db":
                try:
                    os.remove(item)
                    print(f"   - Deleted {item.name}")
                except Exception as e:
                    print(f"   - Failed to delete {item.name}: {e}")
    
    # Clean storage
    storage_dir = dagster_home / "storage"
    if storage_dir.exists():
        for item in storage_dir.iterdir():
             if item.is_dir(): # Run directories
                 try:
                     shutil.rmtree(item)
                     print(f"   - Deleted storage/{item.name}")
                 except Exception as e:
                     print(f"   - Failed to delete {item.name}: {e}")

    print("✅ Dagster state cleaned!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Skip confirmation")
    args = parser.parse_args()

    if args.force:
        cleanup_db()
        cleanup_dagster()
    else:
        confirm = input("⚠️ This will WIPE ALL DATA and RECREATE SCHEMA. Type 'yes' to proceed: ")
        if confirm.lower() == "yes":
            cleanup_db()
            cleanup_dagster()
        else:
            print("Operation cancelled.")
