# 人机回环 (HITL)

pydantic-deep 支持通过 `interrupt_on` 配置要求对敏感操作进行人工审批。

## 配置

```python
agent = create_deep_agent(
    interrupt_on={
        "execute": True,       # Shell 命令执行
        "write_file": True,    # 创建/覆盖文件
        "edit_file": True,     # 修改现有文件
    }
)
```

## 工作原理

当工具需要审批时：

1. Agent 调用工具
2. 工具执行被推迟
3. 返回 `DeferredToolRequests` 而不是结果
4. 您进行审核并批准/拒绝
5. 使用决策通过后的结果继续执行

## 示例流程

```python
import asyncio
from pydantic_deep import create_deep_agent, DeepAgentDeps, StateBackend

async def main():
    agent = create_deep_agent(
        interrupt_on={
            "execute": True,
            "write_file": True,
        }
    )

    deps = DeepAgentDeps(backend=StateBackend())

    # 初始运行
    result = await agent.run(
        "Create a script that prints hello world and run it",
        deps=deps,
    )

    # 检查是否需要审批
    if hasattr(result, 'deferred_tool_calls'):
        print("Approval needed for:")
        for call in result.deferred_tool_calls:
            print(f"  - {call.tool_name}: {call.args}")

        # 在实际应用中，您会提示用户
        # 在此示例中，全部批准
        approved = result.approve_all()

        # 使用批准结果继续
        result = await agent.run(
            approved,
            deps=deps,
            message_history=result.all_messages(),
        )

    print(result.output)

asyncio.run(main())
```

## 选择性审批

您可以批准或拒绝单个工具调用：

```python
if hasattr(result, 'deferred_tool_calls'):
    decisions = []

    for call in result.deferred_tool_calls:
        if call.tool_name == "execute":
            # 批准前审查命令
            if "rm" in call.args.get("command", ""):
                decisions.append(call.deny("Destructive command not allowed"))
            else:
                decisions.append(call.approve())
        elif call.tool_name == "write_file":
            # 总是批准写入
            decisions.append(call.approve())

    # 使用决策结果继续
    result = await agent.run(
        decisions,
        deps=deps,
        message_history=result.all_messages(),
    )
```

## 交互式审批

对于 CLI 应用程序：

```python
async def interactive_run(agent, prompt, deps):
    result = await agent.run(prompt, deps=deps)

    while hasattr(result, 'deferred_tool_calls'):
        for call in result.deferred_tool_calls:
            print(f"\nTool: {call.tool_name}")
            print(f"Args: {call.args}")

            response = input("Approve? [y/n]: ").lower()
            if response == 'y':
                call.approve()
            else:
                reason = input("Reason for denial: ")
                call.deny(reason)

        result = await agent.run(
            result.get_decisions(),
            deps=deps,
            message_history=result.all_messages(),
        )

    return result
```

## Web 应用程序集成

对于具有异步审批的 Web 应用：

```python
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()
pending_approvals = {}

@app.post("/agent/run")
async def run_agent(prompt: str):
    result = await agent.run(prompt, deps=deps)

    if hasattr(result, 'deferred_tool_calls'):
        # 存储以供稍后审批
        request_id = generate_id()
        pending_approvals[request_id] = {
            "result": result,
            "calls": result.deferred_tool_calls,
        }
        return {
            "status": "pending_approval",
            "request_id": request_id,
            "tools": [
                {"name": c.tool_name, "args": c.args}
                for c in result.deferred_tool_calls
            ]
        }

    return {"status": "complete", "output": result.output}

@app.post("/agent/approve/{request_id}")
async def approve(request_id: str, decisions: list[dict]):
    pending = pending_approvals.pop(request_id)

    for i, decision in enumerate(decisions):
        call = pending["calls"][i]
        if decision["approved"]:
            call.approve()
        else:
            call.deny(decision.get("reason", "Denied"))

    result = await agent.run(
        pending["result"].get_decisions(),
        deps=deps,
        message_history=pending["result"].all_messages(),
    )

    return {"status": "complete", "output": result.output}
```

## 默认行为

默认情况下：

| 工具 | 需要审批 |
|------|-------------------|
| `execute` | 是 (如果启用) |
| `write_file` | 否 |
| `edit_file` | 否 |
| `task` | 否 |
| 其他工具 | 否 |

!!! tip
    即使没有审批，`execute` 也仅在沙箱后端中工作。

## 最佳实践

### 1. 始终审查执行

```python
interrupt_on={"execute": True}
```

Shell 命令可能很危险。始终审查。

### 2. 生产环境中审查写入

```python
interrupt_on={
    "write_file": True,
    "edit_file": True,
}
```

在生产环境中，审查文件修改。

### 3. 记录所有审批

```python
import logging

logger = logging.getLogger(__name__)

for call in result.deferred_tool_calls:
    logger.info(f"Approving: {call.tool_name} with {call.args}")
    call.approve()
```

### 4. 设置超时

```python
import asyncio

try:
    approval = await asyncio.wait_for(
        get_user_approval(call),
        timeout=300,  # 5 分钟超时
    )
except asyncio.TimeoutError:
    call.deny("Approval timeout")
```

## 下一步

- [子智能体](subagents.md) - 任务委托
- [流式传输](streaming.md) - 实时输出
- [示例](../examples/index.md) - 更多示例
