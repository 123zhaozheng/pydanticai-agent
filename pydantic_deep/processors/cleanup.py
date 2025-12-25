"""Cleanup processors for message history."""

from __future__ import annotations
from typing import TYPE_CHECKING, Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart
)
from pydantic_ai.tools import RunContext

if TYPE_CHECKING:
    from pydantic_deep.deps import DeepAgentDeps


def deduplicate_stateful_tools_processor(
    ctx: RunContext[Any],  # RunContext with Any to avoid circular import
    messages: list[ModelMessage]
) -> list[ModelMessage]:
    """
    Remove old tool calls and returns for stateful tools, but keep recent ones.

    These tools modify state that is fully reflected in the system prompt,
    so keeping their OLD history in messages wastes tokens and creates confusion.

    Tools filtered (keep only last 2 occurrences):
    - write_todos: Current todos are shown in system prompt
    - read_todos: Same information as system prompt
    - list_skills: Skill list is shown in system prompt

    Tools NOT filtered (preserved):
    - load_skill: Full instructions are only in conversation history, NOT in system prompt
    - read_skill_resource: Resource content is only in conversation history

    Strategy:
    1. Track occurrences of filtered tools
    2. Keep only the LAST 2 occurrences of each filtered tool
    3. Remove older occurrences to save tokens
    4. This prevents infinite loops while still cleaning up old history
    """

    # Tools to filter (keep only recent ones)
    # Note: load_skill is NOT here because its full instructions are not in system prompt
    TOOLS_TO_FILTER = {
        "write_todos",
        "read_todos",
        "list_skills",
    }

    # Count occurrences of each filtered tool from the end
    tool_call_positions: dict[str, list[int]] = {tool: [] for tool in TOOLS_TO_FILTER}
    tool_return_positions: dict[str, list[int]] = {tool: [] for tool in TOOLS_TO_FILTER}

    # First pass: find all positions
    for i, msg in enumerate(messages):
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart) and part.tool_name in TOOLS_TO_FILTER:
                    tool_call_positions[part.tool_name].append(i)
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name in TOOLS_TO_FILTER:
                    tool_return_positions[part.tool_name].append(i)

    # Determine which positions to keep (last 2 occurrences)
    positions_to_keep_calls = set()
    positions_to_keep_returns = set()

    for tool_name in TOOLS_TO_FILTER:
        # Keep last 2 calls
        if len(tool_call_positions[tool_name]) > 2:
            positions_to_keep_calls.update(tool_call_positions[tool_name][-2:])
        else:
            positions_to_keep_calls.update(tool_call_positions[tool_name])

        # Keep last 2 returns
        if len(tool_return_positions[tool_name]) > 2:
            positions_to_keep_returns.update(tool_return_positions[tool_name][-2:])
        else:
            positions_to_keep_returns.update(tool_return_positions[tool_name])

    new_messages: list[ModelMessage] = []

    for msg in messages:
        if isinstance(msg, ModelResponse):
            # Filter out tool calls for stateful tools
            new_parts = []
            for part in msg.parts:
                # Keep everything except ToolCallPart for filtered tools
                if isinstance(part, ToolCallPart) and part.tool_name in TOOLS_TO_FILTER:
                    continue
                new_parts.append(part)

            # Only include message if it has remaining parts
            if new_parts:
                try:
                    new_msg = msg.model_copy(update={"parts": new_parts})
                    new_messages.append(new_msg)
                except AttributeError:
                    # Fallback if model_copy is not available
                    msg.parts = new_parts
                    new_messages.append(msg)

        elif isinstance(msg, ModelRequest):
            # Filter out tool returns for stateful tools
            new_parts = []
            for part in msg.parts:
                # Keep everything except ToolReturnPart for filtered tools
                if isinstance(part, ToolReturnPart) and part.tool_name in TOOLS_TO_FILTER:
                    continue
                new_parts.append(part)

            # Only include message if it has remaining parts
            if new_parts:
                try:
                    new_msg = msg.model_copy(update={"parts": new_parts})
                    new_messages.append(new_msg)
                except AttributeError:
                    # Fallback if model_copy is not available
                    msg.parts = new_parts
                    new_messages.append(msg)
        else:
            # Keep all other message types as-is
            new_messages.append(msg)

    # CRITICAL: PydanticAI requires message history to end with ModelRequest
    # If we accidentally removed the last ModelRequest, add it back
    if new_messages and not isinstance(new_messages[-1], ModelRequest):
        # Find the last ModelRequest in original messages and append it
        for msg in reversed(messages):
            if isinstance(msg, ModelRequest):
                new_messages.append(msg)
                break

    return new_messages
