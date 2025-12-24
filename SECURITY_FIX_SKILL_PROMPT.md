"""
Security Fix: Skill Permission Filtering in System Prompt

ISSUE:
- System prompt was showing all skills to all users
- Even though list_skills and load_skill have permission checks,
  exposing skill names in system prompt is information leakage

BEFORE:
```python
if include_skills and loaded_skills:
    skills_prompt = get_skills_system_prompt(ctx.deps, loaded_skills)
    # All users see: "code-review, sql-optimizer, ..." 
```

AFTER:
```python
if include_skills and loaded_skills:
    # Filter by permission first
    filtered_skills = await filter_skills_by_permission(
        loaded_skills, ctx.deps.user_id, ctx.deps
    )
    skills_prompt = get_skills_system_prompt(ctx.deps, filtered_skills)
    # User only sees skills they have permission for
```

EXAMPLE:
- Admin user sees: "code-review, sql-optimizer, data-analysis"
- Developer sees: "code-review"  
- Regular user sees: (empty, no skills section)

This ensures:
1. ✅ No information leakage about restricted skills
2. ✅ Cleaner system prompt (less noise)
3. ✅ Consistent with tool filtering behavior
4. ✅ Backward compatible (falls back if permission check fails)
"""
