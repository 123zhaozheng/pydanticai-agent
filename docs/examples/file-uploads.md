# 文件上传

上传文件供 Agent 处理。Agent 可以使用内置文件工具分析、搜索和处理上传的文件。

## 概览

pydantic-deep 支持两种文件上传方式：

1. **`run_with_files()`** - 在一次调用中上传文件并运行 Agent 的辅助函数
2. **`deps.upload_file()`** - 直接上传到依赖项以获得更多控制

上传的文件：

- 存储在后端（StateBackend, FilesystemBackend 等）
- 在系统提示词中对 Agent 可见
- 通过文件工具可访问（`read_file`, `grep`, `glob`, `execute`）

## 快速开始

### 使用 run_with_files()

处理文件的最简单方法：

```python
import asyncio
from pydantic_deep import create_deep_agent, DeepAgentDeps, run_with_files
from pydantic_deep.backends import StateBackend

async def main():
    agent = create_deep_agent()
    deps = DeepAgentDeps(backend=StateBackend())

    # 在一次调用中上传并处理文件
    with open("data.csv", "rb") as f:
        result = await run_with_files(
            agent,
            "Analyze this data and find trends",
            deps,
            files=[("data.csv", f.read())],
        )

    print(result)

asyncio.run(main())
```

### 使用 deps.upload_file()

为了通过上传过程获得更多控制：

```python
async def main():
    agent = create_deep_agent()
    deps = DeepAgentDeps(backend=StateBackend())

    # 分别上传文件
    deps.upload_file("config.json", b'{"debug": true}')
    deps.upload_file("data.csv", csv_bytes)

    # 运行 Agent - 它在系统提示词中看到上传的文件
    result = await agent.run("Summarize the config and data", deps=deps)
```

## 工作原理

### 文件存储

当你上传文件时：

1. 内容写入后端 `/uploads/<filename>`
2. 元数据在 `deps.uploads` 字典中跟踪
3. Agent 在动态系统提示词中看到文件信息

```python
deps.upload_file("sales.csv", csv_bytes)

# 文件存储于： /uploads/sales.csv
# 跟踪的元数据：
print(deps.uploads)
# {'/uploads/sales.csv': {'name': 'sales.csv', 'path': '/uploads/sales.csv', 'size': 1024, 'line_count': 50}}
```

### 系统提示词

Agent 在其上下文中看到上传的文件：

```
## Uploaded Files

Files uploaded by the user:
- `/uploads/sales.csv` (1.0 KB, 50 lines)
- `/uploads/config.json` (128 B, 5 lines)

Use `read_file`, `grep`, `glob` or `execute` to work with these files.
For large files, use `offset` and `limit` in `read_file`.
```

### Agent 工具

Agent 可以使用这些工具来处理上传的文件：

| 工具 | 用法 |
|------|-------|
| `read_file` | 读取文件内容（对于大文件带有 offset/limit） |
| `grep` | 在文件中搜索模式 |
| `glob` | 按模式查找文件 |
| `execute` | 运行处理文件的脚本（使用 DockerSandbox） |

## 自定义上传目录

默认情况下，文件上传到 `/uploads/`。你可以自定义此设置：

```python
# 带自定义目录的 run_with_files
result = await run_with_files(
    agent,
    "Process configs",
    deps,
    files=[("app.json", config_bytes)],
    upload_dir="/configs",  # 文件进入 /configs/
)

# 带自定义目录的直接上传
deps.upload_file("db.json", data, upload_dir="/data")
# 存储于： /data/db.json
```

## 多个文件

一次上传多个文件：

```python
files = [
    ("sales_q1.csv", q1_data),
    ("sales_q2.csv", q2_data),
    ("sales_q3.csv", q3_data),
]

result = await run_with_files(
    agent,
    "Compare sales across all quarters",
    deps,
    files=files,
)
```

## 二进制文件

二进制文件（图像、PDF 等）只能获得有限支持：

```python
# 二进制文件上传
deps.upload_file("image.png", png_bytes)

# 对于二进制文件，line_count 将为 None
print(deps.uploads["/uploads/image.png"]["line_count"])  # None
```

