	# 后端 (Backends)

后端为 deep agents 提供文件存储。所有后端实现 `BackendProtocol`。

## 可用后端

| 后端 | 持久性 | 执行 | 用例 |
|---------|-------------|-----------|----------|
| `StateBackend` | 临时 | 否 | 测试，临时文件 |
| `FilesystemBackend` | 持久 | 否 | 真实文件操作 |
| `DockerSandbox` | 临时 | 是 | 安全代码执行 |
| `CompositeBackend` | 混合 | 取决于 | 按路径前缀路由 |

## StateBackend

内存存储，非常适合测试和临时操作。

```python
from pydantic_deep import StateBackend, DeepAgentDeps

backend = StateBackend()
deps = DeepAgentDeps(backend=backend)

# 文件存储在内存中
backend.write("/src/app.py", "print('hello')")
print(backend.read("/src/app.py"))

# 访问所有文件
print(backend.files.keys())
```

### 特点

- ✅ 快速 - 无磁盘 I/O
- ✅ 隔离 - 无副作用
- ✅ 完美适合测试
- ❌ 进程结束时数据丢失
- ❌ 无命令执行

## FilesystemBackend

带有可选虚拟模式的真实文件系统操作。

```python
from pydantic_deep import FilesystemBackend

# 直接文件系统访问
backend = FilesystemBackend("/path/to/workspace")

# 虚拟模式 - 跟踪写入但不持久化
backend = FilesystemBackend("/path/to/workspace", virtual_mode=True)
```

### 虚拟模式

虚拟模式跟踪所有操作而不修改实际文件系统：

```python
backend = FilesystemBackend("/workspace", virtual_mode=True)

# 写入到虚拟存储
backend.write("/workspace/new_file.py", "content")

# 如果存在则从虚拟读取，否则从真实文件系统读取
content = backend.read("/workspace/existing_file.py")

# 获取虚拟写入列表
print(backend.virtual_files)
```

### Ripgrep 集成

FilesystemBackend 在可用时使用 ripgrep 进行快速搜索：

```python
# 跨文件快速正则表达式搜索
matches = backend.grep_raw(r"def \w+\(", path="/workspace/src")
```

## DockerSandbox

使用 Docker 容器的隔离执行环境。

!!! warning "需要 Docker"
    确保 Docker 已安装并运行。

```python
from pydantic_deep.backends.sandbox import DockerSandbox

sandbox = DockerSandbox(
    image="python:3.12-slim",
    work_dir="/workspace",
)

try:
    deps = DeepAgentDeps(backend=sandbox)

    # Agent 现在可以安全地执行代码
    agent = create_deep_agent(
        interrupt_on={"execute": True},  # 仍然要求审批
    )

    result = await agent.run(
        "Create and run a Python script",
        deps=deps,
    )
finally:
    sandbox.stop()  # 清理容器
```

### 执行

```python
# 在容器中执行命令
response = sandbox.execute("python script.py", timeout=30)
print(response.output)
print(response.exit_code)
```

## CompositeBackend

基于路径前缀将操作路由到不同的后端。

```python
from pydantic_deep import CompositeBackend, StateBackend, FilesystemBackend

backend = CompositeBackend(
    default=StateBackend(),  # 未匹配路径的默认值
    routes={
        "/project/": FilesystemBackend("/my/project"),
        "/workspace/": FilesystemBackend("/tmp/workspace"),
        # /temp/ 进入默认 (StateBackend)
    },
)

deps = DeepAgentDeps(backend=backend)
```

### 用例

- 持久化项目文件 + 临时暂存空间
- 多个项目目录
- 只读源 + 可写输出

## 后端协议

所有后端都实现此协议：

```python
from typing import Protocol

class BackendProtocol(Protocol):
    def ls_info(self, path: str) -> list[FileInfo]:
        """List directory contents."""
        ...

    def read(self, path: str, offset: int = 0, limit: int = 2000) -> str:
        """Read file contents with line numbers."""
        ...

    def write(self, path: str, content: str) -> WriteResult:
        """Write file contents."""
        ...

    def edit(
        self,
        path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> EditResult:
        """Edit file by replacing strings."""
        ...

    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        """Find files matching glob pattern."""
        ...

    def grep_raw(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
    ) -> list[GrepMatch] | str:
        """Search file contents with regex."""
        ...
```

### SandboxProtocol

扩展 BackendProtocol 以支持执行：

```python
class SandboxProtocol(BackendProtocol, Protocol):
    def execute(
        self,
        command: str,
        timeout: int | None = None,
    ) -> ExecuteResponse:
        """Execute a shell command."""
        ...

    @property
    def id(self) -> str:
        """Unique identifier for this sandbox."""
        ...
```

## 自定义后端

通过实现协议创建您自己的后端：

```python
from pydantic_deep import BackendProtocol, FileInfo, WriteResult

class S3Backend:
    """Store files in S3."""

    def __init__(self, bucket: str):
        self.bucket = bucket
        self._client = boto3.client('s3')

    def read(self, path: str, offset: int = 0, limit: int = 2000) -> str:
        response = self._client.get_object(Bucket=self.bucket, Key=path)
        content = response['Body'].read().decode('utf-8')
        lines = content.split('\n')
        # Add line numbers like StateBackend
        return '\n'.join(
            f"{i+1}\t{line}"
            for i, line in enumerate(lines[offset:offset+limit])
        )

    def write(self, path: str, content: str) -> WriteResult:
        self._client.put_object(
            Bucket=self.bucket,
            Key=path,
            Body=content.encode('utf-8'),
        )
        return WriteResult(path=path)

    # Implement other methods...
```

## 路径安全

所有后端都验证路径以防止目录遍历：

```python
# 这些将失败并报错：
backend.read("../etc/passwd")      # 父目录
backend.read("~/secrets")          # 主目录扩展
backend.read("C:\\Windows\\...")   # Windows 绝对路径
```

## 下一步

- [工具集](toolsets.md) - 工具如何使用后端
- [Docker 沙箱示例](../examples/docker-sandbox.md) - 完整示例
- [API 参考](../api/backends.md) - 完整 API
