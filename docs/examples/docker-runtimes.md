# Docker 运行时

本指南展示了如何使用 `RuntimeConfig` 和 `SessionManager` 在预配置环境中使用 Docker 执行代码。

## 快速开始

```python
from pydantic_deep import DockerSandbox, DeepAgentDeps, create_deep_agent

# 使用带有预装包的内置运行时
sandbox = DockerSandbox(runtime="python-datascience")
deps = DeepAgentDeps(backend=sandbox)

agent = create_deep_agent()
result = await agent.run(
    "Load /uploads/data.csv and create a visualization",
    deps=deps,
)

sandbox.stop()
```

## RuntimeConfig

[`RuntimeConfig`][pydantic_deep.types.RuntimeConfig] 类定义了一个预配置的执行环境。

### 使用内置运行时

pydantic-deep 提供了几个内置运行时：

| 运行时 | 描述 | 包 |
|---------|-------------|----------|
| `python-minimal` | 纯净 Python 3.12 | 无 |
| `python-datascience` | 数据科学栈 | pandas, numpy, matplotlib, scikit-learn, seaborn |
| `python-web` | Web 开发 | FastAPI, SQLAlchemy, httpx, uvicorn |
| `node-minimal` | 纯净 Node.js 20 | 无 |
| `node-react` | React 开发 | TypeScript, Vite, React |

```python
from pydantic_deep import DockerSandbox, BUILTIN_RUNTIMES

# 选项 1：使用运行时名称（字符串）
sandbox = DockerSandbox(runtime="python-datascience")

# 选项 2：直接使用 RuntimeConfig
sandbox = DockerSandbox(runtime=BUILTIN_RUNTIMES["python-datascience"])
```

### 创建自定义运行时

```python
from pydantic_deep import RuntimeConfig, DockerSandbox

# 自定义 ML 运行时
ml_runtime = RuntimeConfig(
    name="ml-env",
    description="Machine learning environment with PyTorch",
    base_image="python:3.12-slim",
    packages=["torch", "transformers", "datasets", "accelerate"],
    setup_commands=["apt-get update", "apt-get install -y git"],
    env_vars={"TOKENIZERS_PARALLELISM": "false"},
    work_dir="/workspace",
)

sandbox = DockerSandbox(runtime=ml_runtime)
```

### 运行时配置选项

```python
RuntimeConfig(
    name="my-runtime",           # 唯一标识符
    description="...",           # 人类可读的描述

    # 镜像源（选择一个）：
    image="my-registry/image:v1",  # 预构建镜像
    # 或者
    base_image="python:3.12",      # 构建的基础镜像

    # 包（仅限 base_image）：
    packages=["pandas", "numpy"],
    package_manager="pip",  # pip, npm, apt, cargo

    # 额外设置：
    setup_commands=["apt-get update"],
    env_vars={"DEBUG": "true"},
    work_dir="/workspace",

    # 缓存：
    cache_image=True,  # 本地缓存构建的镜像
)
```

## SessionManager

对于多用户应用程序，使用 [`SessionManager`][pydantic_deep.session.SessionManager] 管理每个用户的隔离容器。

### 基本用法

```python
from pydantic_deep import SessionManager, DeepAgentDeps, create_deep_agent

# 使用默认运行时创建管理器
manager = SessionManager(default_runtime="python-datascience")

async def handle_user_request(user_id: str, query: str):
    # 获取或创建此用户的沙箱
    sandbox = await manager.get_or_create(user_id)

    deps = DeepAgentDeps(backend=sandbox)
    agent = create_deep_agent()

    result = await agent.run(query, deps=deps)
    return result.output

# 定期清理空闲会话
await manager.cleanup_idle(max_idle=1800)  # 30 分钟

# 完成后关闭所有会话
await manager.shutdown()
```

### 会话持久化

同一用户的请求之间会话持久存在：

```python
# 请求 1：创建文件
sandbox = await manager.get_or_create("user-123")
sandbox.execute("echo 'hello' > /workspace/greeting.txt")

# 请求 2：文件仍然存在！
sandbox = await manager.get_or_create("user-123")  # 同一个容器
result = sandbox.execute("cat /workspace/greeting.txt")
print(result.output)  # "hello"
```

### 自动清理

```python
# 启动后台清理循环
manager.start_cleanup_loop(interval=300)  # 每 5 分钟检查一次

# ... 你的应用程序运行 ...

# 关闭时停止清理
manager.stop_cleanup_loop()
await manager.shutdown()
```

### 配置选项

```python
SessionManager(
    default_runtime="python-datascience",  # 新会话的默认值
    default_idle_timeout=3600,             # 1 小时空闲超时
)
```

## 完整示例

```python
import asyncio
from pydantic_deep import (
    create_deep_agent,
    DeepAgentDeps,
    SessionManager,
    RuntimeConfig,
)

async def main():
    # 用于数据分析的自定义运行时
    runtime = RuntimeConfig(
        name="analysis-env",
        description="Data analysis environment",
        base_image="python:3.12-slim",
        packages=["pandas", "numpy", "matplotlib", "seaborn"],
    )

    # 多用户会话管理器
    manager = SessionManager(
        default_runtime=runtime,
        default_idle_timeout=1800,  # 30 分钟
    )

    try:
        # 模拟多用户
        for user_id in ["alice", "bob", "charlie"]:
            sandbox = await manager.get_or_create(user_id)
            deps = DeepAgentDeps(backend=sandbox)

            # 上传用户特定数据
            with open(f"{user_id}_data.csv", "rb") as f:
                deps.upload_file("data.csv", f.read())

            agent = create_deep_agent()
            result = await agent.run(
                "Analyze /uploads/data.csv and create a summary",
                deps=deps,
            )
            print(f"{user_id}: {result.output[:100]}...")

        # 检查活动会话
        print(f"Active sessions: {manager.session_count}")

    finally:
        # 清理所有会话
        count = await manager.shutdown()
        print(f"Cleaned up {count} sessions")

if __name__ == "__main__":
    asyncio.run(main())
```

## 系统提示词集成

当在 DockerSandbox 中使用运行时时，Agent 会自动接收有关可用包的信息：

```
## Runtime Environment

**Name:** python-datascience
**Description:** Python with pandas, numpy, matplotlib, scikit-learn, seaborn
**Working directory:** /workspace

**Pre-installed packages** (use directly without installation):
- pandas
- numpy
- matplotlib
- scikit-learn
- seaborn
```

这有助于 Agent 在无需安装包的情况下了解哪些工具可用。

## 最佳实践

1. **尽可能使用内置运行时** - 它们经过测试和优化。

2. **启用镜像缓存** - 设置 `cache_image=True`（默认）以避免重建镜像。

3. **设置适当的空闲超时** - 平衡资源使用与用户体验。

4. **始终清理** - 使用 `sandbox.stop()` 或 `manager.shutdown()` 释放资源。

5. **考虑预热** - 对于延迟敏感的应用，预创建容器：
   ```python
   sandbox = DockerSandbox(runtime="python-datascience")
   sandbox.start()  # 立即启动容器
   ```