!!! note
    二进制文件已存储，但基于文本的分析受限。对于完整的二进制处理，请考虑使用带有适当工具的 DockerSandbox。

## 大文件

对于大文件，Agent 应该使用分页：

```python
deps.upload_file("large_log.txt", log_bytes)  # 100,000 lines

# Agent 将看到：
# - `/uploads/large_log.txt` (5.2 MB, 100000 lines)

# Agent 随后可以：
# 1. read_file("/uploads/large_log.txt", limit=100)  # First 100 lines
# 2. read_file("/uploads/large_log.txt", offset=100, limit=100)  # Next 100
# 3. grep("ERROR", "/uploads/large_log.txt")  # Search for patterns
```

## 子智能体访问

上传的文件与子智能体共享：

```python
deps.upload_file("data.csv", csv_bytes)

# 主 Agent 可以委托给子智能体
# 子智能体将有权访问 /uploads/data.csv
result = await agent.run(
    "Delegate data analysis to the data-analyst subagent",
    deps=deps,
)
```

## 完整示例

```python
"""Full file uploads workflow example."""

import asyncio
from pydantic import BaseModel
from pydantic_deep import (
    create_deep_agent,
    DeepAgentDeps,
    StateBackend,
    run_with_files,
)


class AnalysisResult(BaseModel):
    """Structured analysis result."""
    summary: str
    total_records: int
    insights: list[str]


async def main():
    # 使用结构化输出创建 Agent
    agent = create_deep_agent(
        model="openai:gpt-4.1",
        output_type=AnalysisResult,
        instructions="""
        You are a data analyst. When analyzing files:
        1. Read the file to understand structure
        2. Perform analysis
        3. Return structured insights
        """,
    )

    deps = DeepAgentDeps(backend=StateBackend())

    # 样本数据
    sales_data = b"""date,product,quantity,revenue
2024-01-15,Widget A,50,2500
2024-01-16,Widget B,30,1800
2024-01-17,Widget A,75,3750
2024-01-18,Widget C,20,1600
2024-01-19,Widget B,45,2700
"""

    # 运行文件上传
    result = await run_with_files(
        agent,
        "Analyze the sales data: identify top product, total revenue, and trends",
        deps,
        files=[("sales.csv", sales_data)],
    )

    # 对结构化结果的类型安全访问
    print(f"Summary: {result.summary}")
    print(f"Total records: {result.total_records}")
    print("Insights:")
    for insight in result.insights:
        print(f"  - {insight}")


if __name__ == "__main__":
    asyncio.run(main())
```

## API 参考

### run_with_files()

```python
async def run_with_files(
    agent: Agent[DeepAgentDeps, OutputT],
    query: str,
    deps: DeepAgentDeps,
    files: list[tuple[str, bytes]] | None = None,
    *,
    upload_dir: str = "/uploads",
) -> OutputT:
    """Run agent with file uploads.

    Args:
        agent: The agent to run.
        query: The user query/prompt.
        deps: Agent dependencies.
        files: List of (filename, content) tuples to upload.
        upload_dir: Directory to store uploads.

    Returns:
        Agent output (type depends on agent's output_type).
    """
```

### deps.upload_file()

```python
def upload_file(
    self,
    name: str,
    content: bytes,
    *,
    upload_dir: str = "/uploads",
) -> str:
    """Upload a file to the backend and track it.

    Args:
        name: Original filename (e.g., "sales.csv")
        content: File content as bytes
        upload_dir: Directory to store uploads

    Returns:
        The path where the file was stored.
    """
```

### UploadedFile

```python
class UploadedFile(TypedDict):
    """Metadata for an uploaded file."""
    name: str        # Original filename
    path: str        # Path in backend (e.g., /uploads/sales.csv)
    size: int        # Size in bytes
    line_count: int | None  # Number of lines (None for binary)
```

## 下一步

- [基本用法](basic-usage.md) - 核心功能
- [Docker 沙箱](docker-sandbox.md) - 对上传的文件执行代码
- [结构化输出](../advanced/structured-output.md) - 类型安全的结果
