# Processors API

用于管理对话上下文的历史记录处理器。

## create_summarization_processor

::: pydantic_deep.processors.create_summarization_processor
    options:
      show_source: false

### 签名

```python
def create_summarization_processor(
    model: str = "openai:gpt-4.1",
    trigger: ContextSize | list[ContextSize] | None = ("tokens", 170000),
    keep: ContextSize = ("messages", 20),
    max_input_tokens: int | None = None,
    token_counter: TokenCounter | None = None,
    summary_prompt: str | None = None,
) -> SummarizationProcessor
```

### 参数

| 参数 | 类型 | 默认值 | 描述 |
|-----------|------|---------|-------------|
| `model` | `str` | `"openai:gpt-4.1"` | 用于生成摘要的模型 |
| `trigger` | `ContextSize \| list[ContextSize] \| None` | `("tokens", 170000)` | 何时触发摘要 |
| `keep` | `ContextSize` | `("messages", 20)` | 保留多少上下文 |
| `max_input_tokens` | `int \| None` | `None` | 最大 Token (分数触发器需要) |
| `token_counter` | `TokenCounter \| None` | `None` | 自定义 Token 计数函数 |
| `summary_prompt` | `str \| None` | `None` | 自定义摘要提示词 |

### 返回值

`SummarizationProcessor` - 配置好的处理器实例。

### 示例

```python
from pydantic_deep import create_deep_agent
from pydantic_deep.processors import create_summarization_processor

processor = create_summarization_processor(
    trigger=("tokens", 100000),
    keep=("messages", 20),
)

agent = create_deep_agent(history_processors=[processor])
```

---

## SummarizationProcessor

::: pydantic_deep.processors.SummarizationProcessor
    options:
      show_source: false

### 定义

```python
@dataclass
class SummarizationProcessor:
    model: str
    trigger: ContextSize | list[ContextSize] | None = None
    keep: ContextSize = ("messages", 20)
    token_counter: TokenCounter = _count_tokens_approximately
    summary_prompt: str = DEFAULT_SUMMARY_PROMPT
    max_input_tokens: int | None = None
    trim_tokens_to_summarize: int | None = 4000
```

### 属性

| 属性 | 类型 | 描述 |
|-----------|------|-------------|
| `model` | `str` | 用于生成摘要的模型 |
| `trigger` | `ContextSize \| list[ContextSize] \| None` | 触发摘要的阈值 |
| `keep` | `ContextSize` | 摘要后保留多少上下文 |
| `token_counter` | `TokenCounter` | 计算消息中 Token 的函数 |
| `summary_prompt` | `str` | 生成摘要的提示词模板 |
| `max_input_tokens` | `int \| None` | 最大输入 Token (分数触发器需要) |
| `trim_tokens_to_summarize` | `int \| None` | 生成摘要时包含的最大 Token |

### 方法

#### \_\_call\_\_

```python
async def __call__(self, messages: list[ModelMessage]) -> list[ModelMessage]
```

处理消息并在需要时进行总结。这是由 pydantic-ai 的历史记录处理器机制自动调用的。

### 示例

```python
from pydantic_deep.processors import SummarizationProcessor

processor = SummarizationProcessor(
    model="openai:gpt-4.1",
    trigger=[
        ("messages", 50),
        ("tokens", 100000),
    ],
    keep=("messages", 10),
    trim_tokens_to_summarize=4000,
)
```

---

## 类型别名

### ContextSize

```python
ContextFraction = tuple[Literal["fraction"], float]
ContextTokens = tuple[Literal["tokens"], int]
ContextMessages = tuple[Literal["messages"], int]

ContextSize = ContextFraction | ContextTokens | ContextMessages
```

指定上下文大小阈值：

- `("messages", N)` - 消息数量
- `("tokens", N)` - Token 数量
- `("fraction", F)` - `max_input_tokens` 的分数 (0 < F <= 1)

### TokenCounter

```python
TokenCounter = Callable[[Sequence[ModelMessage]], int]
```

自定义 Token 计数的函数类型。

---

## 常量

| 常量 | 值 | 描述 |
|----------|-------|-------------|
| `DEFAULT_SUMMARY_PROMPT` | (see source) | 摘要的默认提示词模板 |

## 下一步

- [Agent API](agent.md) - Agent 工厂和配置
- [Types API](types.md) - 类型定义
