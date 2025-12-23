# Agent (智能体)

`create_deep_agent()` 函数是创建深度智能体的主要入口点。

## 基本用法

```python
from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend

# 使用默认值创建 Agent
agent = create_deep_agent()

# 使用依赖项运行
deps = DeepAgentDeps(backend=StateBackend())
result = await agent.run("Hello!", deps=deps)
```

## 配置选项

### 模型选择

```python
# Anthropic (默认)
agent = create_deep_agent(model="openai:gpt-4.1")

# OpenAI
agent = create_deep_agent(model="openai:gpt-4")

# 用于测试（无 API 调用）
from pydantic_ai.models.test import TestModel
agent = create_deep_agent(model=TestModel())
```

### 自定义指令

```python
agent = create_deep_agent(
    instructions="""
    You are a Python expert specializing in data science.

    When writing code:
    - Use type hints
    - Include docstrings
    - Prefer pandas for data manipulation
    """
)
```

### 启用/禁用功能

```python
agent = create_deep_agent(
    include_todo=True,        # 规划工具 (默认: True)
    include_filesystem=True,  # 文件操作 (默认: True)
    include_subagents=True,   # 任务委托 (默认: True)
    include_skills=True,      # 技能包 (默认: True)
)
```

### 人机回环

要求对敏感操作进行审批：

```python
agent = create_deep_agent(
    interrupt_on={
        "execute": True,      # 要求审批命令执行
        "write_file": True,   # 要求审批文件写入
        "edit_file": True,    # 要求审批文件编辑
    }
)
```

### 结构化输出

使用 Pydantic 模型获取类型安全的响应：

```python
from pydantic import BaseModel

class TaskAnalysis(BaseModel):
    summary: str
    priority: str
    estimated_hours: float

agent = create_deep_agent(output_type=TaskAnalysis)

result = await agent.run("Analyze this task: implement auth", deps=deps)
print(result.output.priority)  # 类型安全访问
```

更多详情请参阅 [结构化输出](../advanced/structured-output.md)。

### 上下文管理

自动总结长对话：

```python
from pydantic_deep.processors import create_summarization_processor

processor = create_summarization_processor(
    trigger=("tokens", 100000),
    keep=("messages", 20),
)

agent = create_deep_agent(history_processors=[processor])
```

更多详情请参阅 [历史记录处理器](../advanced/processors.md)。

## 依赖项

`DeepAgentDeps` 类保存所有运行时状态：

```python
from dataclasses import dataclass
from pydantic_deep import BackendProtocol, Todo, UploadedFile

@dataclass
class DeepAgentDeps:
    backend: BackendProtocol  # 文件存储
    files: dict[str, FileData]  # 文件缓存
    todos: list[Todo]  # 任务列表
    subagents: dict[str, Any]  # 预配置的 Agent
    uploads: dict[str, UploadedFile]  # 上传文件的元数据
```

### 创建依赖项

```python
# 简单 - 内存存储
deps = DeepAgentDeps(backend=StateBackend())

# 使用文件系统存储
deps = DeepAgentDeps(backend=FilesystemBackend("/workspace"))

# 使用初始 todo
from pydantic_deep import Todo
deps = DeepAgentDeps(
    backend=StateBackend(),
    todos=[
        Todo(content="Review code", status="pending", active_form="Reviewing code"),
    ]
)
```

### Uploading Files

上传文件供 Agent 处理：

```python
# 上传文件
deps.upload_file("data.csv", csv_bytes)
# 文件存储于 /uploads/data.csv

# 自定义上传目录
deps.upload_file("config.json", config_bytes, upload_dir="/configs")
# 文件存储于 /configs/config.json

# 检查上传
for path, info in deps.uploads.items():
    print(f"{path}: {info['size']} bytes, {info['line_count']} lines")
```

或者使用 `run_with_files()` 辅助函数：

```python
from pydantic_deep import run_with_files

result = await run_with_files(
    agent,
    "Analyze this data",
    deps,
    files=[("data.csv", csv_bytes)],
)
```

更多详情请参阅 [文件上传](../examples/file-uploads.md)。

## 运行 Agent

### 基本运行

```python
result = await agent.run("Create a calculator module", deps=deps)
print(result.output)  # Agent 的文本响应
```

### 流式传输

```python
from pydantic_ai._agent_graph import CallToolsNode

async with agent.iter("Create a calculator", deps=deps) as run:
    async for node in run:
        if isinstance(node, CallToolsNode):
            # 从响应中获取工具调用
            for part in node.model_response.parts:
                if hasattr(part, 'tool_name'):
                    print(f"Calling: {part.tool_name}")

    result = run.result
```

### 继续对话

```python
# 首次交互
result1 = await agent.run("Create a file", deps=deps)

# 使用历史记录继续
result2 = await agent.run(
    "Now modify it",
    deps=deps,
    message_history=result1.all_messages(),
)
```

## 添加自定义工具

### 函数工具

```python
from pydantic_ai import RunContext

async def get_weather(
    ctx: RunContext[DeepAgentDeps],
    city: str,
) -> str:
    """Get current weather for a city.

    Args:
        city: Name of the city.

    Returns:
        Weather description.
    """
    return f"Weather in {city}: Sunny, 22°C"

agent = create_deep_agent(tools=[get_weather])
```

### 在工具中访问依赖项

```python
async def save_report(
    ctx: RunContext[DeepAgentDeps],
    content: str,
) -> str:
    """Save a report to the filesystem."""
    # 通过依赖项访问后端
    result = ctx.deps.backend.write("/reports/latest.md", content)
    return f"Saved to {result.path}"
```

## 子智能体配置

预配置专业子智能体：

```python
from pydantic_deep import SubAgentConfig

subagents = [
    SubAgentConfig(
        name="code-reviewer",
        description="Reviews code for quality and security issues",
        instructions="""
        You are an expert code reviewer. Focus on:
        - Security vulnerabilities
        - Performance issues
        - Code style
        """,
    ),
    SubAgentConfig(
        name="test-writer",
        description="Generates pytest test cases",
        instructions="Generate comprehensive pytest tests...",
    ),
]

agent = create_deep_agent(subagents=subagents)
```

主 Agent 随后可以委托：

```python
# Agent can call: task(description="Review the calculator module", subagent_type="code-reviewer")
```

## 技能配置

从目录加载技能：

```python
agent = create_deep_agent(
    skill_directories=[
        {"path": "~/.pydantic-deep/skills", "recursive": True},
        {"path": "./project-skills", "recursive": False},
    ]
)
```

或者直接提供技能：

```python
skills = [
    {
        "name": "code-review",
        "description": "Review code for quality",
        "path": "/path/to/skill",
        "tags": ["code", "review"],
        "version": "1.0.0",
        "author": "",
        "frontmatter_loaded": True,
    }
]

agent = create_deep_agent(skills=skills)
```

## 使用统计

```python
result = await agent.run("Create a module", deps=deps)

usage = result.usage()
print(f"Input tokens: {usage.input_tokens}")
print(f"Output tokens: {usage.output_tokens}")
print(f"Total requests: {usage.requests}")
```

## 错误处理

```python
try:
    result = await agent.run(prompt, deps=deps)
except Exception as e:
    print(f"Agent error: {e}")
```

## 下一步

- [后端](backends.md) - 存储选项
- [工具集](toolsets.md) - 可用工具
- [技能](skills.md) - 模块化能力
