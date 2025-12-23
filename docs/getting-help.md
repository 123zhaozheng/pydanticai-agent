# 获取帮助

## 文档

本文档是您的首要资源。使用搜索栏（按 `/` 或 `s`）查找特定主题。

## GitHub Issues

用于提交 Bug、功能请求或提问：

[:fontawesome-brands-github: 提交 Issue](https://github.com/vstorm-co/pydantic-deep/issues){ .md-button }

### 提交 Issue 之前

1. **搜索现有 Issue** - 您遇到的问题可能已经被报告过了
2. **查阅文档** - 答案可能就在文档中
3. **准备最小复现示例** - 帮助我们复现问题

### Bug 报告模板

```markdown
## 描述
[清晰地描述 Bug]

## 复现步骤
1. 创建 agent...
2. 调用 agent.run()...
3. 观察报错...

## 预期行为
[您预期的结果]

## 实际行为
[实际发生的结果]

## 环境
- pydantic-deep 版本: X.X.X
- Python 版本: 3.XX
- OS: [例如 macOS 14.0]
```

## 社区资源

### Pydantic AI

pydantic-deep 基于 Pydantic AI 构建。他们的文档是非常好的资源：

- [Pydantic AI 文档](https://ai.pydantic.dev/)
- [Pydantic AI GitHub](https://github.com/pydantic/pydantic-ai)

### Pydantic

用于数据验证和类型提示：

- [Pydantic 文档](https://docs.pydantic.dev/)

## 常见问题 (FAQ)

### pydantic-deep 与 LangChain 有什么不同？

pydantic-deep 基于 Pydantic AI 构建，提供：

- 使用 Pydantic 模型构建类型安全的 Agent
- 更简单、更 Pythonic 的 API
- 更好的 IDE 支持和自动补全
- 没有复杂的链式抽象

### 我可以使用除 Anthropic 以外的模型吗？

是的！Pydantic AI 支持多种提供商：

```python
# OpenAI
agent = create_deep_agent(model="openai:gpt-4")

# Google
agent = create_deep_agent(model="google:gemini-1.5-pro")

# Anthropic (默认)
agent = create_deep_agent(model="openai:gpt-4.1")
```

### 如何在没有 API 调用的情况下运行（用于测试）？

使用 Pydantic AI 中的 `TestModel`：

```python
from pydantic_ai.models.test import TestModel

agent = create_deep_agent(model=TestModel())
```

### 我可以在异步框架中使用 pydantic-deep 吗？

是的！pydantic-deep 是完全异步原生的：

```python
from fastapi import FastAPI
from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend

app = FastAPI()
agent = create_deep_agent()

@app.post("/chat")
async def chat(prompt: str):
    deps = DeepAgentDeps(backend=StateBackend())
    result = await agent.run(prompt, deps=deps)
    return {"response": result.output}
```

### 如何在运行之间持久化文件？

使用 `FilesystemBackend` 替代 `StateBackend`：

```python
from pydantic_deep import FilesystemBackend

backend = FilesystemBackend("/path/to/workspace")
deps = DeepAgentDeps(backend=backend)
```
