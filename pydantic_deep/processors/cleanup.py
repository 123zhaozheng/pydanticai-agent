"""Cleanup processors for message history."""

from __future__ import annotations
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.messages import (
    ModelMessage, 
    ModelRequest, 
    ModelResponse, 
    ToolCallPart, 
    ToolReturnPart
)

from pydantic_deep.deps import DeepAgentDeps


def deduplicate_stateful_tools_processor(
    ctx: RunContext[DeepAgentDeps], 
    messages: list[ModelMessage]
) -> list[ModelMessage]:
    """
    Remove messages related to stateful tools (todos, skills) 
    whose effects are already reflected in the system prompt.
    
    This reduces token usage and prevents "duplicate context" confusion 
    where the LLM sees both the history of changes and the final state.
    
    Tools filtered:
    - write_todos
    - read_todos
    - load_skill
    - list_skills
    """
    
    # Tools to filter
    # These tools modify state that is fully visible in the System Prompt
    TOOLS_TO_FILTER = {
        "write_todos", 
        "read_todos", 
        "load_skill", 
        "list_skills"
    }
    
    new_messages: list[ModelMessage] = []
    
    for msg in messages:
        if isinstance(msg, ModelResponse):
            # Filter ToolCallParts
            new_parts = []
            has_filtered_parts = False
            
            for part in msg.parts:
                if isinstance(part, ToolCallPart) and part.tool_name in TOOLS_TO_FILTER:
                    has_filtered_parts = True
                    continue
                new_parts.append(part)
            
            # If we filtered parts, we need to create a new message
            if has_filtered_parts:
                # If no parts left (empty message), skip it completely
                if not new_parts:
                    continue
                
                # Copy message with new parts
                # Note: ModelResponse is a Pydantic model (dataclass-like)
                # We use model_copy with update
                try:
                    # Pydantic V2
                    new_msg = msg.model_copy(update={"parts": new_parts})
                    new_messages.append(new_msg)
                except AttributeError:
                    # Fallback if specific version differences
                    msg.parts = new_parts
                    new_messages.append(msg)
            else:
                # No changes, keep original
                new_messages.append(msg)
                
        elif isinstance(msg, ModelRequest):
            # Filter ToolReturnParts
            new_parts = []
            has_filtered_parts = False
            
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name in TOOLS_TO_FILTER:
                    has_filtered_parts = True
                    continue
                new_parts.append(part)
            
            if has_filtered_parts:
                if not new_parts:
                    continue
                
                try:
                    new_msg = msg.model_copy(update={"parts": new_parts})
                    new_messages.append(new_msg)
                except AttributeError:
                    msg.parts = new_parts
                    new_messages.append(msg)
            else:
                new_messages.append(msg)
        else:
            # Other message types (e.g. SystemPrompt)
            new_messages.append(msg)
            
    return new_messages
