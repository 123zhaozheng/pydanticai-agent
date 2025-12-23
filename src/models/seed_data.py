"""Seed data for MCP tools, skills, and permissions."""

from sqlalchemy.orm import Session
from src.models.tools_skills import McpTool, Skill, RoleToolPermission, RoleSkillPermission


def seed_builtin_tools(db: Session) -> None:
    """Create built-in tools (filesystem, todo, etc.)."""
    
    builtin_tools = [
        {
            "name": "read_file",
            "description": "Read file content with line numbers",
            "transport_type": "http",
            "url": "http://localhost:8080/tools/read_file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "offset": {"type": "integer", "description": "Starting line (0-indexed)"},
                    "limit": {"type": "integer", "description": "Max lines to read"}
                },
                "required": ["path"]
            },
            "is_builtin": True,
            "is_active": True,
        },
        {
            "name": "write_file",
            "description": "Write content to a file (creates or overwrites)",
            "transport_type": "http",
            "url": "http://localhost:8080/tools/write_file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["path", "content"]
            },
            "is_builtin": True,
            "is_active": True,
        },
        {
            "name": "edit_file",
            "description": "Edit a file by replacing strings",
            "transport_type": "http",
            "url": "http://localhost:8080/tools/edit_file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                    "replace_all": {"type": "boolean", "default": False}
                },
                "required": ["path", "old_string", "new_string"]
            },
            "is_builtin": True,
            "is_active": True,
        },
        {
            "name": "execute",
            "description": "Execute a shell command",
            "transport_type": "http",
            "url": "http://localhost:8080/tools/execute",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 120}
                },
                "required": ["command"]
            },
            "is_builtin": True,
            "is_active": True,
        },
        {
            "name": "ls",
            "description": "List files and directories",
            "transport_type": "http",
            "url": "http://localhost:8080/tools/ls",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path", "default": "/"}
                }
            },
            "is_builtin": True,
            "is_active": True,
        },
        {
            "name": "glob",
            "description": "Find files matching a glob pattern",
            "transport_type": "http",
            "url": "http://localhost:8080/tools/glob",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (e.g., '**/*.py')"},
                    "path": {"type": "string", "description": "Base directory", "default": "/"}
                },
                "required": ["pattern"]
            },
            "is_builtin": True,
            "is_active": True,
        },
        {
            "name": "grep",
            "description": "Search for a regex pattern in files",
            "transport_type": "http",
            "url": "http://localhost:8080/tools/grep",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search"},
                    "path": {"type": "string", "description": "File or directory to search"},
                    "glob_pattern": {"type": "string", "description": "Glob pattern to filter files"},
                    "output_mode": {
                        "type": "string",
                        "enum": ["content", "files_with_matches", "count"],
                        "default": "files_with_matches"
                    }
                },
                "required": ["pattern"]
            },
            "is_builtin": True,
            "is_active": True,
        },
    ]
    
    for tool_data in builtin_tools:
        # Check if tool already exists
        existing = db.query(McpTool).filter_by(name=tool_data["name"]).first()
        if not existing:
            tool = McpTool(**tool_data)
            db.add(tool)
    
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
    """Grant admin role all tool and skill permissions.
    
    Args:
        db: Database session
        admin_role_id: ID of the admin role (usually 1)
    """
    # Grant all tool permissions to admin
    tools = db.query(McpTool).all()
    for tool in tools:
        existing = db.query(RoleToolPermission).filter_by(
            role_id=admin_role_id,
            tool_id=tool.id
        ).first()
        if not existing:
            perm = RoleToolPermission(
                role_id=admin_role_id,
                tool_id=tool.id,
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
    print("📦 Seeding built-in tools...")
    seed_builtin_tools(db)
    
    print("📦 Seeding example skills...")
    seed_example_skills(db)
    
    print("🔐 Seeding admin permissions (role_id=1)...")
    seed_admin_permissions(db, admin_role_id=1)
    
    print("✅ All seed data created!")
