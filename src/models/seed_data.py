"""Seed data for MCP servers, skills, and permissions."""

from sqlalchemy.orm import Session
from src.models.tools_skills import McpServer, Skill, RoleToolPermission, RoleSkillPermission


def seed_builtin_tools(db: Session) -> None:
    """Create example built-in MCP server."""
    
    # In the new architecture, we register Servers, not individual tools.
    # Builtin tools (fs, todo) are added by the agent, not via MCP Server table usually.
    # We add an example MCP server here.
    
    builtin_servers = [
        {
            "name": "example-stdio-server",
            "description": "Example STDIO based MCP server",
            "transport_type": "stdio",
            "command": "python",
            "args": ["-m", "mcp_test_server"],
            "env": {"DEBUG": "1"},
            "is_builtin": False,
            "is_active": True,
        }
    ]
    
    for server_data in builtin_servers:
        # Check if server already exists
        existing = db.query(McpServer).filter_by(name=server_data["name"]).first()
        if not existing:
            server = McpServer(**server_data)
            db.add(server)
    
    db.commit()


def seed_example_skills(db: Session) -> None:
    """Create example skills."""
    
    example_skills = [
        {
            "name": "python_code_analyzer",
            "description": "Analyzes Python code for quality issues and best practices",
            "path": "/app/skills/python-analyzer",
            "version": "1.0.0",
            "author": "System",
            "tags": ["python", "code-quality", "linting"],
            "resources": ["pylint_config.json", "analysis_template.md"],
            "frontmatter": {
                "name": "python_code_analyzer",
                "description": "Analyzes Python code for quality issues",
                "tags": ["python", "code-quality"]
            },
            "is_active": True,
            "is_verified": True,
        },
        {
            "name": "sql_optimizer",
            "description": "SQL query optimization and performance analysis",
            "path": "/app/skills/sql-optimizer",
            "version": "1.2.0",
            "author": "System",
            "tags": ["sql", "database", "performance"],
            "resources": ["optimization_rules.yaml"],
            "frontmatter": {
                "name": "sql_optimizer",
                "description": "SQL query optimization advisor",
                "tags": ["sql", "database"]
            },
            "is_active": True,
            "is_verified": True,
        },
    ]
    
    for skill_data in example_skills:
        existing = db.query(Skill).filter_by(name=skill_data["name"]).first()
        if not existing:
            skill = Skill(**skill_data)
            db.add(skill)
    
    db.commit()


def seed_admin_permissions(db: Session, admin_role_id: int) -> None:
    """Grant admin role all server and skill permissions.
    
    Args:
        db: Database session
        admin_role_id: ID of the admin role (usually 1)
    """
    # Grant all server permissions to admin
    servers = db.query(McpServer).all()
    for server in servers:
        existing = db.query(RoleToolPermission).filter_by(
            role_id=admin_role_id,
            server_id=server.id
        ).first()
        if not existing:
            perm = RoleToolPermission(
                role_id=admin_role_id,
                server_id=server.id,
                can_use=True,
                can_configure=True
            )
            db.add(perm)
    
    # Grant all skill permissions to admin
    skills = db.query(Skill).all()
    for skill in skills:
        existing = db.query(RoleSkillPermission).filter_by(
            role_id=admin_role_id,
            skill_id=skill.id
        ).first()
        if not existing:
            perm = RoleSkillPermission(
                role_id=admin_role_id,
                skill_id=skill.id,
                can_use=True,
                can_manage=True
            )
            db.add(perm)
    
    db.commit()


def seed_all(db: Session) -> None:
    """Run all seed functions.
    
    Usage:
        from src.database import SessionLocal
        from src.models.seed_data import seed_all
        
        db = SessionLocal()
        try:
            seed_all(db)
            print("✅ Seed data created successfully!")
        finally:
            db.close()
    """
    print("📦 Seeding built-in servers...")
    seed_builtin_tools(db)
    
    print("📦 Seeding example skills...")
    seed_example_skills(db)
    
    print("🔐 Seeding admin permissions (role_id=1)...")
    seed_admin_permissions(db, admin_role_id=1)
    
    print("✅ All seed data created!")
