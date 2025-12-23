# Agent API

## create_deep_agent

::: pydantic_deep.agent.create_deep_agent
    options:
      show_source: false

### 签名

```python
def create_deep_agent(
    model: str | None = None,
    instructions: str | None = None,
    tools: Sequence[Tool[DeepAgentDeps] | Any] | None = None,
    toolsets: Sequence[AbstractToolset[DeepAgentDeps]] | None = None,
    subagents: list[SubAgentConfig] | None = None,
    skills: list[Skill] | None = None,
    skill_directories: list[SkillDirectory] | None = None,
    backend: BackendProtocol | None = None,
    include_todo: bool = True,
    include_filesystem: bool = True,
    include_subagents: bool = True,
    include_skills: bool = True,
    include_general_purpose_subagent: bool = True,
    interrupt_on: dict[str, bool] | None = None,
    output_type: OutputSpec[OutputDataT] | None = None,
    history_processors: Sequence[HistoryProcessor[DeepAgentDeps]] | None = None,
    **agent_kwargs: Any,
) -> Agent[DeepAgentDeps, OutputDataT] | Agent[DeepAgentDeps, str]
```

### 参数

| 参数 | 类型 | 默认值 | 描述 |
|-----------|------|---------|-------------|
| `model` | `str \| None` | `"openai:gpt-4.1"` | LLM 模型标识符 |
| `instructions` | `str \| None` | Default instructions | Agent 的系统提示词 |
| `tools` | `Sequence[Tool \| Any] \| None` | `None` | 额外的自定义工具 |
| `toolsets` | `Sequence[AbstractToolset] \| None` | `None` | 额外的工具集 |
| `subagents` | `list[SubAgentConfig] \| None` | `None` | 子智能体配置 |
| `skills` | `list[Skill] \| None` | `None` | 预加载的技能 |
| `skill_directories` | `list[SkillDirectory] \| None` | `None` | 发现技能的目录 |
| `backend` | `BackendProtocol \| None` | `StateBackend()` | 文件存储后端 |
| `include_todo` | `bool` | `True` | 包含 TodoToolset |
| `include_filesystem` | `bool` | `True` | 包含 FilesystemToolset |
| `include_subagents` | `bool` | `True` | 包含 SubAgentToolset |
| `include_skills` | `bool` | `True` | 包含 SkillsToolset |
| `include_general_purpose_subagent` | `bool` | `True` | 包含通用子智能体 |
| `interrupt_on` | `dict[str, bool] \| None` | `None` | 需要审批的工具 |
| `output_type` | `OutputSpec \| None` | `None` | 用于结构化输出的 Pydantic 模型 |
| `history_processors` | `Sequence[HistoryProcessor] \| None` | `None` | 历史记录处理器（例如：摘要） |
| `**agent_kwargs` | `Any` | - | 其他 Agent 构造函数参数 |

### 返回值

`Agent[DeepAgentDeps, str]` 或 `Agent[DeepAgentDeps, OutputDataT]` - 配置好的 Pydantic AI Agent。

当提供 `output_type` 时，返回一个以输出模型为类型的 Agent。

### 示例

```python
from pydantic_deep import create_deep_agent, SubAgentConfig

agent = create_deep_agent(
    model="openai:gpt-4.1",
    instructions="You are a coding assistant.",
    subagents=[
        SubAgentConfig(
            name="reviewer",
            description="Reviews code",
            instructions="Review code for issues.",
        ),
    ],
    skill_directories=[
        {"path": "~/.pydantic-deep/skills", "recursive": True},
    ],
    interrupt_on={"execute": True},
)
```

---

## create_default_deps

::: pydantic_deep.agent.create_default_deps
    options:
      show_source: false

### 签名

```python
def create_default_deps(
    backend: BackendProtocol | None = None,
) -> DeepAgentDeps
```

### 参数

| 参数 | 类型 | 默认值 | 描述 |
|-----------|------|---------|-------------|
| `backend` | `BackendProtocol \| None` | `StateBackend()` | 文件存储后端 |

### 返回值

`DeepAgentDeps` - 配置好的依赖项实例。

### 示例

```python
from pydantic_deep import create_default_deps, FilesystemBackend

# 使用默认 StateBackend
deps = create_default_deps()

# 使用自定义后端
deps = create_default_deps(backend=FilesystemBackend("/workspace"))
```

---

## DeepAgentDeps

::: pydantic_deep.deps.DeepAgentDeps
    options:
      show_source: false

### 定义

```python
@dataclass
class DeepAgentDeps:
    backend: BackendProtocol = field(default_factory=StateBackend)
    files: dict[str, FileData] = field(default_factory=dict)
    todos: list[Todo] = field(default_factory=list)
    subagents: dict[str, Any] = field(default_factory=dict)
```

### 属性

| 属性 | 类型 | 描述 |
|-----------|------|-------------|
| `backend` | `BackendProtocol` | 文件存储后端 |
| `files` | `dict[str, FileData]` | 内存文件缓存 |
| `todos` | `list[Todo]` | 任务列表 |
| `subagents` | `dict[str, Any]` | 预配置的子智能体实例 |

### 方法

#### get_todo_prompt

```python
def get_todo_prompt(self) -> str
```

为当前 todo 生成系统提示部分。

#### get_files_summary

```python
def get_files_summary(self) -> str
```

生成内存中文件的摘要。

#### get_subagents_summary

```python
def get_subagents_summary(self) -> str
```

生成可用子智能体的摘要。

#### clone_for_subagent

```python
def clone_for_subagent(self) -> DeepAgentDeps
```

为子智能体创建隔离的依赖项。

- 相同的后端（共享）
- 空的 todo（隔离）
- 空的子智能体（无嵌套委托）
- 相同的文件（共享引用）

### 示例

```python
from pydantic_deep import DeepAgentDeps, StateBackend, Todo

deps = DeepAgentDeps(
    backend=StateBackend(),
    todos=[
        Todo(
            content="Review code",
            status="pending",
            active_form="Reviewing code",
        ),
    ],
)

# Access todo prompt
print(deps.get_todo_prompt())

# Clone for subagent
subagent_deps = deps.clone_for_subagent()
assert subagent_deps.todos == []  # Isolated
assert subagent_deps.backend is deps.backend  # Shared
```
