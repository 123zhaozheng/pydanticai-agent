"""Todo toolset for task planning and tracking."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset

from pydantic_deep.deps import DeepAgentDeps
from pydantic_deep.types import Todo


class TodoItem(BaseModel):
    """A todo item for the write_todos tool."""

    content: str = Field(
        ..., description="The task description in imperative form (e.g., 'Implement feature X')"
    )
    status: Literal["pending", "in_progress", "completed"] = Field(
        ..., description="Task status: pending, in_progress, or completed"
    )
    active_form: str = Field(
        ...,
        description="Present continuous form during execution (e.g., 'Implementing feature X')",
    )


TODO_TOOL_DESCRIPTION = """
使用此工具为您当前的会话创建和管理结构化的任务列表。
这有助于您跟踪进度、组织复杂任务并展示您的严谨性。

## 何时使用此工具
在以下场景使用：
1. 复杂的多步骤任务 - 当一个任务需要3个或更多步骤时
2. 非平凡任务 - 需要仔细规划的任务
3. 用户提供多个任务 - 当用户提供一系列待办事项时
4. 收到新指令后 - 将用户需求捕捉为待办事项
5. 开始任务时 - 在开始工作前将其标记为进行中 (in_progress)
6. 完成任务后 - 立即将其标记为已完成 (completed)

## 任务状态
- pending: 任务尚未开始
- in_progress: 当前正在进行 (限制一次只能有一个)
- completed: 任务成功完成

## 重要
-任何时候只能有 **一个** 任务处于 in_progress 状态
- 完成任务后 **立即** 标记为完成 (不要批量完成)
- 如果遇到阻碍，保持任务为 in_progress 并为阻碍创建一个新任务
"""

TODO_SYSTEM_PROMPT = """
## 任务管理

你可以使用 `write_todos` 工具来跟踪你的任务。
经常使用它来：
- 在开始前规划复杂任务
- 向用户展示进度
- 跟踪已完成和待处理的事项

在处理任务时：
1. 将复杂任务分解为更小的步骤
2. 一次只标记一个任务为进行中
3. 完成后立即标记任务为已完成
"""


READ_TODO_DESCRIPTION = """
读取当前的待办事项列表状态。

使用此工具在以下情况前检查所有任务的当前状态：
- 决定接下来做什么
- 更新任务状态
- 向用户报告进度

返回所有待办事项及其当前状态 (pending, in_progress, completed)。
"""


def create_todo_toolset(id: str | None = None) -> FunctionToolset[DeepAgentDeps]:
    """Create a todo toolset for task management.

    Args:
        id: Optional unique ID for the toolset.

    Returns:
        FunctionToolset with read_todos and write_todos tools.
    """
    toolset: FunctionToolset[DeepAgentDeps] = FunctionToolset(id=id)

    @toolset.tool(description=READ_TODO_DESCRIPTION)
    async def read_todos(ctx: RunContext[DeepAgentDeps]) -> str:  # pragma: no cover
        """Read the current todo list.

        Returns the current state of all todos with their status.
        """
        if not ctx.deps.todos:
            return "No todos in the list. Use write_todos to create tasks."

        lines = ["Current todos:"]
        for i, todo in enumerate(ctx.deps.todos, 1):
            status_icon = {
                "pending": "[ ]",
                "in_progress": "[*]",
                "completed": "[x]",
            }.get(todo.status, "[ ]")
            lines.append(f"{i}. {status_icon} {todo.content}")

        # Add summary
        counts = {"pending": 0, "in_progress": 0, "completed": 0}
        for todo in ctx.deps.todos:
            counts[todo.status] += 1

        lines.append("")
        lines.append(
            f"Summary: {counts['completed']} completed, "
            f"{counts['in_progress']} in progress, "
            f"{counts['pending']} pending"
        )

        return "\n".join(lines)

    @toolset.tool
    async def write_todos(  # pragma: no cover
        ctx: RunContext[DeepAgentDeps],
        todos: list[TodoItem],
    ) -> str:
        """Update the todo list with new items.

        Use this tool to create and manage a structured task list.
        This helps track progress and organize complex tasks.

        Args:
            todos: List of todo items with content, status, and active_form.
        """
        # Convert to internal Todo format
        ctx.deps.todos = [
            Todo(content=t.content, status=t.status, active_form=t.active_form) for t in todos
        ]

        # Count by status
        counts = {"pending": 0, "in_progress": 0, "completed": 0}
        for todo in ctx.deps.todos:
            counts[todo.status] += 1

        return (
            f"Updated {len(todos)} todos: "
            f"{counts['completed']} completed, "
            f"{counts['in_progress']} in progress, "
            f"{counts['pending']} pending"
        )

    return toolset


def get_todo_system_prompt(deps: DeepAgentDeps) -> str:
    """Generate dynamic system prompt section for todos.

    Args:
        deps: The agent dependencies containing todos.

    Returns:
        System prompt section with current todos, or empty string if no todos.
    """
    if not deps.todos:
        return TODO_SYSTEM_PROMPT

    lines = [TODO_SYSTEM_PROMPT, "", "## Current Todos"]

    for todo in deps.todos:
        status_icon = {
            "pending": "[ ]",
            "in_progress": "[*]",
            "completed": "[x]",
        }.get(todo.status, "[ ]")
        lines.append(f"- {status_icon} {todo.content}")

    return "\n".join(lines)


# Alias for convenience
TodoToolset = create_todo_toolset
