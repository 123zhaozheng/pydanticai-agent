# Toolsets API

## TodoToolset

任务规划和跟踪工具。

### 工具

| 工具 | 描述 |
|------|-------------|
| `write_todos` | 更新 todo 列表 |

### 工厂

```python
def create_todo_toolset(
    *,
    id: str = "todo",
) -> TodoToolset
```

### Tool: write_todos

```python
async def write_todos(
    ctx: RunContext[DeepAgentDeps],
    todos: list[dict],
) -> str
```

使用新项更新 todo 列表。

**Parameters:**

| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `todos` | `list[dict]` | Todo 项列表 |

每个 todo 项：
```python
{
    "content": str,      # 任务描述
    "status": str,       # "pending", "in_progress", "completed" (待定, 进行中, 已完成)
    "active_form": str,  # 现在进行时形式
}
```

**Returns:** 确认消息。

### System Prompt

```python
def get_todo_system_prompt(deps: DeepAgentDeps) -> str
```

生成显示当前 todo 的动态系统提示词。

---

## FilesystemToolset

文件操作工具。

### 工具

| 工具 | 描述 |
|------|-------------|
| `ls` | 列出目录内容 |
| `read_file` | 读取带有行号的文件 |
| `write_file` | 创建或覆盖文件 |
| `edit_file` | 替换文件中的字符串 |
| `glob` | 按模式查找文件 |
| `grep` | 搜索文件内容 |
| `execute` | 运行 Shell 命令（仅限沙箱） |

### 工厂

```python
def create_filesystem_toolset(
    *,
    id: str = "filesystem",
    include_execute: bool = False,
    require_write_approval: bool = False,
    require_execute_approval: bool = True,
) -> FilesystemToolset
```

### Tool: ls

```python
async def ls(
    ctx: RunContext[DeepAgentDeps],
    path: str = "/",
) -> str
```

列出目录内容。

**Returns:** 格式化的目录列表。

### Tool: read_file

```python
async def read_file(
    ctx: RunContext[DeepAgentDeps],
    path: str,
    offset: int = 0,
    limit: int = 2000,
) -> str
```

读取带有行号的文件内容。

**Parameters:**

| 参数 | 类型 | 默认值 | 描述 |
|-----------|------|---------|-------------|
| `path` | `str` | Required | 文件路径 |
| `offset` | `int` | `0` | 起始行（0 索引） |
| `limit` | `int` | `2000` | 最大行数 |

**Returns:** 带有行号的文件内容。

### Tool: write_file

```python
async def write_file(
    ctx: RunContext[DeepAgentDeps],
    path: str,
    content: str,
) -> str
```

创建或覆盖文件。

**Returns:** 确认或错误消息。

### Tool: edit_file

```python
async def edit_file(
    ctx: RunContext[DeepAgentDeps],
    path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> str
```

替换文件中的字符串。

**Parameters:**

| 参数 | 类型 | 默认值 | 描述 |
|-----------|------|---------|-------------|
| `path` | `str` | Required | 文件路径 |
| `old_string` | `str` | Required | 要替换的字符串 |
| `new_string` | `str` | Required | 替换字符串 |
| `replace_all` | `bool` | `False` | 替换所有出现 |

**Returns:** 带有出现次数的确认。

### Tool: glob

```python
async def glob(
    ctx: RunContext[DeepAgentDeps],
    pattern: str,
    path: str = "/",
) -> str
```

查找匹配 glob 模式的文件。

**Returns:** 匹配文件的列表。

### Tool: grep

```python
async def grep(
    ctx: RunContext[DeepAgentDeps],
    pattern: str,
    path: str | None = None,
    file_glob: str | None = None,
) -> str
```

使用正则表达式搜索文件内容。

**Returns:** 带有上下文的匹配行。

### Tool: execute

```python
async def execute(
    ctx: RunContext[DeepAgentDeps],
    command: str,
    timeout: int = 30,
) -> str
```

执行 Shell 命令（仅限沙箱）。

**Returns:** 命令输出或错误。

---

## SubAgentToolset

任务委托工具。

### 工具

| 工具 | 描述 |
|------|-------------|
| `task` | 为任务生成子智能体 |

### 工厂

```python
def create_subagent_toolset(
    *,
    id: str = "subagents",
    subagents: list[SubAgentConfig] | None = None,
    default_model: str | None = None,
    include_general_purpose: bool = True,
) -> SubAgentToolset
```

### Tool: task

```python
async def task(
    ctx: RunContext[DeepAgentDeps],
    description: str,
    subagent_type: str = "general-purpose",
) -> str
```

生成子智能体来处理任务。

**Parameters:**

| 参数 | 类型 | 默认值 | 描述 |
|-----------|------|---------|-------------|
| `description` | `str` | Required | 任务描述 |
| `subagent_type` | `str` | `"general-purpose"` | 子智能体名称 |

**Returns:** 子智能体的输出。

### SubAgentConfig

```python
class SubAgentConfig(TypedDict):
    name: str                    # 唯一标识符
    description: str             # 何时使用此子智能体
    instructions: str            # 系统提示词
    tools: NotRequired[list]     # 额外工具
    model: NotRequired[str]      # 自定义模型
```

---

## SkillsToolset

模块化能力工具。

### 工具

| 工具 | 描述 |
|------|-------------|
| `list_skills` | 列出可用技能 |
| `load_skill` | 加载技能指令 |
| `read_skill_resource` | 读取技能资源文件 |

### 工厂

```python
def create_skills_toolset(
    *,
    id: str = "skills",
    directories: list[SkillDirectory] | None = None,
    skills: list[Skill] | None = None,
) -> SkillsToolset
```

### Tool: list_skills

```python
async def list_skills(
    ctx: RunContext[DeepAgentDeps],
) -> str
```

列出所有可用技能。

**Returns:** 带有元数据的格式化技能列表。

### Tool: load_skill

```python
async def load_skill(
    ctx: RunContext[DeepAgentDeps],
    skill_name: str,
) -> str
```

加载技能的完整指令。

**Returns:** 完整的技能指令。

### Tool: read_skill_resource

```python
async def read_skill_resource(
    ctx: RunContext[DeepAgentDeps],
    skill_name: str,
    resource_name: str,
) -> str
```

从技能中读取资源文件。

**Returns:** 资源文件内容。

### Type Definitions

#### Skill

```python
class Skill(TypedDict):
    name: str
    description: str
    path: str
    tags: list[str]
    version: str
    author: str
    frontmatter_loaded: bool
    instructions: NotRequired[str]
    resources: NotRequired[list[str]]
```

#### SkillDirectory

```python
class SkillDirectory(TypedDict):
    path: str
    recursive: NotRequired[bool]
```

#### SkillFrontmatter

```python
class SkillFrontmatter(TypedDict):
    name: str
    description: str
    tags: NotRequired[list[str]]
    version: NotRequired[str]
    author: NotRequired[str]
```

---

## Helper Functions

### discover_skills

```python
def discover_skills(
    directories: list[SkillDirectory],
    backend: Any | None = None,
) -> list[Skill]
```

从文件系统目录中发现技能。

### parse_skill_md

```python
def parse_skill_md(content: str) -> tuple[dict[str, Any], str]
```

将 SKILL.md 解析为 frontmatter 和指令。

### load_skill_instructions

```python
def load_skill_instructions(skill_path: str) -> str
```

从技能目录加载完整指令。
