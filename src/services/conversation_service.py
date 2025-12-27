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
    TextPartDelta,
    UserPromptPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai import (
    PartStartEvent,
    PartDeltaEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    AgentRunResultEvent,
    FinalResultEvent
)

from src.models.conversations import Conversation, Message
from src.models.tools_skills import McpServer
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
    ) -> AsyncGenerator[dict, None]:
        """
        Execute agent with streaming using run_stream_events for full control.
        
        Yields structured events:
        - {"type": "text", "content": "..."}
        - {"type": "tool_call", "tool_name": "...", "args": ...}
        - {"type": "tool_result", "tool_name": "...", "result": ...}
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
        
        # 3. Stream Events using PydanticAI's run_stream_events
        from pydantic_ai.messages import (
            ModelRequest, ModelResponse, UserPromptPart, TextPart, ToolCallPart, ToolReturnPart
        )
        from pydantic_ai import (
            AgentRunResultEvent, 
            PartStartEvent, 
            PartDeltaEvent, 
            FunctionToolCallEvent, 
            FunctionToolResultEvent
        )
        
        assistant_text_chunks = []
        current_tool_calls = []  # To batch tool calls for a single model message
        tool_names = {} # Map tool_call_id -> tool_name
        
        # FIX: run_stream_events returns an AsyncGenerator, not a context manager
        stream = agent.run_stream_events(
            user_message,
            deps=deps,
            message_history=history
        )
            
        async for event in stream:
            # Debug logging
            import datetime
            with open("debug_events.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now()} Event: {type(event)} {event}\n")
            
            # --- Text Generation ---
            if isinstance(event, PartStartEvent):
                if isinstance(event.part, TextPart):
                    chunk = event.part.content
                    if chunk:
                        assistant_text_chunks.append(chunk)
                        yield {
                            "type": "text",
                            "content": chunk
                        }
                        
            elif isinstance(event, PartDeltaEvent):
                if isinstance(event.delta, TextPartDelta):
                    chunk = event.delta.content_delta
                    if chunk:
                        assistant_text_chunks.append(chunk)
                        yield {
                            "type": "text",
                            "content": chunk
                        }
                        
            # --- Tool Call ---
            elif isinstance(event, FunctionToolCallEvent):
                tool_call = {
                    "name": event.part.tool_name,
                    "args": event.part.args,
                    "tool_call_id": event.part.tool_call_id
                }
                current_tool_calls.append(tool_call)
                tool_names[tool_call["tool_call_id"]] = tool_call["name"]
                
                yield {
                    "type": "tool_call",
                    "tool_name": tool_call["name"],
                    "args": tool_call["args"],
                    "tool_call_id": tool_call["tool_call_id"]
                }
            
            # --- Tool Result ---
            elif isinstance(event, FunctionToolResultEvent):
                # 1. Prepare structured result for JSON output
                # Try to extract 'content' from ToolReturnPart or similar objects
                raw_result = event.result
                
                # Check for 'content' attribute (like in ToolReturnPart examples from user)
                if hasattr(raw_result, "content"):
                    serialized_result = raw_result.content
                # If it's a dict with a 'content' key, also use that
                elif isinstance(raw_result, dict) and "content" in raw_result:
                    serialized_result = raw_result["content"]
                # Otherwise, fallback to model_dump/dict/as-is logic
                elif hasattr(raw_result, "model_dump"):
                    serialized_result = raw_result.model_dump()
                elif hasattr(raw_result, "dict"):
                    serialized_result = raw_result.dict()
                else:
                    serialized_result = raw_result

                # Get tool name from mapping
                tool_name = tool_names.get(event.tool_call_id, "unknown")
                
                # Yield result to stream as structured data
                yield {
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": serialized_result, 
                    "tool_call_id": event.tool_call_id
                }

                # 2. Before saving result, save the preceding Model Message with Tool Calls
                if current_tool_calls:
                    model_msg = Message(
                        conversation_id=conversation_id,
                        step_order=step_order,
                        role='model',
                        content="".join(assistant_text_chunks) if assistant_text_chunks else "",
                        tool_calls=current_tool_calls
                    )
                    self.session.add(model_msg)
                    self.session.commit()
                    step_order += 1
                    
                    # Reset accumulators
                    assistant_text_chunks = [] 
                    current_tool_calls = []

                # 3. Persist the Tool Return Message
                # For DB storage, we store the JSON string of the structured result
                import json
                try:
                    db_ret_content = json.dumps(serialized_result, ensure_ascii=False)
                except (TypeError, ValueError):
                    db_ret_content = str(raw_result)

                tool_msg = Message(
                    conversation_id=conversation_id,
                    step_order=step_order,
                    role='tool-return',
                    tool_name=tool_name,
                    tool_call_id=event.tool_call_id,
                    tool_return_content=db_ret_content
                )
                self.session.add(tool_msg)
                self.session.commit()
                step_order += 1

            # End of stream loop
        
        # 4. Save Final Assistant Message (if any text remains or was generated after tools)
        # Note: If the last act was a tool call, and then it finished, we might still have text.
        # But usually `AgentRunResultEvent` signifies end. 
        # We need to capture the final text response.
        
        if assistant_text_chunks:
            final_text = "".join(assistant_text_chunks)
            assistant_msg = Message(
                conversation_id=conversation_id,
                step_order=step_order,
                role='model',
                content=final_text,
                tool_calls=None
            )
            self.session.add(assistant_msg)
            self.session.commit()
        
        # 5. Save State (Todos etc)
        # Because we passed `deps` to the agent, it was mutated in place.
        state = {
            "todos": [t.model_dump() for t in deps.todos] if deps.todos else [],
            "uploads": conv.state.get("uploads", {}) if conv.state else {}
        }
        self.session.query(Conversation).filter(
            Conversation.id == conversation_id
        ).update({"state": state})
        self.session.commit()

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

    async def list_conversations(
        self, 
        user_id: int, 
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> list[Conversation]:
        """
        Get all conversations for a user.
        
        Args:
            user_id: User ID
            include_archived: Whether to include archived conversations
            limit: Max number of conversations to return
            offset: Pagination offset
        
        Returns:
            List of conversations ordered by updated_at desc
        """
        stmt = select(Conversation).where(Conversation.user_id == user_id)
        
        if not include_archived:
            stmt = stmt.where(Conversation.is_archived == False)
        
        stmt = stmt.order_by(desc(Conversation.updated_at)).limit(limit).offset(offset)
        
        result = self.session.execute(stmt)
        return result.scalars().all()

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

    async def get_messages(
        self,
        conversation_id: int,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> list[Message]:
        """
        Get raw messages for a conversation (for display in UI).
        
        Returns:
            List of Message objects ordered by step_order
        """
        # Verify ownership
        conv = await self.get_conversation(conversation_id, user_id)
        if not conv:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        stmt = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.step_order).limit(limit).offset(offset)
        
        result = self.session.execute(stmt)
        return result.scalars().all()

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

    async def generate_title_async(
        self,
        conversation_id: int,
        user_message: str,
        assistant_response: str,
        model: Any = None,  # PydanticAI model or None for default
    ) -> str | None:
        """
        异步生成会话标题。
        
        在第一轮对话完成后调用,用小模型生成简洁标题。
        
        Args:
            conversation_id: 会话 ID
            user_message: 用户的第一条消息
            assistant_response: 助手的第一条回复
            model: 用于生成标题的模型 (默认使用数据库默认模型)
            
        Returns:
            生成的标题,或 None 如果失败
        """
        import logfire
        
        try:
            # 截断长内容
            user_msg = user_message[:200] if len(user_message) > 200 else user_message
            assistant_msg = assistant_response[:300] if len(assistant_response) > 300 else assistant_response
            
            # 构建提示
            prompt = f"""请根据以下对话内容生成一个简洁的中文标题,要求:
