# 结构化输出

pydantic-deep 支持通过 Pydantic 模型进行结构化输出，允许您从 Agent 获得类型安全的响应。

## 基本用法

使用 `output_type` 参数指定预期的响应格式：

```python
from pydantic import BaseModel
from pydantic_deep import create_deep_agent, create_default_deps

class TaskAnalysis(BaseModel):
    summary: str
    priority: str
    estimated_hours: float
    tags: list[str]

# 创建具有结构化输出的 Agent
agent = create_deep_agent(output_type=TaskAnalysis)

deps = create_default_deps()
result = await agent.run(
    "Analyze this task: implement user authentication with OAuth",
    deps=deps,
)

# 对响应的类型安全访问
print(result.output.summary)
print(result.output.priority)
print(result.output.estimated_hours)
```

## 复杂模型

您可以使用嵌套的 Pydantic 模型进行复杂的响应：

```python
from pydantic import BaseModel, Field

class Step(BaseModel):
    description: str
    estimated_time: str
    dependencies: list[str] = Field(default_factory=list)

class ProjectPlan(BaseModel):
    title: str
    overview: str
    steps: list[Step]
    total_estimated_hours: float
    risks: list[str]

agent = create_deep_agent(output_type=ProjectPlan)

result = await agent.run(
    "Create a plan for building a REST API with authentication",
    deps=deps,
)

for i, step in enumerate(result.output.steps, 1):
    print(f"{i}. {step.description} ({step.estimated_time})")
```

## 可选字段

对可能并不总是存在的字段使用 `Optional` 类型：

```python
from pydantic import BaseModel
from typing import Optional

class CodeReview(BaseModel):
    file_path: str
    issues_found: int
    severity: str
    suggestions: list[str]
    security_concerns: Optional[str] = None

agent = create_deep_agent(output_type=CodeReview)
```

## 验证

Pydantic 自动验证 LLM 的响应：

```python
from pydantic import BaseModel, Field, field_validator

class Rating(BaseModel):
    score: int = Field(ge=1, le=10)
    explanation: str

    @field_validator("explanation")
    @classmethod
    def explanation_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Explanation cannot be empty")
        return v

agent = create_deep_agent(output_type=Rating)
```

## 与工具结合

结构化输出与所有 Agent 工具一起工作：

```python
from pydantic import BaseModel
from pydantic_deep import create_deep_agent, create_default_deps, StateBackend

class FileAnalysis(BaseModel):
    file_count: int
    total_lines: int
    languages_detected: list[str]
    summary: str

agent = create_deep_agent(
    output_type=FileAnalysis,
    include_filesystem=True,  # Agent 可以使用文件工具
)

# Agent 读取文件并返回结构化分析
deps = create_default_deps(backend=StateBackend())
result = await agent.run(
    "Analyze the files in the /src directory",
    deps=deps,
)

print(f"Found {result.output.file_count} files")
print(f"Languages: {', '.join(result.output.languages_detected)}")
```

## 类型推断

当使用 `output_type` 时，Agent 的返回类型会被正确推断：

```python
from pydantic import BaseModel
from pydantic_deep import create_deep_agent

class Summary(BaseModel):
    title: str
    content: str

# Agent 类型为 Agent[DeepAgentDeps, Summary]
agent = create_deep_agent(output_type=Summary)

result = await agent.run("Summarize this document", deps=deps)
# result.output 类型为 Summary
reveal_type(result.output)  # Summary
```

## 枚举约束

使用枚举来约束可能的值：

```python
from enum import Enum
from pydantic import BaseModel

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskClassification(BaseModel):
    category: str
    priority: Priority
    assigned_team: str

agent = create_deep_agent(output_type=TaskClassification)
```

## ResponseFormat 类型别名

为了方便起见，`ResponseFormat` 被导出为别名：

```python
from pydantic_deep import ResponseFormat

# ResponseFormat 是 pydantic-ai 的 OutputSpec 的别名
# 将其用于代码中的类型提示
def process_output(output: ResponseFormat) -> None:
    ...
```

## 最佳实践

1. **保持模型专注**：为每个任务创建特定的模型，而不是一个大模型

2. **使用 Field 描述**：帮助 LLM 理解预期内容：
   ```python
   class Analysis(BaseModel):
       summary: str = Field(description="A 2-3 sentence summary")
       confidence: float = Field(ge=0, le=1, description="Confidence score 0-1")
   ```

3. **在指令中提供示例**：使用示例输出引导 LLM：
   ```python
   agent = create_deep_agent(
       output_type=Analysis,
       instructions="""
       Analyze the given text and return structured data.
       Example output structure:
       - summary: Brief overview of the content
       - confidence: How confident you are in the analysis
       """
   )
   ```

4. **处理验证错误**：将 Agent 调用包装在 try/except 中以处理验证失败

## 下一步

- [历史记录处理器](processors.md) - 管理对话上下文
- [流式传输](streaming.md) - 实时响应处理
- [示例](../examples/index.md) - 更多用法示例
