# Permission-Based Tool & Skill Filtering - User Guide

## Overview

The pydantic-deep agent now supports permission-based filtering to control which tools and skills users can access based on their database roles and department.

## Quick Start

### 1. Enable Permission Filtering

```python
from pydantic_deep import create_deep_agent, DeepAgentDeps
from pydantic_deep.clients import DbClient, RedisClient

# Create agent with permission filtering enabled
agent = create_deep_agent(
    model="openai:gpt-4",
    enable_permission_filtering=True,  # Enable filtering
)

# Set user_id in deps when running
deps = DeepAgentDeps(
    db=DbClient(...),
    redis=RedisClient(...),
    user_id=123,  # User ID from database
)

result = await agent.run("Your query here", deps=deps)
```

### 2. How It Works

**Tool Filtering (`prepare_tools`):**
- Filters tools before each LLM request
- Queries database for user's role-based tool permissions
- Caches results in Redis for 5 minutes
- Admin users bypass all restrictions

**Skill Filtering (Runtime):**
- Filters skills in `list_skills` tool
- Checks permissions in `load_skill` tool
- Returns permission denied message for unauthorized access

**Permission Resolution:**
1. **Admin bypass:** `is_admin=True` → all tools/skills
2. **Tool active check:** `is_active=False` → blocked
3. **Department restrictions:** Department blocks tool → denied
4. **Role permissions:** User's roles grant access → allowed

## Database Schema

**Required Tables:**
- `users` - User accounts
- `roles` - User roles (admin, developer, etc.)
- `user_role` - User-role assignments
- `departments` - Organizational structure
- `mcp_tools` - Available MCP tools
- `skills` - Available skills
- `role_tool_permissions` - Role → Tool permissions
- `role_skill_permissions` - Role → Skill permissions
- `department_tool_permissions` - (Optional) Department restrictions
- `department_skill_permissions` - (Optional) Department restrictions

## Setting Up Permissions

### 1. Initialize Database

```bash
python setup_db.py
```

This creates:
- Default roles (admin, developer, data_analyst, user)
- Test users with different permissions
- Built-in tools (read_file, write_file, execute, etc.)
- Example skills (python_analyzer, sql_optimizer)

### 2. Grant Tool Permissions

```python
from src.database import SessionLocal
from src.models import RoleToolPermission, Role, McpTool

db = SessionLocal()

# Get role and tool
role = db.query(Role).filter_by(name="developer").first()
tool = db.query(McpTool).filter_by(name="write_file").first()

# Grant permission
permission = RoleToolPermission(
    role_id=role.id,
    tool_id=tool.id,
    can_use=True,
    can_configure=False,
)
db.add(permission)
db.commit()
```

### 3. Grant Skill Permissions

```python
from src.models import RoleSkillPermission, Skill

# Get skill
skill = db.query(Skill).filter_by(name="python_analyzer").first()

# Grant permission
permission = RoleSkillPermission(
    role_id=role.id,
    skill_id=skill.id,
    can_use=True,
    can_manage=False,
)
db.add(permission)
db.commit()
```

## Examples

### Admin User (Full Access)

```python
deps = DeepAgentDeps(
    db=DbClient(...),
    redis=RedisClient(...),
    user_id=1,  # Admin user
)

agent = create_deep_agent(enable_permission_filtering=True)
result = await agent.run("List all tools and skills", deps=deps)
# Admin sees everything
```

### Developer (Limited Access)

```python
deps = DeepAgentDeps(
    db=DbClient(...),
    redis=RedisClient(...),
    user_id=2,  # Developer user
)

agent = create_deep_agent(enable_permission_filtering=True)
result = await agent.run("Write a file", deps=deps)
# Can use read_file, write_file, python_analyzer
```

### Regular User (Restricted)

```python
deps = DeepAgentDeps(
    db=DbClient(...),
    redis=RedisClient(...),
    user_id=4,  # Regular user
)

agent = create_deep_agent(enable_permission_filtering=True)
result = await agent.run("Load python_analyzer skill", deps=deps)
# Error: "You don't have permission to load skill 'python_analyzer'"
```

## Redis Caching

**Automatic Caching:**
- Tool permissions: `user:tool_permissions:{user_id}`
- Skill permissions: `user:skill_permissions:{user_id}`
- TTL: 5 minutes (300 seconds)

**Clear Cache:**
```python
import redis
r = redis.from_url("redis://localhost:6379/0")
r.delete(f"user:tool_permissions:{user_id}")
r.delete(f"user:skill_permissions:{user_id}")
```

## Backward Compatibility

**Without `user_id`:**
```python
deps = DeepAgentDeps()  # No user_id
agent = create_deep_agent(enable_permission_filtering=True)
result = await agent.run("List skills", deps=deps)
# Returns all tools/skills (no filtering)
```

**Without enabling filtering:**
```python
agent = create_deep_agent(enable_permission_filtering=False)
# All users see all tools/skills
```

## Department-Level Restrictions

**Block tool for entire department:**
```python
from src.models import DepartmentToolPermission

restriction = DepartmentToolPermission(
    department_id=engineering_dept.id,
    tool_id=dangerous_tool.id,
    is_allowed=False,  # Block this tool
)
db.add(restriction)
db.commit()
```

Even if a user's role grants access, department restrictions override.

## Testing

**Run example:**
```bash
python examples/permission_filtering_example.py
```

**Run tests:**
```bash
pytest tests/test_tool_filter.py -v
```

## Troubleshooting

### Issue: All tools filtered out for user
**Solution:** Check role assignments and permissions:
```python
user = db.query(User).filter_by(id=user_id).first()
print(f"Roles: {[r.name for r in user.roles]}")
print(f"Is admin: {user.is_admin}")
```

### Issue: Redis connection error
**Solution:** Falls back to DB-only (slightly slower), no action needed if acceptable.

### Issue: Permission check takes too long
**Solution:** Ensure Redis is running for caching, or increase cache TTL.

## Best Practices

1. **Admin Users:** Use sparingly, only for system administrators
2. **Role Design:** Create specific roles (developer, analyst, etc.) instead of per-user permissions
3. **Cache Invalidation:** Clear cache when permissions change
4. **Department Restrictions:** Use for org-wide policies
5. **Monitoring:** Log permission denials for security auditing

## Advanced: Custom Permission Logic

You can extend the permission system by modifying `tool_filter.py`:

```python
async def custom_permission_check(user_id, tool_name, deps):
    # Your custom logic here
    # e.g., time-based access, quota checking, etc.
    pass
```
