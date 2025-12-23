"""
Quick Start Guide: Setting up Tools & Skills Tables

This guide shows you how to set up the database tables for MCP tools and skills management.

## Step 1: Review Existing Models

Your existing User, Role, and Department models need to add these relationships:

### In your Role model:
```python
from sqlalchemy.orm import relationship

class Role(Base):
    # ... existing fields ...
    
    # ADD these relationships:
    tool_permissions = relationship("RoleToolPermission", back_populates="role", 
                                   cascade="all, delete-orphan")
    skill_permissions = relationship("RoleSkillPermission", back_populates="role",
                                    cascade="all, delete-orphan")
```

### In your Department model:
```python
class Department(Base):
    # ... existing fields ...
    
    # ADD these relationships:
    tool_permissions = relationship("DepartmentToolPermission", back_populates="department",
                                   cascade="all, delete-orphan")
    skill_permissions = relationship("DepartmentSkillPermission", back_populates="department",
                                    cascade="all, delete-orphan")
```

## Step 2: Run Database Migration

### Option A: Using Alembic (Recommended)
```bash
# Create migration
alembic revision --autogenerate -m "Add tools and skills tables"

# Review the generated migration file in alembic/versions/

# Apply migration
alembic upgrade head
```

### Option B: Direct SQL (if not using Alembic)
```bash
# Use the migration script directly
python -c "
from src.database import engine
from src.migrations.001_add_tools_skills import upgrade
upgrade()
"
```

### Option C: Simple init_db() approach
```python
# Update src/database.py init_db() function:
def init_db():
    # Import all models first
    from src.models.tools_skills import McpTool, Skill  # etc.
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
```

Then run:
```bash
python -c "from src.database import init_db; init_db()"
```

## Step 3: Seed Initial Data

```bash
# Run seed script to create built-in tools and example skills
python -c "
from src.database import SessionLocal
from src.models.seed_data import seed_all

db = SessionLocal()
try:
    seed_all(db)
    print('✅ Seed data created!')
finally:
    db.close()
"
```

## Step 4: Verify Tables Were Created

```bash
# Check tables exist (PostgreSQL)
psql -d your_database -c "\dt"

# Check tables exist (MySQL)
mysql -u your_user -p -e "SHOW TABLES;" your_database

# Check tables exist (SQLite)
sqlite3 your_database.db ".tables"
```

You should see these new tables:
- mcp_tools
- skills
- role_tool_permissions
- role_skill_permissions
- department_tool_permissions
- department_skill_permissions

## Step 5: Test Permission Queries

```python
from src.database import SessionLocal
from src.models.tools_skills import McpTool, RoleToolPermission

db = SessionLocal()

# Check built-in tools were created
tools = db.query(McpTool).filter_by(is_builtin=True).all()
print(f"Found {len(tools)} built-in tools")

# Check admin permissions
admin_perms = db.query(RoleToolPermission).filter_by(role_id=1).all()
print(f"Admin has {len(admin_perms)} tool permissions")

db.close()
```

## Common Issues

### Issue: "Table 'mcp_tools' doesn't exist"
**Solution**: Run the migration (Step 2)

### Issue: "No module named 'src.models.tools_skills'"
**Solution**: Make sure `src/models/__init__.py` exists and exports the models

### Issue: "FOREIGN KEY constraint failed"
**Solution**: Make sure User, Role, and Department tables exist before running migration

### Issue: Enum type error (PostgreSQL)
**Solution**: If using PostgreSQL, the TransportType enum will be created automatically

## Next Steps

After setup is complete:
1. ✅ Tables created
2. ✅ Seed data loaded
3. 👉 Implement tool_filter.py (Phase 3)
4. 👉 Integrate with pydantic_deep agent

See `implementation_plan.md` for the full roadmap.
