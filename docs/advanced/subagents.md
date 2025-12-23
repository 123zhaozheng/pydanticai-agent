# 子智能体 (Subagents)

子智能体允许主 Agent 将特定任务委托给专注的、上下文隔离的 Agent。

## 为什么使用子智能体？

- **专注的上下文** - 每个子智能体都有清晰、特定的目的
- **隔离** - 新的待办事项列表，无嵌套委托
- **专业化** - 针对特定任务的专家指令
- **减少混淆** - 更少的上下文 = 更好的性能

## 定义子智能体

```python
from pydantic_deep import create_deep_agent, SubAgentConfig

subagents = [
    SubAgentConfig(
        name="code-reviewer",
        description="Reviews code for quality, security, and best practices",
        instructions="""
        You are an expert code reviewer. When reviewing code:

        1. Check for security vulnerabilities
        2. Look for performance issues
        3. Verify proper error handling
        4. Assess code readability

        Provide specific, actionable feedback.
        """,
    ),
    SubAgentConfig(
        name="test-writer",
        description="Generates pytest test cases for Python code",
        instructions="""
        You are a testing expert. Generate comprehensive tests:

        - Unit tests for individual functions
        - Edge cases and error conditions
        - Use pytest fixtures and parametrize
        - Include docstrings explaining each test
        """,
    ),
    SubAgentConfig(
        name="doc-writer",
        description="Writes documentation and docstrings",
        instructions="""
        You are a technical writer. Create clear documentation:

        - Use Google-style docstrings
        - Include examples in docstrings
        - Write clear README sections
        - Document edge cases and gotchas
        """,
    ),
]

agent = create_deep_agent(subagents=subagents)
```

## Task 工具如何工作

主 Agent 可以调用 `task` 工具：

```python
task(
    description="Review the authentication module for security issues",
    subagent_type="code-reviewer",
)
```

这将会：

1. 使用子智能体的指令创建一个新的 Agent
2. 克隆依赖项：
   - 相同的后端（共享文件）
   - 空待办事项列表（隔离规划）
   - 无嵌套子智能体
3. 使用描述作为提示运行子智能体
4. 将子智能体的输出返回给主 Agent

## 上下文隔离

子智能体接收隔离的上下文：

```python
def clone_for_subagent(self) -> DeepAgentDeps:
    """Create deps for a subagent."""
    return DeepAgentDeps(
        backend=self.backend,      # 共享 - 可以读/写相同的文件
        files=self.files,          # 共享引用
        todos=[],                  # 新鲜 - 子智能体独立规划
        subagents={},              # 空 - 无嵌套委托
    )
```

这防止了：

- 累积的 todo 导致的上下文膨胀
- 嵌套委托导致的无限递归
- 混合职责导致的混淆

## 通用子智能体

默认情况下，包含一个通用子智能体：

```python
agent = create_deep_agent(
    include_general_purpose_subagent=True,  # 默认: True
)
```

这允许委托没有专门子智能体的任务：

```python
task(
    description="Research the best Python logging libraries",
    subagent_type="general-purpose",
)
```

如果您只想要特定的子智能体，请禁用：

```python
agent = create_deep_agent(
    subagents=subagents,
    include_general_purpose_subagent=False,
)
```

## 每个子智能体使用自定义模型

为不同的子智能体使用不同的模型：

```python
subagents = [
    SubAgentConfig(
        name="code-reviewer",
        description="Reviews code (uses powerful model)",
        instructions="...",
        model="openai:gpt-4.1",
    ),
    SubAgentConfig(
        name="simple-formatter",
        description="Formats code (uses fast model)",
        instructions="...",
        model="anthropic:claude-3-haiku-20240307",
    ),
]
```

## 每个子智能体使用自定义工具

子智能体可以拥有自定义工具：

```python
async def run_tests(ctx, path: str) -> str:
    """Run pytest on the given path."""
    ...

subagents = [
    SubAgentConfig(
        name="test-writer",
        description="Writes and runs tests",
        instructions="...",
        tools=[run_tests],
    ),
]
```

## 示例：代码审查流水线

```python
import asyncio
from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend, SubAgentConfig

async def main():
    subagents = [
        SubAgentConfig(
            name="code-reviewer",
            description="Reviews code for issues",
            instructions="""
            Review code thoroughly. Check for:
            - Security issues
            - Performance problems
            - Error handling
            - Code style

            Format your review as markdown with sections.
            """,
        ),
        SubAgentConfig(
            name="test-writer",
            description="Generates pytest tests",
            instructions="""
            Write comprehensive pytest tests.
            Cover happy paths, edge cases, and error conditions.
            Use fixtures and parametrize decorators.
            """,
        ),
    ]

    agent = create_deep_agent(subagents=subagents)
    deps = DeepAgentDeps(backend=StateBackend())

    # 创建一些要审查的代码
    deps.backend.write("/src/auth.py", '''
def authenticate(username, password):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    user = db.execute(query)
    if user and user.password == password:
        return True
    return False
    ''')

    result = await agent.run(
        """
        1. Review /src/auth.py for security issues
        2. Generate tests for the authenticate function
        3. Report findings
        """,
        deps=deps,
    )

    print(result.output)

asyncio.run(main())
```

## 最佳实践

### 1. 清晰的描述

描述有助于主 Agent 进行选择：

```python
# Good - clear when to use
SubAgentConfig(
    name="security-reviewer",
    description="Reviews code specifically for security vulnerabilities like SQL injection, XSS, and authentication issues",
    ...
)

# Bad - too vague
SubAgentConfig(
    name="reviewer",
    description="Reviews code",
    ...
)
```

### 2. 专注的指令

保持子智能体指令专注：

```python
# Good - specific focus
instructions="""
You are a security expert. Focus ONLY on:
- SQL injection
- XSS vulnerabilities
- Authentication issues
- Authorization flaws

Do NOT comment on code style or performance.
"""

# Bad - too broad
instructions="Review the code and check everything."
```

### 3. 输出格式

指定预期的输出格式：

```python
instructions="""
...

Output your review in this format:
## Summary
[1-2 sentence overview]

## Critical Issues
- [Issue 1]
- [Issue 2]

## Recommendations
- [Recommendation 1]
"""
```

### 4. 限制子智能体数量

使用 3-5 个专注的子智能体，而不是许多通用的子智能体：

```python
# Good - focused experts
subagents = [
    SubAgentConfig(name="security-reviewer", ...),
    SubAgentConfig(name="test-writer", ...),
    SubAgentConfig(name="doc-writer", ...),
]

# Bad - too many similar agents
subagents = [
    SubAgentConfig(name="python-reviewer", ...),
    SubAgentConfig(name="javascript-reviewer", ...),
    SubAgentConfig(name="typescript-reviewer", ...),
    SubAgentConfig(name="go-reviewer", ...),
    # ... 10 more language-specific reviewers
]
```

## 下一步

- [流式传输](streaming.md) - 监控子智能体进度
- [示例](../examples/index.md) - 更多示例
- [API 参考](../api/toolsets.md) - SubAgentToolset API
