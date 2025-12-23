# 工具集 (Toolsets)

工具集是扩展 Agent 能力的工具集合。pydantic-deep 包含四个内置工具集。

## 内置工具集

### TodoToolset

任务规划和跟踪。

| 工具 | 描述 |
|------|-------------|
| `write_todos` | 使用任务和状态更新 todo 列表 |

```python
# Agent can call:
write_todos(todos=[
    {"content": "Create module", "status": "in_progress", "active_form": "Creating module"},
    {"content": "Write tests", "status": "pending", "active_form": "Writing tests"},
])
```

**Todo 状态值：**

- `pending` - 尚未开始
- `in_progress` - 目前正在处理
- `completed` - 完成

### FilesystemToolset

使用配置的后端进行文件操作。

| 工具 | 描述 |
|------|-------------|
| `ls` | 列出目录内容 |
| `read_file` | 读取带有行号的文件 |
| `write_file` | 创建或覆盖文件 |
| `edit_file` | 替换文件中的字符串 |
| `glob` | 按模式查找文件 |
| `grep` | 搜索文件内容 |
| `execute` | 运行 Shell 命令（仅限沙箱） |

```python
# Agent can call:
ls(path="/src")
read_file(path="/src/app.py")
write_file(path="/src/new.py", content="print('hello')")
edit_file(path="/src/app.py", old_string="old", new_string="new")
glob(pattern="**/*.py", path="/src")
grep(pattern="def main", path="/src")
execute(command="python test.py", timeout=30)  # 如果是沙箱后端
```

### SubAgentToolset

将任务委托给专业子智能体。

| 工具 | 描述 |
|------|-------------|
| `task` | 生成子智能体来处理任务 |

```python
# Agent can call:
task(
    description="Review the authentication module for security issues",
    subagent_type="code-reviewer",
)
```

**内置子智能体类型：**

- `general-purpose` - 用于任何任务的默认 Agent（如已启用）
- 来自 `subagents` 配置的自定义类型

### SkillsToolset

模块化能力包。

| 工具 | 描述 |
|------|-------------|
| `list_skills` | 列出带有元数据的可用技能 |
| `load_skill` | 加载技能的完整指令 |
| `read_skill_resource` | 从技能中读取额外文件 |

```python
# Agent can call:
list_skills()
load_skill(skill_name="code-review")
read_skill_resource(skill_name="code-review", resource_name="template.md")
```

## 启用/禁用工具集

```python
agent = create_deep_agent(
    include_todo=True,        # TodoToolset
    include_filesystem=True,  # FilesystemToolset
    include_subagents=True,   # SubAgentToolset
    include_skills=True,      # SkillsToolset
)
```

## 自定义工具集

使用 `FunctionToolset` 创建自定义工具集：

```python
from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset
from pydantic_deep import DeepAgentDeps

# 创建工具集
my_toolset = FunctionToolset[DeepAgentDeps](id="my-tools")

@my_toolset.tool
async def fetch_data(
    ctx: RunContext[DeepAgentDeps],
    url: str,
) -> str:
    """Fetch data from a URL.

    Args:
        url: The URL to fetch.

    Returns:
        The response content.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

@my_toolset.tool
async def analyze_sentiment(
    ctx: RunContext[DeepAgentDeps],
    text: str,
) -> str:
    """Analyze sentiment of text.

    Args:
        text: Text to analyze.

    Returns:
        Sentiment analysis result.
    """
    # 你的情感分析逻辑
    return "Positive"

# 添加到 Agent
agent = create_deep_agent(toolsets=[my_toolset])
```

## 工具文档

工具使用文档字符串供 LLM 理解：

```python
@my_toolset.tool
async def process_data(
    ctx: RunContext[DeepAgentDeps],
    data: str,
    format: str = "json",
) -> str:
    """Process and transform data.

    This tool takes raw data and processes it according to the
    specified format. Supports JSON, CSV, and XML formats.

    Args:
        data: The raw data to process.
        format: Output format - 'json', 'csv', or 'xml'. Defaults to 'json'.

    Returns:
        Processed data in the requested format.

    Example:
        >>> process_data(data="name,age\\nAlice,30", format="json")
        '[{"name": "Alice", "age": "30"}]'
    """
    ...
```

## 审批要求

要求对敏感工具进行人工审批：

```python
from pydantic_ai.common_tools.dangerous import DangerousCapability

@my_toolset.tool
async def delete_files(
    ctx: RunContext[DeepAgentDeps],
    pattern: str,
) -> str:
    """Delete files matching pattern."""
    ...

# 标记为危险
delete_files.dangerous = DangerousCapability.FILESYSTEM
```

或者通过 `interrupt_on` 进行配置：

```python
agent = create_deep_agent(
    interrupt_on={
        "delete_files": True,
        "execute": True,
    }
)
```

## 动态系统提示词

工具集可以贡献动态系统提示词：

```python
def get_my_system_prompt(deps: DeepAgentDeps) -> str:
    """Generate system prompt based on current state."""
    if deps.some_condition:
        return "## Additional Context\nSome relevant information..."
    return ""
```

Agent 工厂使用这些来构建动态指令。

## 工具返回类型

工具可以返回各种类型：

```python
# 字符串 - 最常见
async def my_tool(ctx: RunContext[DeepAgentDeps]) -> str:
    return "Result text"

# 结构化数据（转换为字符串）
async def my_tool(ctx: RunContext[DeepAgentDeps]) -> dict:
    return {"status": "success", "count": 42}

# 列表
async def my_tool(ctx: RunContext[DeepAgentDeps]) -> list[str]:
    return ["item1", "item2", "item3"]
```

## 最佳实践

### 1. 清晰的文档字符串

编写详细的文档字符串 - 它们是 LLM 的文档。

### 2. 类型提示

为所有参数使用类型提示：

```python
async def process(
    ctx: RunContext[DeepAgentDeps],
    items: list[str],          # List of strings
    count: int = 10,           # Integer with default
    enabled: bool = True,      # Boolean
) -> str:
    ...
```

### 3. 错误处理

返回信息丰富的错误：

```python
async def read_config(
    ctx: RunContext[DeepAgentDeps],
    name: str,
) -> str:
    try:
        return load_config(name)
    except FileNotFoundError:
        return f"Error: Config '{name}' not found. Available: {list_configs()}"
```

### 4. 幂等操作

尽可能使工具幂等：

```python
async def ensure_directory(
    ctx: RunContext[DeepAgentDeps],
    path: str,
) -> str:
    """Ensure directory exists (creates if needed)."""
    if directory_exists(path):
        return f"Directory {path} already exists"
    create_directory(path)
    return f"Created directory {path}"
```

## 下一步

- [技能](skills.md) - 模块化能力包
- [API 参考](../api/toolsets.md) - 完整的工具集 API
- [自定义工具示例](../examples/basic-usage.md) - 更多示例