- 不超过15个字
- 直接输出标题,不要任何解释
- 概括对话的主要目的

用户: {user_msg}
助手: {assistant_msg}

标题:"""
            
            # 获取模型: 传入的模型 > 数据库默认模型 > 硬编码后备
            if model is None:
                try:
                    from src.services.model_manager import model_manager
                    model = model_manager.get_default_model(self.session)
                    logfire.info("TitleGen using default model from database")
                except Exception as e:
                    logfire.warn("TitleGen failed to get default model, using fallback", error=str(e))
                    from pydantic_ai.models.openai import OpenAIModel
                    model = OpenAIModel("gpt-4o-mini")
            
            from pydantic_ai import Agent
            title_agent = Agent(
                model=model,
                system_prompt="你是一个标题生成助手,只输出简短的中文标题。"
            )
            result = await title_agent.run(prompt)
            title = result.output.strip()
            
            # 清理标题 (移除引号等)
            title = title.strip('"\'')
            if len(title) > 50:
                title = title[:47] + "..."
            
            # 更新数据库
            self.session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).update({"title": title})
            self.session.commit()
            
            logfire.info("TitleGen generated title", conversation_id=conversation_id, title=title)
            return title
            
        except Exception as e:
            logfire.warn("TitleGen failed", conversation_id=conversation_id, error=str(e))
            return None
    
    def should_generate_title(self, conversation: Conversation) -> bool:
        """检查是否需要生成标题"""
        if conversation.title is None:
            return True
        if conversation.title.strip() in ("", "新会话", "New Chat", "Untitled"):
            return True
        return False
