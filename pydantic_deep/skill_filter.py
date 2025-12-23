"""Helper functions for skill permission filtering."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_deep.deps import DeepAgentDeps
    from pydantic_deep.types import Skill


async def filter_skills_by_permission(
    skills: list[Skill],
    user_id: int | str | None,
    deps: DeepAgentDeps,
) -> list[Skill]:
    """
    Filter skills based on user permissions.
    
    Args:
        skills: List of all available skills
        user_id: User ID to check permissions for
        deps: Agent dependencies with db and redis clients
        
    Returns:
        Filtered list of skills the user has permission to use
    """
    if not user_id:
        # No user_id, return all skills (backward compatible)
        return skills
    
    from pydantic_deep.tool_filter import get_user_skill_permissions
    
    # Get permitted skill names
    permitted_skills = await get_user_skill_permissions(user_id, deps)
    
    # Filter skills
    filtered = [skill for skill in skills if skill["name"] in permitted_skills]
    
    return filtered
