# pydantic-deep

<p style="font-size: 1.3em; color: #888; margin-top: -0.5em;">
Pydantic AI 风格的深度智能体框架
</p>

[![PyPI version](https://img.shields.io/pypi/v/pydantic-deep.svg)](https://pypi.org/project/pydantic-deep/)
[![CI](https://github.com/vstorm-co/pydantic-deep/actions/workflows/ci.yml/badge.svg)](https://github.com/vstorm-co/pydantic-deep/actions/workflows/ci.yml)
[![coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/vstorm-co/pydantic-deep)
[![python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org/)
[![license](https://img.shields.io/badge/license-MIT-green)](https://opensource.org/licenses/MIT)

---

**pydantic-deep** 是一个构建在 [Pydantic AI](https://ai.pydantic.dev/) 之上的 Python 深度智能体 (deep agent) 框架，旨在帮助您快速构建具备规划、文件系统操作、子智能体委托和技能的生产级自主 Agent。

## 为什么选择 pydantic-deep？

构建能够规划、执行多步骤任务并处理文件的自主 Agent 是复杂的。pydantic-deep 提供：

<div class="feature-grid">
<div class="feature-card">
<h3>📋 规划</h3>
<p>内置待办事项列表用于任务分解。Agent 自动分解复杂任务并跟踪进度。</p>
</div>

<div class="feature-card">
<h3>📁 文件系统</h3>
<p>虚拟和真实文件系统操作。支持 grep 和 glob 的文件读取、写入和编辑。</p>
</div>

<div class="feature-card">
<h3>🤖 子智能体</h3>
<p>将专业任务委托给隔离的子智能体。代码审查、测试、文档 - 每个都有专注的上下文。</p>
</div>

<div class="feature-card">
<h3>🎯 技能</h3>
<p>按需加载的模块化能力包。扩展 Agent 能力而不臃肿上下文。</p>
</div>
</div>

## Hello World 示例

```python
import asyncio
from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend

async def main():
    # 创建具备所有能力的 deep agent
    agent = create_deep_agent(
        model="openai:gpt-4.1",
        instructions="You are a helpful coding assistant.",
    )

    # 创建使用内存存储的依赖项
    deps = DeepAgentDeps(backend=StateBackend())

    # 运行 agent
    result = await agent.run(
        "Create a Python function that calculates fibonacci numbers",
        deps=deps,
    )

    print(result.output)

asyncio.run(main())
```

## 工具与依赖注入示例

```python
from pydantic_ai import RunContext
from pydantic_deep import create_deep_agent, DeepAgentDeps

# 定义自定义工具
async def get_weather(
    ctx: RunContext[DeepAgentDeps],
    city: str,
) -> str:
    """Get weather for a city."""
    # 通过 ctx.deps 访问依赖项
    return f"Weather in {city}: Sunny, 22°C"

# 创建带有自定义工具的 agent
agent = create_deep_agent(
    tools=[get_weather],
    instructions="You can check weather and work with files.",
)
```

## 关键特性

| 特性 | 描述 |
|---------|-------------|
| **规划** | 用于任务分解和跟踪的 Todo 工具集 |
| **文件系统** | 读取、写入、编辑、glob、grep 操作 |
| **子智能体** | 上下文隔离的任务委托 |
| **技能** | 具有渐进式披露的模块化能力包 |
| **后端** | StateBackend, FilesystemBackend, DockerSandbox, CompositeBackend |
| **结构化输出** | 通过 `output_type` 使用 Pydantic 模型进行类型安全的响应 |
| **上下文管理** | 长对话的自动摘要 |
| **HITL** | 人机回环审批工作流 |

## llms.txt

pydantic-deep 支持 [llms.txt](https://llmstxt.org/) 标准。访问 `/llms.txt` 获取针对 LLM 优化的内容。

## 下一步

<div class="feature-grid">
<div class="feature-card">
<h3>📖 安装</h3>
<p>几分钟内开始使用 pydantic-deep。</p>
<a href="installation/">安装指南 →</a>
</div>

<div class="feature-card">
<h3>🎓 核心概念</h3>
<p>了解 Agent、后端和工具集。</p>
<a href="concepts/">核心概念 →</a>
</div>

<div class="feature-card">
<h3>📝 示例</h3>
<p>通过实际示例了解 pydantic-deep 的实战应用。</p>
<a href="examples/">示例 →</a>
</div>

<div class="feature-card">
<h3>📚 API 参考</h3>
<p>完整的 API 文档。</p>
<a href="api/">API 参考 →</a>
</div>
</div>
