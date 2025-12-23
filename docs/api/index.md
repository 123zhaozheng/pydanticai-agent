# API 参考

pydantic-deep 的完整 API 文档。

## 模块

| 模块 | 描述 |
|--------|-------------|
| [`pydantic_deep.agent`](agent.md) | Agent 工厂和配置 |
| [`pydantic_deep.backends`](backends.md) | 存储后端 |
| [`pydantic_deep.toolsets`](toolsets.md) | 工具集合 |
| [`pydantic_deep.processors`](processors.md) | 历史记录处理器 |
| [`pydantic_deep.types`](types.md) | 类型定义 |

## 快速参考

### 主要入口点

```python
from pydantic_deep import (
    # Agent
    create_deep_agent,
    create_default_deps,
    DeepAgentDeps,

    # 后端
    BackendProtocol,
    SandboxProtocol,
    StateBackend,
    FilesystemBackend,
    CompositeBackend,
    BaseSandbox,
    DockerSandbox,

    # 工具集
    TodoToolset,
    FilesystemToolset,
    SubAgentToolset,
    SkillsToolset,

    # 处理器
    SummarizationProcessor,
    create_summarization_processor,

    # 类型
    FileData,
    FileInfo,
    WriteResult,
    EditResult,
    ExecuteResponse,
    GrepMatch,
    Todo,
    SubAgentConfig,
    CompiledSubAgent,
    Skill,
    SkillDirectory,
    SkillFrontmatter,
    ResponseFormat,
)
```

### 创建 Agent

```python
agent = create_deep_agent(
    model="openai:gpt-4.1",
    instructions="You are a helpful assistant.",
    include_todo=True,
    include_filesystem=True,
    include_subagents=True,
    include_skills=True,
    subagents=[...],
    skills=[...],
    skill_directories=[...],
    interrupt_on={"execute": True},
)
```

### 创建依赖项

```python
deps = DeepAgentDeps(
    backend=StateBackend(),
    todos=[],
    subagents={},
)

# 或者使用辅助函数
deps = create_default_deps()
```

### 运行

```python
# 基本运行
result = await agent.run(prompt, deps=deps)

# 带历史记录
result = await agent.run(
    prompt,
    deps=deps,
    message_history=previous_result.all_messages(),
)

# 流式传输
async with agent.iter(prompt, deps=deps) as run:
    async for node in run:
        ...
    result = run.result
```

## 类型注解

pydantic-deep 是完全类型化的。主 Agent 类型是：

```python
Agent[DeepAgentDeps, str]
```

其中：

- `DeepAgentDeps` - 依赖项类型
- `str` - 输出类型（Agent 返回字符串）

## 协议

### BackendProtocol

```python
class BackendProtocol(Protocol):
    def ls_info(self, path: str) -> list[FileInfo]: ...
    def read(self, path: str, offset: int = 0, limit: int = 2000) -> str: ...
    def write(self, path: str, content: str) -> WriteResult: ...
    def edit(self, path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult: ...
    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]: ...
    def grep_raw(self, pattern: str, path: str | None = None, glob: str | None = None) -> list[GrepMatch] | str: ...
```

### SandboxProtocol

```python
class SandboxProtocol(BackendProtocol, Protocol):
    def execute(self, command: str, timeout: int | None = None) -> ExecuteResponse: ...
    @property
    def id(self) -> str: ...
```

## 异常

pydantic-deep 使用标准 Python 异常：

| 异常 | 何时抛出 |
|-----------|-------------|
| `ValueError` | 无效参数（错误路径，缺少文件） |
| `FileNotFoundError` | 文件不存在 |
| `PermissionError` | 路径遍历尝试 |
| `TimeoutError` | 执行超时 |

## 下一步

- [Agent API](agent.md) - 详细的 Agent 文档
- [Backends API](backends.md) - 存储后端详情
- [Toolsets API](toolsets.md) - 工具集合详情
