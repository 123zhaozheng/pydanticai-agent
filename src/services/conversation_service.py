"""Service for managing conversations and message persistence."""

import json
from typing import Any, AsyncGenerator

from sqlalchemy.orm import Session
from sqlalchemy.future import select
from sqlalchemy import desc

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
    ToolCallPart,
    ToolReturnPart,
)

from src.models.conversations import Conversation, Message
from src.models.tools_skills import McpTool
from pydantic_deep.deps import DeepAgentDeps
from pydantic_deep.types import Todo

class ConversationService:
    """Service to handle conversation logic, history persistence, and state management."""

    def __init__(self, session: Session):
        self.session = session

    async def chat_stream(
        self,
        conversation_id: int,
        user_message: str,
        user_id: int,
        deps: DeepAgentDeps,
        agent: Any,  # Typed Agent[DeepAgentDeps, str]
    ) -> AsyncGenerator[str, None]:
        """
        Execute agent with streaming and real-time event-based persistence.
        
        Orchestration Flow:
        1. Load History & State (Hydration)
        2. Stream Events & Persist in Real-Time
        3. Save Final State (Dehydration)
        4. Yield Text to UI
        """
        # 1. Validation & Hydration
        conv = await self.get_conversation(conversation_id, user_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")
            
        # Hydrate state (Todos) from DB
        if conv.state and "todos" in conv.state:
            deps.todos = [
                Todo(**t) for t in conv.state["todos"]
            ]
            
        # Load message history
        history = await self.get_history(conversation_id)
        
        # Determine next step_order
        step_order = self._get_next_step_order(conversation_id)
        
        # 2. Persist User Message (Immediate)
        user_msg = Message(
            conversation_id=conversation_id,
            step_order=step_order,
            role='user',
            content=user_message
        )
        self.session.add(user_msg)
        self.session.commit()
        step_order += 1
        
        # 3. Running the Stream with Event-Based Persistence
        from pydantic_ai import (
            FunctionToolCallEvent,
            FunctionToolResultEvent,
            TextPartDelta,
            PartDeltaEvent,
        )
        
        # Track assistant response text chunks
        assistant_text_chunks = []
        current_model_tool_calls = []  # Track tool calls in current response
        
        async with agent.run_stream(
            user_message,
            deps=deps,
            message_history=history
        ) as stream:
            
            async for event in stream:
                # A. Stream text output to frontend
                if isinstance(event, PartDeltaEvent):
                    if isinstance(event.delta, TextPartDelta):
                        chunk = event.delta.content_delta
                        assistant_text_chunks.append(chunk)
                        yield chunk
                
                # B. Capture Tool Calls (Real-time)
                elif isinstance(event, FunctionToolCallEvent):
                    # Save tool call metadata
                    tool_call_data = {
                        "name": event.part.tool_name,
                        "args": event.part.args,
                        "tool_call_id": event.part.tool_call_id
                    }
                    current_model_tool_calls.append(tool_call_data)
                    
                    # Note: We'll save the ModelResponse with tool calls when we're sure
                    # it's complete (after all tool calls in this batch)
                
                # C. Capture Tool Returns (Real-time)
                elif isinstance(event, FunctionToolResultEvent):
                    # If this is the first tool return and we have pending tool calls,
                    # save the ModelResponse first
                    if current_model_tool_calls:
                        model_response_msg = Message(
                            conversation_id=conversation_id,
                            step_order=step_order,
                            role='model',
                            content="",  # Model made tool calls, no text yet
                            tool_calls=current_model_tool_calls
                        )
                        self.session.add(model_response_msg)
                        self.session.commit()
                        step_order += 1
                        current_model_tool_calls = []  # Clear after saving
                    
                    # Save the tool return
                    tool_return_msg = Message(
                        conversation_id=conversation_id,
                        step_order=step_order,
                        role='tool-return',
                        tool_name=event.part.tool_name,
                        tool_call_id=event.part.tool_call_id,
                        tool_return_content=str(event.part.content)
                    )
                    self.session.add(tool_return_msg)
                    self.session.commit()
                    step_order += 1
        
        # 4. Post-Stream: Save Final Assistant Response (if any text)
        if assistant_text_chunks:
            final_text = "".join(assistant_text_chunks)
            final_msg = Message(
                conversation_id=conversation_id,
                step_order=step_order,
                role='model',
                content=final_text,
                tool_calls=None  # Final response is pure text
            )
            self.session.add(final_msg)
            self.session.commit()
        
        # 5. Persist Final State (Dehydration)
        # DeepAgentDeps.todos has been mutated by tools during execution
        await self.save_deps_state(conversation_id, deps)

    def _get_next_step_order(self, conversation_id: int) -> int:
        """Helper to find the next order ID."""
        last_msg = self.session.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(desc(Message.step_order)).first()
        return (last_msg.step_order + 1) if last_msg else 1

    async def create_conversation(self, user_id: int, title: str | None = None) -> Conversation:
        """Create a new conversation for a user."""
        conv = Conversation(user_id=user_id, title=title)
        # Initialize default state
        conv.state = {"todos": [], "uploads": {}}
        
        self.session.add(conv)
        self.session.commit()
        self.session.refresh(conv)
        return conv

    async def get_conversation(self, conversation_id: int, user_id: int) -> Conversation | None:
        """Get a conversation by ID and user ID."""
        stmt = select(Conversation).where(
            Conversation.id == conversation_id, 
            Conversation.user_id == user_id,
            Conversation.is_archived == False
        )
        result = self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_history(self, conversation_id: int) -> list[ModelMessage]:
        """
        Reconstruct PydanticAI message history from database.
        
        This converts our DB `Message` rows back into `ModelRequest`/`ModelResponse` objects
        that PydanticAI can understand.
        """
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.step_order)
        
        db_messages = self.session.execute(stmt).scalars().all()
        
        history: list[ModelMessage] = []
        
        for db_msg in db_messages:
            if db_msg.role == 'user':
                history.append(ModelRequest(parts=[UserPromptPart(content=db_msg.content)]))
            
            elif db_msg.role == 'model':
                # Reconstruct ModelResponse
                parts = []
                if db_msg.content:
                    parts.append(TextPart(content=db_msg.content))
                
                if db_msg.tool_calls:
                    # Deserialize tool calls
                    tool_calls = json.loads(db_msg.tool_calls) if isinstance(db_msg.tool_calls, str) else db_msg.tool_calls
                    for tc in tool_calls:
                        parts.append(ToolCallPart(
                            tool_name=tc['name'],
                            args=tc['args'],
                            tool_call_id=tc.get('tool_call_id')
                        ))
                
                history.append(ModelResponse(parts=parts))
                
            elif db_msg.role == 'tool-return':
                # This is tricky: PydanticAI usually groups ToolReturns into a ModelRequest
                # We need to find the pending ModelRequest or create a new one
                # For simplicity in this v1, we assume creating a new ModelRequest
                # In robust impl, we might merge adjacent tool returns
                
                # Deserializing content can be complex (Json vs Text)
                # Here we treat as text for safety
                history.append(ModelRequest(parts=[ToolReturnPart(
                    tool_name=db_msg.tool_name,
                    content=db_msg.tool_return_content,
                    tool_call_id=db_msg.tool_call_id
                )]))
                
        return history

    async def persist_message(self, conversation_id: int, message: ModelMessage, step_order: int) -> None:
        """
        Persist a single PydanticAI message to the database.
        
        Handles decomposition of complex messages (Text + ToolCalls).
        """
        if isinstance(message, ModelRequest):
            # Could be UserPrompt or ToolReturn
            for part in message.parts:
                if isinstance(part, UserPromptPart):
                    msg = Message(
                        conversation_id=conversation_id,
                        step_order=step_order,
                        role='user',
                        content=part.content
                    )
                    self.session.add(msg)
                    
                elif isinstance(part, ToolReturnPart):
                    msg = Message(
                        conversation_id=conversation_id,
                        step_order=step_order,
                        role='tool-return',
                        tool_name=part.tool_name,
                        tool_call_id=part.tool_call_id,
                        tool_return_content=str(part.content) # Simple serialization
                    )
                    self.session.add(msg)
                    
        elif isinstance(message, ModelResponse):
            # Model response can have text AND tool calls
            text_content = ""
            tool_calls = []
            
            for part in message.parts:
                if isinstance(part, TextPart):
                    text_content += part.content
                elif isinstance(part, ToolCallPart):
                    tool_calls.append({
                        "name": part.tool_name,
                        "args": part.args,
                        "tool_call_id": part.tool_call_id
                    })
            
            msg = Message(
                conversation_id=conversation_id,
                step_order=step_order,
                role='model',
                content=text_content,
                tool_calls=tool_calls if tool_calls else None
            )
            self.session.add(msg)

        self.session.commit()

    async def update_state_from_result(self, conversation_id: int, tool_name: str, result: Any):
        """
        Update conversation state based on specific tool side-effects.
        This is the 'Side-Effect Handler' logic.
        """
        if tool_name == 'write_todos':
            # Result is usually a string message, but we need the actual data
            # In a perfect world, we'd parse the result or capture the input args
            # For this v1, checking if we can get the actual data source might be better
            # BUT: Since tool execution already updated `ctx.deps.todos`, 
            # we should persist `deps.todos` at the end of the turn, NOT relying on return string.
            pass

    async def save_deps_state(self, conversation_id: int, deps: DeepAgentDeps):
        """Save the full Deps state (todos, uploads) to conversation."""
        conv = self.session.get(Conversation, conversation_id)
        if conv:
            # Serialize todos
            todos_data = [
                {"content": t.content, "status": t.status, "active_form": t.active_form} 
                for t in deps.todos
            ]
            
            # Update state (merge or replace)
            new_state = conv.state.copy() if conv.state else {}
            new_state["todos"] = todos_data
            # new_state["uploads"] = deps.uploads # If serializable
            
            conv.state = new_state
            self.session.add(conv)
            self.session.commit()

    # ===== Todos Management =====
    
    async def get_todos(self, conversation_id: int, user_id: int) -> list[dict]:
        """Get current todos for a conversation."""
        conv = await self.get_conversation(conversation_id, user_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        if not conv.state or "todos" not in conv.state:
            return []
        
        return conv.state["todos"]
    
    async def update_todos(
        self, 
        conversation_id: int, 
        user_id: int,
        todos: list[dict]
    ) -> list[dict]:
        """
        Replace entire todos list for a conversation.
        
        IMPORTANT: Only call when agent is NOT running.
        """
        conv = await self.get_conversation(conversation_id, user_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Validate structure
        for todo in todos:
            if not all(k in todo for k in ["content", "status", "active_form"]):
                raise ValueError("Each todo must have: content, status, active_form")
            
            if todo["status"] not in ["pending", "in_progress", "completed"]:
                raise ValueError(f"Invalid status: {todo['status']}")
        
        # Replace entire list
        new_state = conv.state.copy() if conv.state else {}
        new_state["todos"] = todos
        
        conv.state = new_state
        self.session.add(conv)
        self.session.commit()
        
        return todos
