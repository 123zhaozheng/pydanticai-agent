# 技能示例

此示例演示用于模块化能力扩展的技能系统。

## 源代码

:material-file-code: `examples/skills_usage.py`

## 概览

技能是模块化包，它们：

- 扩展 Agent 能力
- 使用渐进式披露（frontmatter → 完整指令）
- 包含可选资源文件

## 示例技能

该示例在 `examples/skills/` 中包含两个技能：

### 代码审查技能

```
examples/skills/code-review/
├── SKILL.md
└── example_review.md
```

**SKILL.md:**
```yaml
---
name: code-review
description: Review Python code for quality, security, and best practices
version: 1.0.0
tags:
  - code
  - review
  - python
  - quality
author: pydantic-deep
---

# Code Review Skill

审查代码时，请遵循以下准则：

## Review Process
1. Read the entire file before making comments
2. Check for security issues first
3. Review code structure and patterns
...
```

### 测试生成器技能

```
examples/skills/test-generator/
└── SKILL.md
```

**SKILL.md:**
```yaml
---
name: test-generator
description: Generate pytest test cases for Python functions and classes
version: 1.0.0
tags:
  - testing
  - pytest
  - python
---

# Test Generator Skill

Generate comprehensive pytest tests...
```

## 完整示例

```python
"""Skills usage example."""

import asyncio
from pathlib import Path

from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend


SKILLS_DIR = Path(__file__).parent / "skills"


async def main():
    # 创建带有技能的 Agent
    agent = create_deep_agent(
        model="openai:gpt-4.1",
        instructions="""
        You are a coding assistant with specialized skills.

        When asked to review code or generate tests:
        1. First check available skills with list_skills
        2. Load the relevant skill with load_skill
        3. Follow the skill's guidelines

        Always use skill instructions for specialized tasks.
        """,
        skill_directories=[
            {"path": str(SKILLS_DIR), "recursive": True},
        ],
    )

    deps = DeepAgentDeps(backend=StateBackend())

    # 创建一些代码进行审查
    deps.backend.write(
        "/code/example.py",
        '''def calculate_total(items):
    total = 0
    for item in items:
        total = total + item["price"] * item["quantity"]
    return total

def get_user_data(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return db.execute(query)
''',
    )

    # 要求 Agent 使用技能
    result = await agent.run(
        """
        1. List your available skills
        2. Load the code-review skill
        3. Review /code/example.py following the skill's guidelines
        """,
        deps=deps,
    )

    print(result.output)


asyncio.run(main())
```

## 无需 API 密钥运行

该示例支持无需 API 密钥运行以进行演示：

```bash
# 列出发现的技能
uv run python examples/skills_usage.py --discover

# 加载技能指令
uv run python examples/skills_usage.py --load
```

### 发现输出

```
Discovering skills from: /path/to/examples/skills

Skill: test-generator
  Description: Generate pytest test cases for Python functions and classes
  Version: 1.0.0
  Tags: testing, pytest, python
  Path: /path/to/examples/skills/test-generator

Skill: code-review
  Description: Review Python code for quality, security, and best practices
  Version: 1.0.0
  Tags: code, review, python, quality
  Path: /path/to/examples/skills/code-review
  Resources: example_review.md
```

## 技能工具

### list_skills

返回所有可用技能及其元数据：

```python
# Agent output:
Available Skills:

**code-review** (v1.0.0)
  Description: Review Python code for quality, security, and best practices
  Tags: code, review, python, quality
  Path: /path/to/skill (resources: example_review.md)

**test-generator** (v1.0.0)
  Description: Generate pytest test cases for Python functions and classes
  Tags: testing, pytest, python
  Path: /path/to/skill
```

### load_skill

加载特定技能的完整指令：

```python
# Agent calls: load_skill(skill_name="code-review")
# Returns complete SKILL.md content with detailed instructions
```

### read_skill_resource

从技能中读取额外文件：

```python
# Agent calls: read_skill_resource(
#     skill_name="code-review",
#     resource_name="example_review.md"
# )
# Returns the resource file content
```

## 创建你自己的技能

### 1. 创建目录

```bash
mkdir -p ~/.pydantic-deep/skills/my-skill
```

### 2. 编写 SKILL.md

```markdown
---
name: my-skill
description: What this skill does
version: 1.0.0
tags:
  - tag1
  - tag2
author: your-name
---

# My Skill

给 Agent 的详细指令...

## When to Use

Use this skill when...

## Process

1. Step one
2. Step two
3. Step three

## Output Format

Provide output in this format:
...
```

### 3. 添加资源（可选）

```bash
# 模板、示例、清单等。
echo "# Template" > ~/.pydantic-deep/skills/my-skill/template.md
```

### 4. 配置 Agent

```python
agent = create_deep_agent(
    skill_directories=[
        {"path": "~/.pydantic-deep/skills", "recursive": True},
    ],
)
```

## 最佳实践

1. **清晰的描述** - 帮助 Agent 选择正确的技能
2. **专注的技能** - 一个技能，一个目的
3. **可操作的指令** - 准确告诉 Agent 做什么
4. **包含示例** - 显示预期的输出格式
5. **版本化你的技能** - 随着时间的推移跟踪更改

## 下一步

- [概念：技能](../concepts/skills.md) - 深入研究
- [Docker 沙箱](docker-sandbox.md) - 隔离执行
- [API 参考](../api/toolsets.md) - SkillsToolset API
