"""
Example: Permission-based tool and skill filtering.

This example demonstrates how to use permission-based filtering to control
which tools and skills users can access based on their role and department.

Prerequisites:
1. Database initialized with setup_db.py
2. Redis server running (optional, will fallback to DB-only if unavailable)

Usage:
    python examples/permission_filtering_example.py
"""

import asyncio
from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend
from pydantic_deep.clients import DbClient, RedisClient
from src.database import SessionLocal


async def example_admin_user():
    """Example: Admin user has access to all tools and skills."""
    print("\n" + "="*60)
    print("ADMIN USER - Full Access")
    print("="*60)
    
    deps = DeepAgentDeps(
        backend=StateBackend(),
        db=DbClient(session_factory=SessionLocal),
        redis=RedisClient(),
        user_id=1,  # Admin user from seed data
    )
    
    agent = create_deep_agent(
        model="openai:gpt-4o-mini",
        enable_permission_filtering=True,
        include_execute=False,  # Exclude for safety in example
    )
    
    result = await agent.run(
        "List all available tools and skills",
        deps=deps
    )
    
    print(f"\nAdmin's available resources:\n{result.output}")


async def example_developer_user():
    """Example: Developer has read/write file access and python_analyzer skill."""
    print("\n" + "="*60)
    print("DEVELOPER USER - Limited Access")
    print("="*60)
    
    deps = DeepAgentDeps(
        backend=StateBackend(),
        db=DbClient(session_factory=SessionLocal),
        redis=RedisClient(),
        user_id=2,  # developer1 from seed data
    )
    
    agent = create_deep_agent(
        model="openai:gpt-4o-mini",
        enable_permission_filtering=True,
        include_execute=False,
    )
    
    result = await agent.run(
        "List all available skills",
        deps=deps
    )
    
    print(f"\nDeveloper's available skills:\n{result.output}")


async def example_data_analyst_user():
    """Example: Data analyst has read-only access and sql_optimizer skill."""
    print("\n" + "="*60)
    print("DATA ANALYST USER - Read-only + SQL Tools")
    print("="*60)
    
    deps = DeepAgentDeps(
        backend=StateBackend(),
        db=DbClient(session_factory=SessionLocal),
        redis=RedisClient(),
        user_id=3,  # analyst1 from seed data
    )
    
    agent = create_deep_agent(
        model="openai:gpt-4o-mini",
        enable_permission_filtering=True,
        include_execute=False,
    )
    
    result = await agent.run(
        "What tools and skills can I use?",
        deps=deps
    )
    
    print(f"\nData Analyst's available resources:\n{result.output}")


async def example_unauthorized_access():
    """Example: Regular user tries to access restricted skill."""
    print("\n" + "="*60)
    print("REGULAR USER - Restricted Access Attempt")
    print("="*60)
    
    deps = DeepAgentDeps(
        backend=StateBackend(),
        db=DbClient(session_factory=SessionLocal),
        redis=RedisClient(),
        user_id=4,  # user1 from seed data (minimal permissions)
    )
    
    agent = create_deep_agent(
        model="openai:gpt-4o-mini",
        enable_permission_filtering=True,
        include_execute=False,
    )
    
    result = await agent.run(
        "Load the python_analyzer skill",
        deps=deps
    )
    
    print(f"\nRegular user trying to load restricted skill:\n{result.output}")


async def example_no_filtering():
    """Example: Agent without permission filtering (backward compatible)."""
    print("\n" + "="*60)
    print("NO FILTERING - Backward Compatible Mode")
    print("="*60)
    
    deps = DeepAgentDeps(
        backend=StateBackend(),
        db=DbClient(session_factory=SessionLocal),
        redis=RedisClient(),
        # No user_id set
    )
    
    agent = create_deep_agent(
        model="openai:gpt-4o-mini",
        enable_permission_filtering=False,  # Filtering disabled
        include_execute=False,
    )
    
    result = await agent.run(
        "List all available skills",
        deps=deps
    )
    
    print(f"\nAll skills (no filtering):\n{result.output}")


async def main():
    """Run all examples."""
    print("\n🔐 PERMISSION-BASED TOOL & SKILL FILTERING EXAMPLES\n")
    print("These examples demonstrate role-based access control for AI agent tools.")
    
    try:
        # Test different user roles
        await example_admin_user()
        await example_developer_user()
        await example_data_analyst_user()
        await example_unauthorized_access()
        await example_no_filtering()
        
        print("\n" + "="*60)
        print("✅ ALL EXAMPLES COMPLETED")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("1. Run 'python setup_db.py' to initialize database")
        print("2. Redis server running (optional)")
        print("3. Configured DATABASE_URL in src/config.py")


if __name__ == "__main__":
    asyncio.run(main())
