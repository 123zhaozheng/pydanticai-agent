# 流式传输

pydantic-deep 支持流式执行以进行实时进度监控。

## 基本流式传输

使用 `agent.iter()` 进行流式传输：

```python
import asyncio
from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend

async def main():
    agent = create_deep_agent()
    deps = DeepAgentDeps(backend=StateBackend())

    async with agent.iter("Create a Python module", deps=deps) as run:
        async for node in run:
            print(f"Node: {type(node).__name__}")

        result = run.result

    print(f"\nFinal output: {result.output}")

asyncio.run(main())
```

## 节点类型

在流式传输过程中，您将收到不同的节点类型：

```python
from pydantic_ai._agent_graph import (
    UserPromptNode,
    ModelRequestNode,
    CallToolsNode,
    End,
)

async with agent.iter(prompt, deps=deps) as run:
    async for node in run:
        if isinstance(node, UserPromptNode):
            print("📝 Processing user prompt...")

        elif isinstance(node, ModelRequestNode):
            print("🤖 Calling model...")

        elif isinstance(node, CallToolsNode):
            # 从响应中提取工具名称
            tools = []
            for part in node.model_response.parts:
                if hasattr(part, 'tool_name'):
                    tools.append(part.tool_name)

            if tools:
                print(f"🔧 Executing: {', '.join(tools)}")

        elif isinstance(node, End):
            print("✅ Completed!")
```

## 进度显示

显示进度指示器：

```python
import sys

async def run_with_progress(agent, prompt, deps):
    step = 0

    async with agent.iter(prompt, deps=deps) as run:
        async for node in run:
            step += 1
            node_type = type(node).__name__

            # 清除行并显示进度
            sys.stdout.write(f"\r[Step {step}] {node_type}...")
            sys.stdout.flush()

        print("\n")
        return run.result
```

## 工具调用详情

获取有关工具调用的详细信息：

```python
async with agent.iter(prompt, deps=deps) as run:
    async for node in run:
        if isinstance(node, CallToolsNode):
            for part in node.model_response.parts:
                if hasattr(part, 'tool_name'):
                    print(f"Tool: {part.tool_name}")
                    if hasattr(part, 'args'):
                        print(f"  Args: {part.args}")
```

## 实时输出

对于长时间运行的操作，显示中间结果：

```python
async def run_with_live_output(agent, prompt, deps):
    async with agent.iter(prompt, deps=deps) as run:
        async for node in run:
            if isinstance(node, CallToolsNode):
                for part in node.model_response.parts:
                    if hasattr(part, 'tool_name'):
                        tool = part.tool_name

                        # 显示特定于工具的输出
                        if tool == "write_todos":
                            print("\n📋 Updated todo list")
                        elif tool == "write_file":
                            path = part.args.get("path", "")
                            print(f"\n📝 Writing: {path}")
                        elif tool == "read_file":
                            path = part.args.get("path", "")
                            print(f"\n📖 Reading: {path}")

        return run.result
```

## Web 流式传输

对于使用服务器发送事件 (SSE) 的 Web 应用程序：

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json

app = FastAPI()

@app.get("/agent/stream")
async def stream_agent(prompt: str):
    async def event_generator():
        async with agent.iter(prompt, deps=deps) as run:
            async for node in run:
                node_type = type(node).__name__

                data = {"type": node_type}

                if isinstance(node, CallToolsNode):
                    tools = []
                    for part in node.model_response.parts:
                        if hasattr(part, 'tool_name'):
                            tools.append(part.tool_name)
                    data["tools"] = tools

                yield f"data: {json.dumps(data)}\n\n"

            # 发送最终结果
            yield f"data: {json.dumps({'type': 'complete', 'output': run.result.output})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
```

## 取消

取消正在运行的 Agent：

```python
import asyncio

async def run_with_timeout(agent, prompt, deps, timeout=60):
    try:
        async with asyncio.timeout(timeout):
            async with agent.iter(prompt, deps=deps) as run:
                async for node in run:
                    pass
                return run.result
    except asyncio.TimeoutError:
        print("Agent execution timed out")
        return None
```

## 使用统计

在流式传输期间跟踪 Token 使用情况：

```python
async with agent.iter(prompt, deps=deps) as run:
    async for node in run:
        pass

    result = run.result
    usage = result.usage()

    print(f"Input tokens: {usage.input_tokens}")
    print(f"Output tokens: {usage.output_tokens}")
    print(f"Total requests: {usage.requests}")
```

## 示例：进度条

使用 `rich` 进行美观的进度显示：

```python
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

async def run_with_rich_progress(agent, prompt, deps):
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Starting...", total=None)

        async with agent.iter(prompt, deps=deps) as run:
            async for node in run:
                node_type = type(node).__name__

                if isinstance(node, ModelRequestNode):
                    progress.update(task, description="🤖 Thinking...")
                elif isinstance(node, CallToolsNode):
                    tools = []
                    for part in node.model_response.parts:
                        if hasattr(part, 'tool_name'):
                            tools.append(part.tool_name)
                    if tools:
                        progress.update(
                            task,
                            description=f"🔧 {', '.join(tools)}"
                        )

            progress.update(task, description="✅ Complete!")
            return run.result
```

## 下一步

- [人机回环](human-in-the-loop.md) - 审批工作流
- [示例](../examples/index.md) - 更多示例
