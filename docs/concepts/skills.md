# 技能 (Skills)

技能是通过基于文件系统的配置扩展 Agent 能力的模块化包。它们支持**渐进式披露**——仅在需要时加载详细指令。

## 什么是技能？

一个技能是一个包含以下内容的文件夹：

- `SKILL.md` - 带有 YAML frontmatter 和指令的定义
- 可选的资源文件（模板、脚本、文档）

```
~/.pydantic-deep/skills/
├── code-review/
│   ├── SKILL.md
│   └── checklist.md
├── test-generator/
│   ├── SKILL.md
│   └── templates/
│       └── pytest.py
└── documentation/
    └── SKILL.md
```

## SKILL.md 格式

```markdown
---
name: code-review
description: Review Python code for quality and security
version: 1.0.0
tags:
  - code
  - review
  - python
author: your-name
---

# Code Review Skill

给 Agent 的详细指令...

## Review Process

1. Read the entire file first
2. Check for security issues
3. Review code structure
...
```

### Frontmatter 字段

| 字段 | 必需 | 描述 |
|-------|----------|-------------|
| `name` | 是 | 唯一技能标识符 |
| `description` | 是 | 简要描述（显示在列表中） |
| `version` | 否 | 语义版本（默认：'1.0.0'） |
| `tags` | 否 | 用于分类的标签列表 |
| `author` | 否 | 技能作者 |

## 渐进式披露

技能使用渐进式披露来优化 Token 使用：

### 1. 发现（低成本）

仅加载 YAML frontmatter：

```python
# Agent calls list_skills()
# Returns:
# - code-review: Review Python code for quality and security [code, review]
# - test-generator: Generate pytest test cases [testing, python]
```

### 2. 加载（按需）

需要时加载完整指令：

```python
# Agent calls load_skill("code-review")
# Returns complete SKILL.md content
```

### 3. 资源（按需）

单独访问额外文件：

```python
# Agent calls read_skill_resource("code-review", "checklist.md")
# Returns specific resource file
```

## 使用技能

### 启用技能

```python
from pydantic_deep import create_deep_agent

agent = create_deep_agent(
    skill_directories=[
        {"path": "~/.pydantic-deep/skills", "recursive": True},
    ],
    include_skills=True,
)
```

### 可用工具

| 工具 | 描述 |
|------|-------------|
| `list_skills` | 列出所有可用技能 |
| `load_skill` | 加载技能的完整指令 |
| `read_skill_resource` | 从技能中读取资源文件 |

### Agent 工作流

Agent 通常：

1. 接收任务（"检查此代码的安全问题"）
2. 列出可用技能以查找相关技能
3. 加载适当的技能指令
4. 遵循技能指南
5. 按需访问资源

## 创建技能

### 步骤 1: 创建目录

```bash
mkdir -p ~/.pydantic-deep/skills/my-skill
```

### 步骤 2: 编写 SKILL.md

```markdown
---
name: api-design
description: Design RESTful APIs following best practices
version: 1.0.0
tags:
  - api
  - rest
  - design
author: your-name
---

# API Design Skill

你是一位 API 设计专家。设计 API 时，请遵循以下原则：

## REST Conventions

- Use nouns for resources: `/users`, `/orders`
- Use HTTP methods correctly: GET, POST, PUT, DELETE
- Version your API: `/v1/users`

## Response Format

始终返回结构一致的 JSON：

```json
{
  "data": {...},
  "meta": {
    "page": 1,
    "total": 100
  }
}
```

## Error Handling

返回适当的状态码：
- 400: Bad request
- 401: Unauthorized
- 404: Not found
- 500: Server error
```

### 步骤 3: 添加资源（可选）

```bash
# 创建模板文件
cat > ~/.pydantic-deep/skills/api-design/openapi-template.yaml << 'EOF'
openapi: 3.0.0
info:
  title: API Name
  version: 1.0.0
paths: {}
EOF
```

## 技能发现

### 从目录

```python
from pydantic_deep.toolsets.skills import discover_skills

skills = discover_skills([
    {"path": "~/.pydantic-deep/skills", "recursive": True},
    {"path": "./project-skills", "recursive": False},
])

for skill in skills:
    print(f"{skill['name']}: {skill['description']}")
```

### 预加载技能

```python
skills = [
    {
        "name": "code-review",
        "description": "Review code for quality",
        "path": "/path/to/skill",
        "tags": ["code"],
        "version": "1.0.0",
        "author": "",
        "frontmatter_loaded": True,
    }
]

agent = create_deep_agent(skills=skills)
```

## 示例：代码审查技能

### SKILL.md

```markdown
---
name: code-review
description: Review Python code for quality, security, and best practices
version: 1.0.0
tags:
  - code
  - review
  - python
  - security
---

# Code Review Skill

审查代码时，请遵循此检查清单：

## Security

- [ ] No hardcoded secrets
- [ ] Input validation on external data
- [ ] No SQL injection vulnerabilities
- [ ] Proper error handling

## Code Quality

- [ ] Functions have single responsibility
- [ ] Descriptive variable names
- [ ] Type hints present
- [ ] Docstrings for public functions

## Output Format

```markdown
## Summary
[Brief assessment]

## Critical Issues
- [List security/major bugs]

## Improvements
- [Suggested improvements]

## Good Practices
- [Positive aspects]
```
```

### 用法

```python
agent = create_deep_agent(
    skill_directories=[{"path": "./skills"}],
)

result = await agent.run(
    "Load the code-review skill and review /src/auth.py",
    deps=deps,
)
```

## 最佳实践

### 1. 清晰的名称

使用描述性的、连字符连接的名称：
- ✅ `code-review`, `test-generator`, `api-design`
- ❌ `cr`, `skill1`, `mySkill`

### 2. 专注的技能

每个技能应该做好一件事：
- ✅ `code-review` - Reviews code
- ❌ `code-review-and-testing-and-docs` - 太宽泛

### 3. 可操作的指令

编写 Agent 可以遵循的指令：

```markdown
# Good
When you find a security issue:
1. Note the file and line number
2. Describe the vulnerability
3. Suggest a fix with code example

# Bad
Be careful about security.
```

### 4. 包含示例

显示预期的输出格式：

```markdown
## Example Review

**File:** auth.py:42
**Issue:** SQL Injection
**Severity:** Critical

```python
# Bad
query = f"SELECT * FROM users WHERE id = {user_id}"

# Good
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```
```

### 5. 版本化你的技能

进行更改时更新版本：

```yaml
version: 1.0.0  # Initial release
version: 1.1.0  # Added new checklist items
version: 2.0.0  # Breaking changes to format
```

## 下一步

- [技能示例](../examples/skills.md) - 完整工作示例
- [API 参考](../api/toolsets.md#skillstoolset) - SkillsToolset API
