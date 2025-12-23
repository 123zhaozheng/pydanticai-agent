# 示例

本节包含演示 pydantic-deep 功能的实际示例。

## 运行示例

所有示例都在 `examples/` 目录中：

```bash
# 设置你的 API 密钥
export ANTHROPIC_API_KEY=your-api-key

# 运行示例
uv run python examples/<example_name>.py
```

## 示例概览

<div class="feature-grid">

<div class="feature-card">
<h3>📖 基本用法</h3>
<p>pydantic-deep 入门。创建 Agent，使用 todo，处理文件。</p>
<a href="basic-usage/">查看示例 →</a>
</div>

<div class="feature-card">
<h3>📁 文件系统</h3>
<p>使用 FilesystemBackend 和 CompositeBackend 进行真实文件系统操作。</p>
<a href="filesystem/">查看示例 →</a>
</div>

<div class="feature-card">
<h3>🎯 技能</h3>
<p>具有渐进式披露的模块化能力包。</p>
<a href="skills/">查看示例 →</a>
</div>

<div class="feature-card">
<h3>🐳 Docker 沙箱</h3>
<p>Docker 容器中的隔离代码执行。</p>
<a href="docker-sandbox/">查看示例 →</a>
</div>

<div class="feature-card">
<h3>📤 文件上传</h3>
<p>使用 run_with_files() 或 deps.upload_file() 上传文件供 Agent 处理。</p>
<a href="file-uploads/">查看示例 →</a>
</div>

</div>

## 快速示例

### Hello World

```python
import asyncio
from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend

async def main():
    agent = create_deep_agent()
    deps = DeepAgentDeps(backend=StateBackend())

    result = await agent.run("Say hello!", deps=deps)
    print(result.output)

asyncio.run(main())
```

### 创建文件

```python
async def main():
    agent = create_deep_agent()
    deps = DeepAgentDeps(backend=StateBackend())

    result = await agent.run(
        "Create a Python function that calculates factorials and save it to /math/factorial.py",
        deps=deps,
    )

    # 检查创建了什么
    print("Files:", list(deps.backend.files.keys()))
    print("\nContent:")
    print(deps.backend.read("/math/factorial.py"))
```

### 规划任务

```python
async def main():
    agent = create_deep_agent()
    deps = DeepAgentDeps(backend=StateBackend())

    result = await agent.run(
        """
        Create a simple CLI calculator with the following features:
        1. Add, subtract, multiply, divide
        2. Input validation
        3. Help command

        Plan the task first using todos, then implement.
        """,
        deps=deps,
    )

    # 检查 todo 列表
    print("Todos:")
    for todo in deps.todos:
        status = "✓" if todo.status == "completed" else "○"
        print(f"  {status} {todo.content}")
```

### 委托给子智能体

```python
from pydantic_deep import SubAgentConfig

async def main():
    subagents = [
        SubAgentConfig(
            name="code-reviewer",
            description="Reviews code for quality",
            instructions="You are a code review expert...",
        ),
    ]

    agent = create_deep_agent(subagents=subagents)
    deps = DeepAgentDeps(backend=StateBackend())

    # 创建一些代码
    deps.backend.write("/src/app.py", "def add(a, b): return a + b")

    result = await agent.run(
        "Delegate a code review of /src/app.py to the code-reviewer",
        deps=deps,
    )

    print(result.output)
```

### 使用技能

```python
async def main():
    agent = create_deep_agent(
        skill_directories=[
            {"path": "./skills", "recursive": True},
        ],
    )
    deps = DeepAgentDeps(backend=StateBackend())

    result = await agent.run(
        """
        1. List available skills
        2. Load the code-review skill
        3. Use it to review /src/app.py
        """,
        deps=deps,
    )

    print(result.output)
```

## 无 API 测试

使用 `TestModel` 进行无 API 调用的测试：

```python
from pydantic_ai.models.test import TestModel

async def main():
    agent = create_deep_agent(model=TestModel())
    deps = DeepAgentDeps(backend=StateBackend())

    # TestModel 将返回预定义响应
    result = await agent.run("Test prompt", deps=deps)
```

## 示例文件

| 文件 | 描述 |
|------|-------------|
| `basic_usage.py` | 核心功能演示 |
| `filesystem_backend.py` | 真实文件系统操作 |
| `subagents.py` | 任务委托 |
| `human_in_the_loop.py` | 审批工作流 |
| `docker_sandbox.py` | 隔离执行 |
| `composite_backend.py` | 混合存储策略 |
| `streaming.py` | 实时输出 |
| `custom_tools.py` | 添加自定义工具 |
| `skills_usage.py` | 技能系统 |
| `file_uploads.py` | 供 Agent 处理的文件上传 |

## 下一步

- [基本用法](basic-usage.md) - 详细演练
- [核心概念](../concepts/index.md) - 了解基础知识
- [API 参考](../api/index.md) - 完整的 API 文档
