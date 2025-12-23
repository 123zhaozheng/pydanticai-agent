"""Seed data for users, roles, and departments."""

from sqlalchemy.orm import Session
from src.models.user_management import User, Role, Department, Menu, Button, RoleMenu, RoleButton


def hash_password(password: str) -> str:
    """Simple password hashing for demo purposes.
    
    In production, use proper hashing like bcrypt or argon2.
    """
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def seed_roles(db: Session) -> None:
    """Create default roles."""
    
    roles_data = [
        {"name": "admin", "description": "System Administrator - Full access", "is_default": False},
        {"name": "developer", "description": "Software Developer - Code and development tools access", "is_default": False},
        {"name": "data_analyst", "description": "Data Analyst - Read-only and data tools access", "is_default": False},
        {"name": "user", "description": "Regular User - Basic access", "is_default": True},
    ]
    
    for role_data in roles_data:
        existing = db.query(Role).filter_by(name=role_data["name"]).first()
        if not existing:
            role = Role(**role_data)
            db.add(role)
    
    db.commit()
    print("✅ Created default roles")


def seed_departments(db: Session) -> None:
    """Create default departments."""
    
    departments_data = [
        {"name": "Engineering", "description": "Engineering and Development"},
        {"name": "Data Science", "description": "Data Analysis and ML"},
        {"name": "Operations", "description": "IT Operations and Infrastructure"},
    ]
    
    for dept_data in departments_data:
        existing = db.query(Department).filter_by(name=dept_data["name"]).first()
        if not existing:
            dept = Department(**dept_data)
            db.add(dept)
    
    db.commit()
    print("✅ Created default departments")


def seed_admin_user(db: Session) -> None:
    """Create admin user for testing.
    
    Credentials:
        Username: admin
        Password: admin123
    """
    
    existing = db.query(User).filter_by(username="admin").first()
    if existing:
        print("⚠️  Admin user already exists")
        return
    
    # Get admin role
    admin_role = db.query(Role).filter_by(name="admin").first()
    if not admin_role:
        print("❌ Admin role not found, run seed_roles first!")
        return
    
    # Create admin user
    admin_user = User(
        username="admin",
        email="admin@example.com",
        full_name="System Administrator",
        hashed_password=hash_password("admin123"),
        is_active=True,
        is_admin=True,
    )
    
    db.add(admin_user)
    db.flush()  # Get the user ID
    
    # Assign admin role
    admin_user.roles.append(admin_role)
    
    db.commit()
    print("✅ Created admin user (username: admin, password: admin123)")


def seed_test_users(db: Session) -> None:
    """Create test users for different roles."""
    
    test_users = [
        {
            "username": "developer1",
            "email": "dev1@example.com",
            "full_name": "Alice Developer",
            "password": "dev123",
            "role_name": "developer",
            "department_name": "Engineering",
        },
        {
            "username": "analyst1",
            "email": "analyst1@example.com",
            "full_name": "Bob Analyst",
            "password": "analyst123",
            "role_name": "data_analyst",
            "department_name": "Data Science",
        },
        {
            "username": "user1",
            "email": "user1@example.com",
            "full_name": "Charlie User",
            "password": "user123",
            "role_name": "user",
            "department_name": "Operations",
        },
    ]
    
    for user_data in test_users:
        existing = db.query(User).filter_by(username=user_data["username"]).first()
        if existing:
            continue
        
        # Get role and department
        role = db.query(Role).filter_by(name=user_data["role_name"]).first()
        department = db.query(Department).filter_by(name=user_data["department_name"]).first()
        
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data["full_name"],
            hashed_password=hash_password(user_data["password"]),
            is_active=True,
            is_admin=False,
            department_id=department.id if department else None,
        )
        
        db.add(user)
        db.flush()
        
        if role:
            user.roles.append(role)
    
    db.commit()
    print("✅ Created test users (developer1, analyst1, user1)")


def seed_menus(db: Session) -> None:
    """Create default menu structure."""
    
    menus_data = [
        {"name": "Dashboard", "path": "/dashboard", "icon": "home", "order": 1, "parent_id": None},
        {"name": "Tools", "path": "/tools", "icon": "tools", "order": 2, "parent_id": None},
        {"name": "Skills", "path": "/skills", "icon": "book", "order": 3, "parent_id": None},
        {"name": "Settings", "path": "/settings", "icon": "settings", "order": 4, "parent_id": None},
    ]
    
    for menu_data in menus_data:
        existing = db.query(Menu).filter_by(name=menu_data["name"]).first()
        if not existing:
            menu = Menu(**menu_data)
            db.add(menu)
    
    db.commit()
    print("✅ Created default menus")


def seed_buttons(db: Session) -> None:
    """Create default buttons with permission keys."""
    
    buttons_data = [
        {"name": "Create Tool", "permission_key": "tool:create", "description": "Create new MCP tool"},
        {"name": "Edit Tool", "permission_key": "tool:edit", "description": "Edit existing tool"},
        {"name": "Delete Tool", "permission_key": "tool:delete", "description": "Delete tool"},
        {"name": "Create Skill", "permission_key": "skill:create", "description": "Create new skill"},
        {"name": "Edit Skill", "permission_key": "skill:edit", "description": "Edit existing skill"},
        {"name": "Delete Skill", "permission_key": "skill:delete", "description": "Delete skill"},
    ]
    
    for button_data in buttons_data:
        existing = db.query(Button).filter_by(permission_key=button_data["permission_key"]).first()
        if not existing:
            button = Button(**button_data)
            db.add(button)
    
    db.commit()
    print("✅ Created default buttons")


def seed_user_management_all(db: Session) -> None:
    """Run all user management seed functions.
    
    Usage:
        from src.database import SessionLocal
        from src.models.seed_user_data import seed_user_management_all
        
        db = SessionLocal()
        try:
            seed_user_management_all(db)
        finally:
            db.close()
    """
    print("\n📦 Seeding user management data...\n")
    
    seed_roles(db)
    seed_departments(db)
    seed_menus(db)
    seed_buttons(db)
    seed_admin_user(db)
    seed_test_users(db)
    
    print("\n✅ User management seed data complete!\n")
    print("Test accounts:")
    print("  - admin / admin123 (admin)")
    print("  - developer1 / dev123 (developer)")
    print("  - analyst1 / analyst123 (data_analyst)")
    print("  - user1 / user123 (user)")
