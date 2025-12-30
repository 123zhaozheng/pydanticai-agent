"""Models package - exports all database models."""

from src.models.tools_skills import (
    McpServer,
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

from src.models.llm_models import (
    LLMModelConfig,
    RoleModelPermission,
    DepartmentModelPermission,
)

__all__ = [
    # Tools & Skills
    "McpServer",
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
    # LLM Models
    "LLMModelConfig",
    "RoleModelPermission",
    "DepartmentModelPermission",
]
