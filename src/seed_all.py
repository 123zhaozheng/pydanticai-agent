"""
Complete seed script - combines all seed data.

This script seeds:
1. User management (roles, departments, users, menus, buttons)
2. Tools & Skills (MCP tools, skills, permissions)

Usage:
    python -m src.seed_all
"""

from src.database import SessionLocal
from src.models.seed_user_data import seed_user_management_all
from src.models.seed_data import seed_builtin_tools, seed_example_skills, seed_admin_permissions


def seed_all():
    """Run all seed functions in correct order."""
    db = SessionLocal()
    
    try:
        print("\n" + "="*60)
        print("🌱 SEEDING DATABASE")
        print("="*60)
        
        # 1. User management (must come first)
        print("\n📦 Phase 1: User Management")
        print("-" * 60)
        seed_user_management_all(db)
        
        # 2. Tools & Skills
        print("\n📦 Phase 2: Tools & Skills")
        print("-" * 60)
        seed_builtin_tools(db)
        seed_example_skills(db)
        
        # 3. Admin permissions for tools/skills
        print("\n📦 Phase 3: Admin Permissions")
        print("-" * 60)
        seed_admin_permissions(db, admin_role_id=1)
        
        print("\n" + "="*60)
        print("✅ ALL SEED DATA COMPLETED!")
        print("="*60)
        
        print("\n🔐 Test Accounts:")
        print("  👤 admin / admin123 (System Administrator)")
        print("  👤 developer1 / dev123 (Developer)")
        print("  👤 analyst1 / analyst123 (Data Analyst)")
        print("  👤 user1 / user123 (Regular User)")
        print()
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
