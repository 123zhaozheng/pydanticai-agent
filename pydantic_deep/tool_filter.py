"""Tool and skill permission filtering using prepare_tools API."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic_ai import RunContext, ToolDefinition

if TYPE_CHECKING:
    from pydantic_deep.deps import DeepAgentDeps


_BUILTIN_TOOL_PREFIXES: tuple[str, ...] = (
    "read_todos",
    "write_todos",
    "ls",
    "read_file",
    "write_file",
    "edit_file",
    "glob",
    "grep",
    "execute",
    "task",
    "load_skill",
    "run_skill",
)


async def get_user_tool_permissions(
    user_id: int | str,
    deps: DeepAgentDeps,
) -> set[str]:
    """
    Get list of tool names user is permitted to use.
    
    Uses Redis cache with 5-minute TTL for performance.
    
    Args:
        user_id: User ID to check permissions for
        deps: Agent dependencies with db and redis clients
        
    Returns:
        Set of tool names the user can access
    """
    if not user_id:
        return set()
    
    cache_key = f"user:tool_permissions:{user_id}"
    
    # Try Redis cache first
    try:
        cached = await deps.redis.client.get(cache_key)
        if cached:
            return set(json.loads(cached))
    except Exception:
        # Redis unavailable, fall back to DB
        pass
    
    # Query database
    try:
        from src.models import McpTool, RoleToolPermission, User, DepartmentToolPermission
        
        session = deps.db.get_session()
        
        # Get user
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return set()
        
        # Admin users get all tools
        if user.is_admin:
            tool_names = {tool.name for tool in session.query(McpTool).filter_by(is_active=True).all()}
        else:
            # Get user's role IDs
            role_ids = [role.id for role in user.roles]
            
            # Get permitted tools via roles
            role_permissions = session.query(RoleToolPermission).filter(
                RoleToolPermission.role_id.in_(role_ids),
                RoleToolPermission.can_use == True
            ).all()
            
            tool_ids = {p.tool_id for p in role_permissions}
            
            # Check department restrictions (if user has department)
            if user.department_id:
                dept_restrictions = session.query(DepartmentToolPermission).filter(
                    DepartmentToolPermission.department_id == user.department_id,
                    DepartmentToolPermission.is_allowed == False
                ).all()
                
                blocked_tool_ids = {r.tool_id for r in dept_restrictions}
                tool_ids = tool_ids - blocked_tool_ids
            
            # Get actual tool names
            tools = session.query(McpTool).filter(
                McpTool.id.in_(tool_ids),
                McpTool.is_active == True
            ).all()
            
            tool_names = {tool.name for tool in tools}
        
        # Cache for 5 minutes
        try:
            await deps.redis.client.setex(cache_key, 300, json.dumps(list(tool_names)))
        except Exception:
            pass  # Redis unavailable, continue without caching
        
        return tool_names
        
    except Exception as e:
        # Database error, log and return empty set
        print(f"Error fetching tool permissions: {e}")
        return set()
    finally:
        if 'session' in locals():
            session.close()


async def get_user_skill_permissions(
    user_id: int | str,
    deps: DeepAgentDeps,
) -> set[str]:
    """
    Get list of skill names user is permitted to use.
    
    Uses Redis cache with 5-minute TTL for performance.
    
    Args:
        user_id: User ID to check permissions for
        deps: Agent dependencies with db and redis clients
        
    Returns:
        Set of skill names the user can access
    """
    if not user_id:
        return set()
    
    cache_key = f"user:skill_permissions:{user_id}"
    
    # Try Redis cache first
    try:
        cached = await deps.redis.client.get(cache_key)
        if cached:
            return set(json.loads(cached))
    except Exception:
        pass
    
    # Query database
    try:
        from src.models import Skill, RoleSkillPermission, User, DepartmentSkillPermission
        
        session = deps.db.get_session()
        
        # Get user
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return set()
        
        # Admin users get all skills
        if user.is_admin:
            skill_names = {skill.name for skill in session.query(Skill).filter_by(is_active=True).all()}
        else:
            # Get user's role IDs
            role_ids = [role.id for role in user.roles]
            
            # Get permitted skills via roles
            role_permissions = session.query(RoleSkillPermission).filter(
                RoleSkillPermission.role_id.in_(role_ids),
                RoleSkillPermission.can_use == True
            ).all()
            
            skill_ids = {p.skill_id for p in role_permissions}
            
            # Check department restrictions
            if user.department_id:
                dept_restrictions = session.query(DepartmentSkillPermission).filter(
                    DepartmentSkillPermission.department_id == user.department_id,
                    DepartmentSkillPermission.is_allowed == False
                ).all()
                
                blocked_skill_ids = {r.skill_id for r in dept_restrictions}
                skill_ids = skill_ids - blocked_skill_ids
            
            # Get actual skill names
            skills = session.query(Skill).filter(
                Skill.id.in_(skill_ids),
                Skill.is_active == True
            ).all()
            
            skill_names = {skill.name for skill in skills}
        
        # Cache for 5 minutes
        try:
            await deps.redis.client.setex(cache_key, 300, json.dumps(list(skill_names)))
        except Exception:
            pass
        
        return skill_names
        
    except Exception as e:
        print(f"Error fetching skill permissions: {e}")
        return set()
    finally:
        if 'session' in locals():
            session.close()


async def filter_tools_by_permission(
    ctx: RunContext[DeepAgentDeps],
    tool_defs: list[ToolDefinition]
) -> list[ToolDefinition]:
    """
    Filter tools based on user permissions.
    
    This is the prepare_tools function that PydanticAI calls before each LLM request.
    
    IMPORTANT: Built-in tools (todos, filesystem, subagents, skills) are ALWAYS allowed.
    Permission filtering only applies to MCP tools added from database.
    
    Args:
        ctx: RunContext with deps containing user_id
        tool_defs: List of available tool definitions
        
    Returns:
        Filtered list of tools the user has permission to use
    """
    # If no user_id, return all tools (backward compatible)
    user_id = getattr(ctx.deps, "user_id", None)
    if not user_id:
        return tool_defs
    
    # Get user's permitted MCP tools
    permitted_mcp_tools = await get_user_tool_permissions(user_id, ctx.deps)
    if not permitted_mcp_tools:
        return tool_defs
    
    # Filter tool definitions
    filtered = []
    append = filtered.append
    builtin_prefixes = _BUILTIN_TOOL_PREFIXES
    for tool_def in tool_defs:
        name = tool_def.name
        if name.startswith(builtin_prefixes) or name in permitted_mcp_tools:
            append(tool_def)
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[ToolFilter] User {user_id}: {len(filtered)}/{len(tool_defs)} tools allowed")
    
    return filtered


def create_permission_filter():
    """
    Create a prepare_tools function for permission filtering.
    
    Returns:
        Async function compatible with Agent's prepare_tools parameter
        
    Example:
        agent = Agent(
            model='openai:gpt-4',
            prepare_tools=create_permission_filter(),
            deps_type=DeepAgentDeps,
        )
    """
    return filter_tools_by_permission

def get_user_permitted_skills(
    user_id: int,
    db_session,
) -> list:
    """Get skills that a user has permission to use.
    
    Args:
        user_id: User ID to check permissions for
        db_session: SQLAlchemy database session
        
    Returns:
        List of Skill objects the user can access
        
    Example:
        ```python
        from src.database import get_db
        db = next(get_db())
        skills = get_user_permitted_skills(user_id=1, db_session=db)
        for skill in skills:
            print(f"User can use skill: {skill.name}")
        ```
    """
    from src.models.tools_skills import Skill, RoleSkillPermission, DepartmentSkillPermission
    from src.models.user_management import User
    
    # Get user
    user = db_session.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    
    # Get role IDs (many-to-many relationship)
    role_ids = [role.id for role in user.roles] if user.roles else []
    if not role_ids:
        return []
    
    # Query skills via role permissions
    permitted_skills = db_session.query(Skill).join(
        RoleSkillPermission,
        RoleSkillPermission.skill_id == Skill.id
    ).filter(
        RoleSkillPermission.role_id.in_(role_ids),
        RoleSkillPermission.can_use == True,
        Skill.is_active == True
    ).all()
    
    # Filter by department restrictions if user has department
    if user.department_id:
        dept_restrictions = db_session.query(DepartmentSkillPermission).filter(
            DepartmentSkillPermission.department_id == user.department_id,
            DepartmentSkillPermission.is_allowed == False
        ).all()
        blocked_skill_ids = {r.skill_id for r in dept_restrictions}
        permitted_skills = [s for s in permitted_skills if s.id not in blocked_skill_ids]
    
    return permitted_skills
