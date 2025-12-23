# Docker 沙箱示例

此示例演示使用 DockerSandbox 的隔离代码执行。

## 源代码

:material-file-code: `examples/docker_sandbox.py`

## 先决条件

!!! warning "需要 Docker"
    此示例需要安装并运行 Docker。

```bash
# 安装 Docker: https://docs.docker.com/get-docker/

# 拉取 Python 镜像
docker pull python:3.12-slim

# 安装 docker 包
uv add pydantic-deep[sandbox]
```

## 概览

DockerSandbox 提供：

- 隔离的执行环境
- 安全的代码执行
- 容器生命周期管理
- 容器内的文件操作

## 完整示例

```python
"""Docker sandbox example for isolated code execution."""

import asyncio

from pydantic_deep import create_deep_agent, DeepAgentDeps
from pydantic_deep.backends.sandbox import DockerSandbox


async def main():
    # 创建 Docker 沙箱
    sandbox = DockerSandbox(
        image="python:3.12-slim",
        work_dir="/workspace",
    )

    try:
        # 使用沙箱后端创建 Agent
        agent = create_deep_agent(
            model="openai:gpt-4.1",
            instructions="""
            You are a Python development assistant.
            You can write code, save it to files, and execute it.
            Always test your code by running it.
            """,
            # 要求审批执行（为了安全）
            interrupt_on={"execute": True},
        )

        deps = DeepAgentDeps(backend=sandbox)

        # 运行 Agent
        result = await agent.run(
            """
            Create a Python script that:
            1. Defines a function to calculate fibonacci numbers
            2. Prints the first 10 fibonacci numbers
            3. Save it to /workspace/fibonacci.py
            4. Run it and show the output
            """,
            deps=deps,
        )

        print(result.output)

    finally:
        # 始终清理容器
        sandbox.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

## 沙箱配置

### 基本设置

```python
sandbox = DockerSandbox(
    image="python:3.12-slim",  # Docker 镜像
    work_dir="/workspace",      # 容器内的工作目录
)
```

### 自定义配置

```python
sandbox = DockerSandbox(
    image="python:3.12",
    work_dir="/app",
    # 可以在实现中添加额外选项
)
```

## 执行

`execute` 工具在容器内运行命令：

```python
# Agent can call:
execute(command="python script.py", timeout=30)
```

响应包含：

```python
@dataclass
class ExecuteResponse:
    output: str        # stdout + stderr
    exit_code: int     # 进程退出码
    truncated: bool    # 如果输出被截断则为 True
```

## 人机回环

始终要求审批执行：

```python
agent = create_deep_agent(
    interrupt_on={"execute": True},
)

result = await agent.run(prompt, deps=deps)

# 处理审批...
if hasattr(result, 'deferred_tool_calls'):
    for call in result.deferred_tool_calls:
        if call.tool_name == "execute":
            print(f"Command: {call.args['command']}")
            # 审查并批准/拒绝
```

## 容器生命周期

### 自动启动

容器在首次操作时自动启动：

```python
sandbox = DockerSandbox(image="python:3.12-slim")
sandbox.write("/test.py", "print('hello')")  # 启动容器
```

### 手动停止

完成后始终停止容器：

```python
try:
    # Use sandbox...
finally:
    sandbox.stop()
```

或者使用上下文管理器模式：

```python
async with DockerSandbox(...) as sandbox:
    # Use sandbox...
# 容器自动停止
```

## 文件操作

所有标准文件操作都在容器内工作：

```python
# 写入文件
sandbox.write("/workspace/app.py", "print('hello')")

# 读取文件
content = sandbox.read("/workspace/app.py")

# 编辑文件
sandbox.edit("/workspace/app.py", "hello", "world")

# 列出目录
files = sandbox.ls_info("/workspace")

# Glob 模式
python_files = sandbox.glob_info("**/*.py", "/workspace")

# 搜索内容
matches = sandbox.grep_raw("def main", "/workspace")
```

## 安全注意事项

!!! danger "安全警告"
    即使有 Docker 隔离，也要小心：

    - 来自容器的网络访问
    - 资源消耗
    - 恶意代码执行
    - 容器逃逸漏洞

### 最佳实践

1. **始终要求审批** `execute`
2. **使用最小镜像**（slim 变体）
3. **设置执行超时**
4. **审批前审查命令**
5. **使用后清理容器**

## 错误处理

```python
try:
    result = sandbox.execute("python script.py", timeout=30)
    if result.exit_code != 0:
        print(f"Script failed: {result.output}")
    except TimeoutError:
        print("Execution timed out")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sandbox.stop()
```

## 替代方案：LocalSandbox

用于无 Docker 的开发/测试：

```python
from pydantic_deep.backends.sandbox import LocalSandbox

# 在本地机器上执行（生产环境中危险！）
sandbox = LocalSandbox(work_dir="/tmp/workspace")
```

!!! warning
    LocalSandbox 在没有隔离的情况下在实际机器上运行命令。
    仅在开发中用于受信任的代码。

## 运行示例

```bash
# 确保 Docker 正在运行
docker ps

# 运行示例
uv run python examples/docker_sandbox.py
```

## 预期输出

```
Note: This example requires Docker to be installed and running.

Agent Response:
==================================================
I'll create a fibonacci script for you...

[Approval prompt for execute command]

Running: python /workspace/fibonacci.py

Output:
0, 1, 1, 2, 3, 5, 8, 13, 21, 34

The script successfully calculated and printed the first 10 Fibonacci numbers.
```

## 下一步

- [概念：后端](../concepts/backends.md) - 深入研究
- [人机回环](../advanced/human-in-the-loop.md) - 审批工作流
- [API 参考](../api/backends.md) - SandboxProtocol API
