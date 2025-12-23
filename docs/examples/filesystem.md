# 文件系统示例

此示例演示使用 FilesystemBackend 和 CompositeBackend 处理真实文件。

## FilesystemBackend

### 源代码

:material-file-code: `examples/filesystem_backend.py`

### 概览

```python
"""Working with real files on disk."""

import asyncio
import tempfile
from pathlib import Path

from pydantic_deep import (
    create_deep_agent,
    DeepAgentDeps,
    FilesystemBackend,
)


async def main():
    # 创建临时工作区
    with tempfile.TemporaryDirectory() as workspace:
        print(f"Workspace: {workspace}")

        # 创建指向真实文件系统的后端
        # virtual_mode=True 跟踪更改而不持久化（对演示安全）
        backend = FilesystemBackend(workspace, virtual_mode=True)

        agent = create_deep_agent()
        deps = DeepAgentDeps(backend=backend)

        result = await agent.run(
            """
            Create a Python project structure:
            1. src/app.py - Main application
            2. src/utils.py - Utility functions
            3. tests/test_app.py - Test file
            4. README.md - Project description
            """,
            deps=deps,
        )

        print(result.output)

        # 检查创建了什么
        print("\nFiles created:")
        for path in Path(workspace).rglob("*"):
            if path.is_file():
                print(f"  {path.relative_to(workspace)}")


asyncio.run(main())
```

### 虚拟模式

虚拟模式跟踪文件操作而不实际写入磁盘：

```python
# 写入到虚拟存储
backend = FilesystemBackend(workspace, virtual_mode=True)

# 写入到实际文件系统
backend = FilesystemBackend(workspace, virtual_mode=False)
```

这对于以下情况很有用：

- 无副作用的测试
- 应用前预览更改
- 安全演示

## CompositeBackend

### 源代码

:material-file-code: `examples/composite_backend.py`

### 概览

按路径前缀将操作路由到不同的后端：

```python
"""Mixed storage strategies with CompositeBackend."""

import asyncio
import tempfile
from pathlib import Path

from pydantic_deep import (
    create_deep_agent,
    DeepAgentDeps,
    StateBackend,
    FilesystemBackend,
    CompositeBackend,
)


async def main():
    with tempfile.TemporaryDirectory() as workspace:
        # 创建后端：
        # - 用于临时暂存文件的 StateBackend
        # - 用于持久化项目文件的 FilesystemBackend
        memory = StateBackend()
        filesystem = FilesystemBackend(workspace, virtual_mode=True)

        # 按路径前缀路由
        backend = CompositeBackend(
            default=memory,  # 未匹配路径到这里
            routes={
                "/project/": filesystem,    # 项目文件到磁盘
                "/workspace/": filesystem,  # 工作区文件到磁盘
                # /temp/, /scratch/ 进入内存（默认）
            },
        )

        agent = create_deep_agent()
        deps = DeepAgentDeps(backend=backend)

        result = await agent.run(
            """
            Create files in different locations:
            1. /project/src/app.py - Persistent application code
            2. /project/README.md - Persistent documentation
            3. /scratch/notes.txt - Temporary notes (in memory)
            """,
            deps=deps,
        )

        print(result.output)

        # 显示内容位置
        print("\nIn memory (temporary):")
        for path in memory.files.keys():
            print(f"  {path}")

        print("\nOn filesystem (persistent):")
        for path in Path(workspace).rglob("*"):
            if path.is_file():
                print(f"  {path.relative_to(workspace)}")


asyncio.run(main())
```

### 用例

| 模式 | 用例 |
|---------|----------|
| 内存默认 + 文件系统路由 | 暂存空间 + 持久化输出 |
| 多个文件系统路由 | 多项目工作区 |
| Docker 路由 + 文件系统路由 | 执行代码 + 持久化结果 |

## Glob 和 Grep

查找和搜索文件：

```python
# 查找所有 Python 文件
matches = backend.glob_info("**/*.py", path="/project")
for match in matches:
    print(f"{match['path']} ({match['size']} bytes)")

# 搜索函数定义
results = backend.grep_raw(r"def \w+\(", path="/project/src")
for result in results:
    print(f"{result['path']}:{result['line_number']}: {result['line']}")
```

## 使用偏移量读取

对于大文件，读取特定部分：

```python
# 读取第 100-200 行
content = backend.read("/large_file.py", offset=99, limit=100)
```

## 编辑操作

替换文件中的字符串：

```python
# 替换单次出现
result = backend.edit(
    "/src/app.py",
    old_string="old_function",
    new_string="new_function",
)

# 替换所有出现
result = backend.edit(
    "/src/app.py",
    old_string="TODO",
    new_string="DONE",
    replace_all=True,
)

print(f"Replaced {result.occurrences} occurrences")
```

## 运行示例

```bash
# 文件系统后端
uv run python examples/filesystem_backend.py

# 复合后端
uv run python examples/composite_backend.py
```

## 下一步

- [Docker 沙箱](docker-sandbox.md) - 隔离执行
- [技能示例](skills.md) - 使用技能
- [概念：后端](../concepts/backends.md) - 深入研究
