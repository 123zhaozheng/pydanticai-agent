"""
Quick setup script to initialize database and seed data.

This script will:
1. Create all database tables
2. Seed all initial data (users, roles, tools, skills, etc.)

Usage:
    python setup_db.py
"""

import sys
from src.database import init_db, SessionLocal
from src.seed_all import seed_all


def setup_database():
    """Initialize database and seed data."""
    print("\n" + "="*60)
    print("🚀 DATABASE SETUP")
    print("="*60)
    
    try:
        # Step 1: Create all tables
        print("\n📋 Step 1: Creating database tables...")
        init_db()
        print("✅ Tables created successfully!")
        
        # Step 2: Seed data
        print("\n📋 Step 2: Seeding initial data...")
        seed_all()
        
        print("\n" + "="*60)
        print("🎉 SETUP COMPLETE!")
        print("="*60)
        print("\nYour database is ready to use!")
        print("You can now start the application.\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = setup_database()
    sys.exit(0 if success else 1)
