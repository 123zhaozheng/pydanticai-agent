# 基本用法

此示例演示了 pydantic-deep 的基本功能。

## 源代码

:material-file-code: `examples/basic_usage.py`

## 概览

此示例展示了：

- 创建 deep agent
- 使用内存 StateBackend
- 用于规划的 Todo 工具集
- 用于文件操作的文件系统工具集

## 完整示例

```python
"""Basic usage example for pydantic-deep."""

import asyncio
from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend


async def main():
    # 使用默认设置创建 deep agent
    # 包括：TodoToolset, FilesystemToolset, SubAgentToolset, SkillsToolset
    agent = create_deep_agent(
        model="openai:gpt-4.1",
        instructions="""
        You are a helpful coding assistant.
        When given complex tasks, break them down using the todo list.
        """,
    )

    # 使用内存存储创建依赖项
    deps = DeepAgentDeps(backend=StateBackend())

    # 运行 Agent
    result = await agent.run(
        """
        Create a simple Python calculator module with:
        1. add, subtract, multiply, divide functions
        2. A main function that demonstrates usage
        3. Save it to /src/calculator.py
        """,
        deps=deps,
    )

    # 打印 Agent 的响应
    print("Agent Response:")
    print("=" * 50)
    print(result.output)

    # 检查创建了哪些文件
    print("\nFiles Created:")
    print("=" * 50)
    for path in sorted(deps.backend.files.keys()):
        print(f"  {path}")

    # 显示创建文件的内容
    for path in sorted(deps.backend.files.keys()):
        print(f"\n--- {path} ---")
        content = deps.backend.read(path)
        print(content)

    # 显示 todo 列表状态
    print("\nTodo List:")
    print("=" * 50)
    for todo in deps.todos:
        status_icon = {
            "pending": "[ ]",
            "in_progress": "[*]",
            "completed": "[x]",
        }.get(todo.status, "[ ]")
        print(f"  {status_icon} {todo.content}")

    # 显示使用统计
    usage = result.usage()
    print(f"\nUsage Statistics:")
    print(f"  Input tokens: {usage.input_tokens}")
    print(f"  Output tokens: {usage.output_tokens}")
    print(f"  Total requests: {usage.requests}")


if __name__ == "__main__":
    asyncio.run(main())
```

## 运行示例

```bash
export ANTHROPIC_API_KEY=your-api-key
uv run python examples/basic_usage.py
```

## 预期输出

```
Agent Response:
==================================================
I'll create a calculator module for you. Let me break this down...

Files Created:
==================================================
  /src/calculator.py

--- /src/calculator.py ---
     1  """Simple calculator module."""
     2
     3  def add(a: float, b: float) -> float:
     4      """Add two numbers."""
     5      return a + b
     6
     7  def subtract(a: float, b: float) -> float:
     8      """Subtract b from a."""
     9      return a - b
    10
    11  def multiply(a: float, b: float) -> float:
    12      """Multiply two numbers."""
    13      return a * b
    14
    15  def divide(a: float, b: float) -> float:
    16      """Divide a by b."""
    17      if b == 0:
    18          raise ValueError("Cannot divide by zero")
    19      return a / b
    20
    21  def main():
    22      """Demonstrate calculator usage."""
    23      print(f"10 + 5 = {add(10, 5)}")
    24      print(f"10 - 5 = {subtract(10, 5)}")
    25      print(f"10 * 5 = {multiply(10, 5)}")
    26      print(f"10 / 5 = {divide(10, 5)}")
    27
    28  if __name__ == "__main__":
    29      main()

Todo List:
==================================================
  [x] Create calculator module structure
  [x] Implement arithmetic functions
  [x] Add main demonstration function
  [x] Save to /src/calculator.py

Usage Statistics:
  Input tokens: 1234
  Output tokens: 567
  Total requests: 3
```

## 关键概念

### Agent 创建

```python
agent = create_deep_agent(
    model="openai:gpt-4.1",  # LLM 模型
    instructions="...",                           # 系统提示词
)
```

Agent 创建时启用了所有默认工具集。

### 依赖项

```python
deps = DeepAgentDeps(backend=StateBackend())
```

- `StateBackend` 将文件存储在内存中
- `deps.backend.files` - 所有文件的字典
- `deps.todos` - todo 项列表

### 运行

```python
result = await agent.run(prompt, deps=deps)
```

- `result.output` - Agent 的文本响应
- `result.usage()` - Token 使用统计
- `result.all_messages()` - 完整对话历史

### 访问文件

```python
# 列出所有文件
deps.backend.files.keys()

# 读取文件（带行号）
deps.backend.read("/src/calculator.py")

# 直接写入文件
deps.backend.write("/test.py", "print('hello')")
```

## 变体

### 不使用规划

```python
agent = create_deep_agent(include_todo=False)
```

### 使用自定义指令

```python
agent = create_deep_agent(
    instructions="""
    You are a Python expert specializing in clean code.
    Always use type hints and docstrings.
    Follow PEP 8 style guidelines.
    """
)
```

### 无 API 测试

```python
from pydantic_ai.models.test import TestModel

agent = create_deep_agent(model=TestModel())
```

## 下一步

- [文件系统示例](filesystem.md) - 真实文件操作
- [技能示例](skills.md) - 使用技能
- [概念：Agent](../concepts/agents.md) - 深入研究
