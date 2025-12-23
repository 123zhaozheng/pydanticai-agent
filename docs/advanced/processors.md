# 历史记录处理器

pydantic-deep 支持历史记录处理器以管理对话上下文。最常见的用例是自动摘要，用于处理长对话而不超过 Token 限制。

## 摘要处理器

`SummarizationProcessor` 监控对话长度，并在达到阈值时自动总结旧消息。

### 基本用法

```python
from pydantic_deep import create_deep_agent
from pydantic_deep.processors import create_summarization_processor

# 创建摘要处理器
processor = create_summarization_processor(
    trigger=("tokens", 100000),  # 达到 100k token 时总结
    keep=("messages", 20),       # 总结后保留最后 20 条消息
)

# 创建带有处理器的 agent
agent = create_deep_agent(
    history_processors=[processor],
)
```

### 触发条件

您可以基于不同的条件触发摘要：

```python
# 当消息数量超过阈值时触发
processor = create_summarization_processor(
    trigger=("messages", 50),
)

# 当 Token 数量超过阈值时触发
processor = create_summarization_processor(
    trigger=("tokens", 100000),
)

# 在最大输入 Token 的比例处触发
processor = create_summarization_processor(
    trigger=("fraction", 0.8),  # 最大 Token 的 80%
    max_input_tokens=200000,    # 比例触发器需要此参数
)

# 多个触发条件（任一条件触发）
processor = create_summarization_processor(
    trigger=[
        ("messages", 100),
        ("tokens", 150000),
    ],
)
```

### 保留配置

控制摘要后保留多少上下文：

```python
# 保留最后 N 条消息
processor = create_summarization_processor(
    trigger=("tokens", 100000),
    keep=("messages", 20),
)

# 保留最后 N 个 Token 量的消息
processor = create_summarization_processor(
    trigger=("tokens", 100000),
    keep=("tokens", 10000),
)

# 保留最大 Token 的比例
processor = create_summarization_processor(
    trigger=("fraction", 0.8),
    keep=("fraction", 0.1),
    max_input_tokens=200000,
)
```

### 自定义 Token 计数器

默认情况下，处理器使用简单的基于字符的估算（每个 Token 约 4 个字符）。为了更准确的计数，请提供自定义 Token 计数器：

```python
def count_tokens(messages):
    """使用 tiktoken 或类似工具的自定义 token 计数器。"""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")

    total = 0
    for msg in messages:
        # 从消息中提取文本并计算 token
        # 实现取决于您的需求
        pass
    return total

processor = create_summarization_processor(
    trigger=("tokens", 100000),
    token_counter=count_tokens,
)
```

### 自定义摘要提示

自定义摘要的执行方式：

```python
custom_prompt = """
Extract the key information from this conversation.
Focus on:
- User requirements and goals
- Important decisions made
- Current state of the task

Messages:
{messages}

Provide a concise summary.
"""

processor = create_summarization_processor(
    trigger=("tokens", 100000),
    summary_prompt=custom_prompt,
)
```

## 直接使用处理器类

为了获得更多控制权，直接使用 `SummarizationProcessor`：

```python
from pydantic_deep.processors import SummarizationProcessor

processor = SummarizationProcessor(
    model="openai:gpt-4.1",
    trigger=("tokens", 100000),
    keep=("messages", 20),
    max_input_tokens=None,
    trim_tokens_to_summarize=4000,  # 限制摘要输入大小
)
```

## 工作原理

1. **在每次模型调用之前**，处理器检查是否满足任何触发条件
2. 如果触发，它会找到一个安全的截断点，不会拆分工具调用/响应对
3. 旧消息使用轻量级 LLM 调用进行总结
4. 摘要替换旧消息，保留最近的上下文
5. Agent 使用压缩的历史记录继续运行

### 工具调用安全

处理器确保工具调用及其响应保持在一起：

```
Messages: [User, AI+ToolCall, ToolResponse, User, AI+ToolCall, ToolResponse, User]
                                           ↑ 安全截断点（完整对之间）
```

## 多个处理器

您可以链接多个历史记录处理器：

```python
from pydantic_deep import create_deep_agent
from pydantic_deep.processors import create_summarization_processor

# 多个处理器按顺序应用
agent = create_deep_agent(
    history_processors=[
        create_summarization_processor(trigger=("tokens", 100000)),
        # 根据需要添加更多处理器
    ],
)
```

## 最佳实践

1. **选择合适的阈值**：将触发阈值设置在模型上下文限制之下，以便为响应留出空间

2. **保留足够的上下文**：保留足够的最近消息，以便 Agent 理解当前任务

3. **监控摘要质量**：检查摘要是否保留了您的用例的重要上下文

4. **使用基于比例的触发器以实现可移植性**：当在具有不同上下文限制的模型之间切换时

## 下一步

- [结构化输出](structured-output.md) - 使用 Pydantic 模型进行类型安全的响应
- [流式传输](streaming.md) - 实时响应处理
- [人机回环](human-in-the-loop.md) - 审批工作流
