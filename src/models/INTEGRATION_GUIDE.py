"""
Update existing User, Role, and Department models with tool/skill permission relationships.

Add these relationships to your existing models:
"""

# ============================================================================
# ADD TO: Role model (app/models/user.py or wherever Role is defined)
# ============================================================================

# ADD these imports at the top:
# from sqlalchemy.orm import relationship

# ADD to Role class:
class Role:
    # ... existing fields ...
    
    # ADD these new relationships:
    tool_permissions = relationship("RoleToolPermission", back_populates="role", 
                                   cascade="all, delete-orphan")
    skill_permissions = relationship("RoleSkillPermission", back_populates="role",
                                    cascade="all, delete-orphan")


# ============================================================================
# ADD TO: Department model (app/models/user.py or wherever Department is defined)
# ============================================================================

# ADD to Department class:
class Department:
    # ... existing fields ...
    
    # ADD these new relationships:
    tool_permissions = relationship("DepartmentToolPermission", back_populates="department",
                                   cascade="all, delete-orphan")
    skill_permissions = relationship("DepartmentSkillPermission", back_populates="department",
                                    cascade="all, delete-orphan")


# ============================================================================
# NOTES:
# ============================================================================
# 1. Make sure to import the new models in your __init__.py:
#    from src.models.tools_skills import (
#        McpTool, Skill, RoleToolPermission, RoleSkillPermission,
#        DepartmentToolPermission, DepartmentSkillPermission
#    )
#
# 2. After adding these relationships, run migration:
#    alembic revision --autogenerate -m "Add tools and skills tables"
#    alembic upgrade head
