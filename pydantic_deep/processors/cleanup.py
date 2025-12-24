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
    
    # Strategy:
    # 1. Identify all messages that contain stateful tool calls/returns.
    # 2. Find the index of the *last* group of such calls.
    # 3. Everything before that last group gets filtered.
    # 4. The last group and anything after it is preserved.
    
    # Track indices of messages containing our target tools
    target_tool_indices: set[int] = set()
    
    for i, msg in enumerate(messages):
        has_target_tool = False
        if isinstance(msg, ModelResponse):
            for part in msg.parts:
                if isinstance(part, ToolCallPart) and part.tool_name in TOOLS_TO_FILTER:
                    has_target_tool = True
                    break
        elif isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name in TOOLS_TO_FILTER:
                    has_target_tool = True
                    break
        
        if has_target_tool:
            target_tool_indices.add(i)
            
    # If no such tools found, return as is
    if not target_tool_indices:
        return messages
        
    # Find the start index of the "last group"
    # We define a "group" loosely here, but for simplicity/safety, let's just say:
    # We want to keep the *very last* interaction involving these tools.
    # So we find the max index.
    last_interaction_index = max(target_tool_indices)
    
    # However, a tool interaction is usually a pair (Call -> Return).
    # If the last thing is a Return, we probably want to keep its matching Call too.
    # Or simpler: just keep the last N *messages* regardless, as a safety buffer?
    # User asked: "Keep the last group... remove all above".
    
    # Safe approach:
    # Iterate through messages.
    # If a message index is < last_interaction_index AND contains a target tool => Filter it.
    # If a message index is >= last_interaction_index => Keep it (it's the last one).
    # Wait, "last group" implies if I did: Todo1, Todo2, Todo3. I want to keep Todo3.
    # So finding 'max' is correct for the very last one.
    
    # Let's verify if the last interaction is a Call or Result.
    # If it's a Result, we likely need to keep the preceding Call too which might be at index-1.
    # To be robust, let's set the "survival threshold" at the last 2-3 messages 
    # OR simply use the logic: "Filter unless it is the last occurrence".
    
    # Refined Logic:
    # We will filter a tool part IF:
    # It is NOT part of the last interaction sequence.
    # But figuring out "sequence" boundaries hard.
    
    # Let's stick to the user's specific request combined with my buffer Logic.
    # User said: "Keep the last set".
    # My "Buffer = 2" logic already does "Keep the last set" if the last set is at the end.
    # But if the last set was 5 messages ago, Buffer=2 would delete it? No, Buffer=2 preserves the TAIL.
    # If the user means "Keep the last occurrence of Todo even if it was 10 turns ago", that's different.
    # Assuming user means: "Allow one active/recent stateful tool interaction to remain in history, delete older ones."
    
    # Let's count how many times these tools appear.
    # We want to keep the tool parts only if they belong to the *last* time they appear in the list.
    
    # Actually, simpler interpretation of "Last Group":
    # Just find the index of the last message that has one of these tools.
    # Let's call it `last_idx`.
    # Any filtering logic ONLY applies to messages where index < last_idx - 1 (give it a small window of context).
    # If message index is close to `last_idx`, we preserve it.
    
    last_target_idx = -1
    if target_tool_indices:
        last_target_idx = max(target_tool_indices)
        
    for i, msg in enumerate(messages):
        # Determine if we should preserve this message's tool parts
        # We preserve if this message is part of the "last interaction"
        # We define "last interaction" as the message at last_target_idx AND its immediate predecessor (the Call)
        # So if i >= last_target_idx - 1, we keep it.
        
        should_preserve = False
        if target_tool_indices:
             if i >= last_target_idx - 1:
                 should_preserve = True
        
        # If we should preserve, just append and continue
        if should_preserve:
            new_messages.append(msg)
            continue

        # Otherwise, perform filtering as before
        if isinstance(msg, ModelResponse):
            new_parts = []
            has_filtered_parts = False  
            for part in msg.parts:
                if isinstance(part, ToolCallPart) and part.tool_name in TOOLS_TO_FILTER:
                    has_filtered_parts = True
                    continue
                new_parts.append(part)
            
            if has_filtered_parts:
                if not new_parts: continue
                try:
                    new_msg = msg.model_copy(update={"parts": new_parts})
                    new_messages.append(new_msg)
                except AttributeError:
                    msg.parts = new_parts
                    new_messages.append(msg)
            else:
                new_messages.append(msg)
                
        elif isinstance(msg, ModelRequest):
            new_parts = []
            has_filtered_parts = False 
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name in TOOLS_TO_FILTER:
                    has_filtered_parts = True
                    continue
                new_parts.append(part)
            
            if has_filtered_parts:
                if not new_parts: continue
                try:
                    new_msg = msg.model_copy(update={"parts": new_parts})
                    new_messages.append(new_msg)
                except AttributeError:
                    msg.parts = new_parts
                    new_messages.append(msg)
            else:
                new_messages.append(msg)
        else:
            new_messages.append(msg)
            
    return new_messages
