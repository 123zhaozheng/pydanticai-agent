# Backends API

## 协议

### BackendProtocol

所有文件存储后端的基协议。

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class BackendProtocol(Protocol):
    def ls_info(self, path: str) -> list[FileInfo]:
        """列出目录内容。"""
        ...

    def read(
        self,
        path: str,
        offset: int = 0,
        limit: int = 2000,
    ) -> str:
        """读取带有行号的文件内容。"""
        ...

    def write(self, path: str, content: str) -> WriteResult:
        """写入文件内容。"""
        ...

    def edit(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """通过替换字符串编辑文件。"""
        ...

    def glob_info(
        self,
        pattern: str,
        path: str = "/",
    ) -> list[FileInfo]:
        """查找匹配 glob 模式的文件。"""
        ...

    def grep_raw(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> list[GrepMatch] | str:
        """使用正则表达式搜索文件内容。"""
        ...
```

### SandboxProtocol

具有命令执行功能的扩展协议。

```python
@runtime_checkable
class SandboxProtocol(BackendProtocol, Protocol):
    def execute(
        self,
        command: str,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """执行 Shell 命令。"""
        ...

    @property
    def id(self) -> str:
        """此沙箱的唯一标识符。"""
        ...
```

---

## StateBackend

内存文件存储。

### 构造函数

```python
class StateBackend:
    def __init__(self) -> None
```

### 属性

| 属性 | 类型 | 描述 |
|-----------|------|-------------|
| `files` | `dict[str, FileData]` | 存储的文件 |

### 示例

```python
from pydantic_deep import StateBackend

backend = StateBackend()

# 写入文件
backend.write("/src/app.py", "print('hello')")

# 读取文件
content = backend.read("/src/app.py")
# "     1\tprint('hello')"

# 列出目录
files = backend.ls_info("/src")
# [FileInfo(name="app.py", path="/src/app.py", is_dir=False, size=14)]

# 编辑文件
backend.edit("/src/app.py", "hello", "world")

# Glob 搜索
matches = backend.glob_info("**/*.py")

# Grep 搜索
matches = backend.grep_raw("print")
```

---

## FilesystemBackend

真实文件系统存储。

### 构造函数

```python
class FilesystemBackend:
    def __init__(
        self,
        root: str | Path,
        virtual_mode: bool = False,
    ) -> None
```

### 参数

| 参数 | 类型 | 默认值 | 描述 |
|-----------|------|---------|-------------|
| `root` | `str \| Path` | Required | 根目录 |
| `virtual_mode` | `bool` | `False` | 跟踪写入而不持久化 |

### 属性

| 属性 | 类型 | 描述 |
|-----------|------|-------------|
| `root` | `Path` | 根目录路径 |
| `virtual_mode` | `bool` | 是否启用虚拟模式 |
| `virtual_files` | `dict[str, str]` | 虚拟文件内容 (当 virtual_mode=True 时) |

### 示例

```python
from pydantic_deep import FilesystemBackend

# 直接文件系统访问
backend = FilesystemBackend("/workspace")

# 虚拟模式（无实际写入）
backend = FilesystemBackend("/workspace", virtual_mode=True)

# 写入文件
backend.write("/workspace/app.py", "print('hello')")

# 读取文件（如果存在则从虚拟读取，否则从真实读取）
content = backend.read("/workspace/app.py")

# 检查虚拟文件
if backend.virtual_mode:
    print(backend.virtual_files)
```

---

## CompositeBackend

通过路径前缀路由操作。

### 构造函数

```python
class CompositeBackend:
    def __init__(
        self,
        default: BackendProtocol,
        routes: dict[str, BackendProtocol],
    ) -> None
```

### 参数

| 参数 | 类型 | 描述 |
|-----------|------|-------------|
| `default` | `BackendProtocol` | 未匹配路径的后端 |
| `routes` | `dict[str, BackendProtocol]` | 路径前缀 → 后端映射 |

### 示例

```python
from pydantic_deep import CompositeBackend, StateBackend, FilesystemBackend

backend = CompositeBackend(
    default=StateBackend(),
    routes={
        "/project/": FilesystemBackend("/my/project"),
        "/workspace/": FilesystemBackend("/tmp/workspace"),
    },
)

# 路由到 FilesystemBackend
backend.write("/project/app.py", "...")

# 路由到 StateBackend（默认）
backend.write("/temp/scratch.txt", "...")
```

---

## DockerSandbox

具有执行功能的 Docker 容器沙箱。

### 构造函数

```python
class DockerSandbox:
    def __init__(
        self,
        image: str,
        work_dir: str = "/workspace",
    ) -> None
```

### 参数

| 参数 | 类型 | 默认值 | 描述 |
|-----------|------|---------|-------------|
| `image` | `str` | Required | Docker 镜像名称 |
| `work_dir` | `str` | `"/workspace"` | 容器中的工作目录 |

### 方法

#### execute

```python
def execute(
    self,
    command: str,
    timeout: int | None = None,
) -> ExecuteResponse
```

在容器中执行命令。

#### stop

```python
def stop(self) -> None
```

停止并删除容器。

### 属性

| 属性 | 类型 | 描述 |
|----------|------|-------------|
| `id` | `str` | 容器 ID |

### 示例

```python
from pydantic_deep.backends.sandbox import DockerSandbox

sandbox = DockerSandbox(
    image="python:3.12-slim",
    work_dir="/workspace",
)

try:
    # 写入文件
    sandbox.write("/workspace/script.py", "print('hello')")

    # 执行命令
    result = sandbox.execute("python /workspace/script.py", timeout=30)
    print(result.output)  # "hello\n"
    print(result.exit_code)  # 0

finally:
    sandbox.stop()
```

---

## BaseSandbox

沙箱的抽象基类。

```python
class BaseSandbox(ABC):
    @abstractmethod
    def execute(
        self,
        command: str,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        ...

    @property
    @abstractmethod
    def id(self) -> str:
        ...
```

继承此类以创建自定义沙箱实现。

---

## 类型定义

### FileInfo

```python
class FileInfo(TypedDict):
    name: str      # 文件/目录名称
    path: str      # 完整路径
    is_dir: bool   # 如果是目录则为 True
    size: int | None  # 文件大小（字节）
```

### FileData

```python
class FileData(TypedDict):
    content: list[str]  # 文件行
    created_at: str     # ISO 8601 时间戳
    modified_at: str    # ISO 8601 时间戳
```

### WriteResult

```python
@dataclass
class WriteResult:
    path: str | None = None
    error: str | None = None
```

### EditResult

```python
@dataclass
class EditResult:
    path: str | None = None
    error: str | None = None
    occurrences: int | None = None
```

### ExecuteResponse

```python
@dataclass
class ExecuteResponse:
    output: str
    exit_code: int | None = None
    truncated: bool = False
```

### GrepMatch

```python
class GrepMatch(TypedDict):
    path: str
    line_number: int
    line: str
```
