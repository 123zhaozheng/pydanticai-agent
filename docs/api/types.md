# Types API

pydantic-deep 中使用的所有类型定义。

## 文件类型

### FileData

文件内容的存储格式。

```python
class FileData(TypedDict):
    content: list[str]  # 文件行
    created_at: str     # ISO 8601 时间戳
    modified_at: str    # ISO 8601 时间戳
```

### FileInfo

列表的文件元数据。

```python
class FileInfo(TypedDict):
    name: str           # 文件或目录名称
    path: str           # 完整路径
    is_dir: bool        # 如果是目录则为 True
    size: int | None    # 文件大小（字节）（目录为 None）
```

---

## 操作结果

### WriteResult

写入操作的结果。

```python
@dataclass
class WriteResult:
    path: str | None = None    # 写入文件的路径
    error: str | None = None   # 如果失败的错误消息
```

### EditResult

编辑操作的结果。

```python
@dataclass
class EditResult:
    path: str | None = None      # 编辑文件的路径
    error: str | None = None     # 如果失败的错误消息
    occurrences: int | None = None  # 进行的替换次数
```

### ExecuteResponse

命令执行的结果。

```python
@dataclass
class ExecuteResponse:
    output: str                 # stdout + stderr
    exit_code: int | None = None  # 进程退出码
    truncated: bool = False     # 如果输出被截断则为 True
```

### GrepMatch

单个 grep 匹配结果。

```python
class GrepMatch(TypedDict):
    path: str         # 文件路径
    line_number: int  # 行号（1 索引）
    line: str         # 匹配的行内容
```

---

## Todo 类型

### Todo

规划的任务项。

```python
class Todo(BaseModel):
    content: str                                    # 任务描述
    status: Literal["pending", "in_progress", "completed"]
    active_form: str  # 现在进行时形式 (例如 "Implementing feature")
```

**状态值：**

| 状态 | 描述 |
|--------|-------------|
| `pending` | 尚未开始 |
| `in_progress` | 目前正在处理 |
| `completed` | 完成 |

---

## 子智能体类型

### SubAgentConfig

子智能体的配置。

```python
class SubAgentConfig(TypedDict):
    name: str                      # 唯一标识符
    description: str               # 何时使用此子智能体
    instructions: str              # 子智能体的系统提示词
    tools: NotRequired[list]       # 额外工具
    model: NotRequired[str]        # 自定义模型（覆盖默认值）
```

### CompiledSubAgent

准备使用的预编译子智能体。

```python
class CompiledSubAgent(TypedDict):
    name: str
    description: str
    agent: NotRequired[object]  # Agent 实例
```

---

## 技能类型

### Skill

完整的技能定义。

```python
class Skill(TypedDict):
    name: str                            # 唯一标识符
    description: str                     # 简要描述
    path: str                            # 技能目录的路径
    tags: list[str]                      # 分类标签
    version: str                         # 语义版本
    author: str                          # 技能作者
    frontmatter_loaded: bool             # 如果仅加载了 frontmatter 则为 True
    instructions: NotRequired[str]       # 完整指令（按需加载）
    resources: NotRequired[list[str]]    # 技能目录中的额外文件
```

### SkillDirectory

技能发现的配置。

```python
class SkillDirectory(TypedDict):
    path: str                           # 技能目录的路径
    recursive: NotRequired[bool]        # 递归搜索（默认：True）
```

### SkillFrontmatter

来自 SKILL.md 的 YAML frontmatter。

```python
class SkillFrontmatter(TypedDict):
    name: str
    description: str
    tags: NotRequired[list[str]]
    version: NotRequired[str]
    author: NotRequired[str]
```

---

## 用法示例

### 创建 Todo

```python
from pydantic_deep import Todo

todo = Todo(
    content="Implement authentication",
    status="in_progress",
    active_form="Implementing authentication",
)
```

### 创建 SubAgentConfig

```python
from pydantic_deep import SubAgentConfig

config: SubAgentConfig = {
    "name": "code-reviewer",
    "description": "Reviews code for quality and security",
    "instructions": "You are an expert code reviewer...",
}
```

### 创建 Skill

```python
from pydantic_deep import Skill

skill: Skill = {
    "name": "api-design",
    "description": "Design RESTful APIs",
    "path": "/path/to/skill",
    "tags": ["api", "rest"],
    "version": "1.0.0",
    "author": "your-name",
    "frontmatter_loaded": True,
}
```

### 创建 SkillDirectory

```python
from pydantic_deep import SkillDirectory

dirs: list[SkillDirectory] = [
    {"path": "~/.pydantic-deep/skills", "recursive": True},
    {"path": "./project-skills", "recursive": False},
]
```

---

## 类型检查

所有类型都支持运行时检查：

```python
from pydantic_deep import Skill

def process_skill(skill: Skill) -> None:
    # 类型检查器知道所有字段
    print(skill["name"])
    print(skill["description"])

    # 可选字段
    if "instructions" in skill:
        print(skill["instructions"])
```

类型从主模块导出：

```python
from pydantic_deep import (
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
)
```
