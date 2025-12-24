"""Models package - exports all database models."""

from src.models.tools_skills import (
    McpTool,
    Skill,
    RoleToolPermission,
    RoleSkillPermission,
    DepartmentToolPermission,
    DepartmentSkillPermission,
    TransportType,
)

from src.models.user_management import (
    User,
    Role,
    Department,
    Menu,
    Button,
    RoleMenu,
    RoleButton,
    user_role,
)

from src.models.conversations import (
    Conversation,
    Message,
)

__all__ = [
    # Tools & Skills
    "McpTool",
    "Skill",
    "RoleToolPermission",
    "RoleSkillPermission",
    "DepartmentToolPermission",
    "DepartmentSkillPermission",
    "TransportType",
    # User Management
    "User",
    "Role",
    "Department",
    "Menu",
    "Button",
    "RoleMenu",
    "RoleButton",
    "user_role",
    # Conversations
    "Conversation",
    "Message",
]
