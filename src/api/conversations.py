"""API endpoints for Conversations management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Literal

from src.database import get_db
from src.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

# ===== Global Sandbox Manager =====
# Reuse sandboxes by conversation_id to avoid creating new containers on every request
_sandbox_manager: dict[int, "DockerSandbox"] = {}


# ===== Response Models =====

class ConversationResponse(BaseModel):
    """Response model for a conversation."""
    id: int
    user_id: int
    title: str | None
    created_at: datetime
    updated_at: datetime
    is_archived: bool
    is_starred: bool
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response model for a message."""
    id: int
    conversation_id: int
    step_order: int
    role: str
    content: str | None
    tool_calls: list[dict] | None
    tool_return_content: str | None
    tool_name: str | None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    """Request model for creating a conversation."""
    title: str | None = None


# ===== Endpoints =====

@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    user_id: int = 1,  # TODO: Get from JWT token
    include_archived: bool = Query(False, description="Include archived conversations"),
    limit: int = Query(50, ge=1, le=100, description="Max conversations to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    Get all conversations for the current user.
    
    **Returns:** List of conversations ordered by most recently updated.
    """
    service = ConversationService(db)
    conversations = await service.list_conversations(
        user_id, 
        include_archived=include_archived,
        limit=limit,
        offset=offset
    )
    return conversations


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """Create a new conversation."""
    service = ConversationService(db)
    conversation = await service.create_conversation(user_id, body.title)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """Get a single conversation by ID."""
    service = ConversationService(db)
    conversation = await service.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    user_id: int = 1,  # TODO: Get from JWT token
    limit: int = Query(100, ge=1, le=500, description="Max messages to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    Get chat history messages for a conversation.
    
    **Returns:** List of messages ordered by step_order (chronological).
    """
    service = ConversationService(db)
    try:
        messages = await service.get_messages(
            conversation_id, 
            user_id,
            limit=limit,
            offset=offset
        )
        return messages
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Chat Endpoint =====

class ChatRequest(BaseModel):
    """Request model for chat."""
    message: str = Field(..., min_length=1, description="User message")
    model_name: str | None = Field(None, description="Model config name (uses default if not specified)")
    upload_path: str | None = Field(None, description="Custom upload directory path on host (optional)")
    enable_subagents: bool = Field(False, description="Enable subagent delegation for complex tasks")
    
    # Tool and skill selection (frontend control with permission intersection)
    # - "auto": Automatically inject all tools/skills user has permission for (default)
    # - list[str]: Specific tool/skill names to use (will be intersected with user permissions)
    mcp_tools: Literal["auto"] | list[str] = Field(
        "auto", 
        description="MCP tools to use: 'auto' for all permitted, or list of specific tool names"
    )
    skills: Literal["auto"] | list[str] = Field(
        "auto",
        description="Skills to use: 'auto' for all permitted, or list of specific skill names"
    )


@router.post("/{conversation_id}/chat")
async def chat_stream(
    conversation_id: int,
    body: ChatRequest,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db)
):
    """
    Stream chat with the agent.
    
    **Returns:** Server-Sent Events (SSE) stream of text chunks.
    
    **Usage:**
    ```javascript
    const eventSource = new EventSource('/api/conversations/1/chat');
    eventSource.onmessage = (event) => {
        console.log(event.data);  // Text chunk
    };
    ```
    """
    from fastapi.responses import StreamingResponse
    from pydantic_deep import create_deep_agent, discover_container_files
    from pydantic_deep.deps import DeepAgentDeps
    from pydantic_deep.backends.sandbox import DockerSandbox
    # from pydantic_deep.processors.cleanup import deduplicate_stateful_tools_processor
    from src.services.model_manager import model_manager

    service = ConversationService(db)

    # Get model instance
    try:
        if body.model_name:
            model = model_manager.get_model(body.model_name, db)
        else:
            model = model_manager.get_default_model(db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Reuse or create sandbox for this conversation
    if conversation_id in _sandbox_manager:
        sandbox = _sandbox_manager[conversation_id]
        print(f"♻️  Reusing sandbox for conversation {conversation_id}")
    else:
        # Create sandbox with automatic volume mounting
        sandbox = DockerSandbox(
            user_id=user_id,
            conversation_id=conversation_id,
            upload_path=body.upload_path,  # Optional custom upload path
            session_id=f"{user_id}:{conversation_id}"  # Name container as user_id:conversation_id
        )
        _sandbox_manager[conversation_id] = sandbox
        print(f"🆕 Created new sandbox for conversation {conversation_id} (session_id: {user_id}:{conversation_id})")

    # Discover files in container
    file_paths = discover_container_files(sandbox)
    print(f"📂 Discovered {len(file_paths)} files in container")

    # Create DeepAgentDeps with sandbox backend and file paths
    deps = DeepAgentDeps(
        backend=sandbox,
        user_id=user_id,
        conversation_id=conversation_id,
        file_paths=file_paths  # Inject container file paths
    )

    # Create Agent (history cleanup disabled to prevent infinite loops)
    # Determine MCP tools and skills selection:
    # - "auto" -> None (include all permitted)
    # - list[str] -> pass the list for filtering (will be intersected with permissions)
    mcp_tool_filter = None if body.mcp_tools == "auto" else body.mcp_tools
    skill_filter = None if body.skills == "auto" else body.skills
    
    agent = create_deep_agent(
        model=model,
        backend=sandbox,
        include_subagents=body.enable_subagents,  # Enable subagents based on request
        enable_permission_filtering=False,
        enable_mcp_tools=True,
        mcp_tool_names=mcp_tool_filter,  # Frontend-selected MCP tools
        skill_names=skill_filter,  # Frontend-selected skills
        # history_processors=[deduplicate_stateful_tools_processor]  # Disabled: causes infinite tool call loops
    )

    import json

    # Streaming generator
    async def event_generator():
        try:
            async for chunk in service.chat_stream(
                conversation_id=conversation_id,
                user_message=body.message,
                user_id=user_id,
                deps=deps,
                agent=agent
            ):
                # SSE format: data: <json_content>\n\n
                # Chunk is now a dict (text, tool_call, tool_result)
                yield f"data: {json.dumps(chunk, default=str)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        finally:
            # Stop container after response completes to avoid resource waste
            if sandbox._container is not None:
                print(f"🛑 Stopping container for conversation {conversation_id}")
                sandbox.stop()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
