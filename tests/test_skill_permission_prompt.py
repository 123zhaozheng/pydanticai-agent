"""
Test: Verify skill permission filtering in system prompt.

This test ensures that the dynamic system prompt only shows skills
that the user has permission to access.
"""

import pytest
from pydantic_deep import create_deep_agent, DeepAgentDeps
from pydantic_deep.clients import DbClient, RedisClient


@pytest.mark.asyncio
async def test_skill_system_prompt_filtering_admin():
    """Admin users should see all skills in system prompt."""
    deps = DeepAgentDeps(
        user_id=1,  # Admin user
        db=DbClient(),
        redis=RedisClient(),
    )
    
    agent = create_deep_agent(
        enable_permission_filtering=True,
        include_skills=True,
        skill_directories=[{"path": "examples/skills"}],
    )
    
    # Get system prompt
    result = await agent.run("What skills do I have?", deps=deps)
    
    # Admin should see all skills mentioned
    assert "code-review" in result.output.lower()
    # Add more assertions based on your skills


@pytest.mark.asyncio
async def test_skill_system_prompt_filtering_limited_user():
    """Limited users should only see permitted skills in system prompt."""
    deps = DeepAgentDeps(
        user_id=4,  # user1 - minimal permissions
        db=DbClient(),
        redis=RedisClient(),
    )
    
    agent = create_deep_agent(
        enable_permission_filtering=True,
        include_skills=True,
        skill_directories=[{"path": "examples/skills"}],
    )
    
    result = await agent.run("What skills do I have?", deps=deps)
    
    # Regular user should not see restricted skills
    assert "python-analyzer" not in result.output.lower()
    # Or should see "no skills" message


@pytest.mark.asyncio
async def test_skill_system_prompt_no_user_id():
    """Without user_id, all skills should be shown (backward compatible)."""
    deps = DeepAgentDeps(
        # No user_id
        db=DbClient(),
        redis=RedisClient(),
    )
    
    agent = create_deep_agent(
        enable_permission_filtering=True,
        include_skills=True,
        skill_directories=[{"path": "examples/skills"}],
    )
    
    result = await agent.run("What skills do I have?", deps=deps)
    
    # All skills visible when no user_id
    assert "code-review" in result.output.lower()
