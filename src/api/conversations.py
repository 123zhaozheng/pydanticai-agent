"""API endpoints for Conversations management."""

import logfire

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Literal

from src.database import get_db
from src.auth import CurrentUser, get_current_user
from src.services.conversation_service import ConversationService
from pydantic_deep.backends.sandbox import DockerSandbox

logger = logfire

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
    current_user: CurrentUser = Depends(get_current_user),
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
        current_user.id, 
        include_archived=include_archived,
        limit=limit,
        offset=offset
    )
    return conversations


@router.post("", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation."""
    service = ConversationService(db)
    conversation = await service.create_conversation(current_user.id, body.title)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single conversation by ID."""
    service = ConversationService(db)
    conversation = await service.get_conversation(conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("/{conversation_id}/messages", response_model=list[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user),
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
            current_user.id,
            limit=limit,
            offset=offset
        )
        return messages
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Conversation Status Endpoints =====

@router.post("/{conversation_id}/archive", response_model=ConversationResponse)
async def archive_conversation(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Archive a conversation.
    
    Archived conversations are hidden from the default list but can still be accessed.
    """
    service = ConversationService(db)
    try:
        conversation = await service.archive_conversation(conversation_id, current_user.id)
        return conversation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{conversation_id}/unarchive", response_model=ConversationResponse)
async def unarchive_conversation(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Unarchive a conversation.
    
    Restores the conversation to the default list.
    """
    service = ConversationService(db)
    try:
        conversation = await service.unarchive_conversation(conversation_id, current_user.id)
        return conversation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{conversation_id}/star", response_model=ConversationResponse)
async def star_conversation(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Star/favorite a conversation.
    
    Starred conversations can be filtered or sorted to the top.
    """
    service = ConversationService(db)
    try:
        conversation = await service.star_conversation(conversation_id, current_user.id)
        return conversation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{conversation_id}/unstar", response_model=ConversationResponse)
async def unstar_conversation(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove star from a conversation.
    """
    service = ConversationService(db)
    try:
        conversation = await service.unstar_conversation(conversation_id, current_user.id)
        return conversation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently delete a conversation.
    
    **WARNING:** This action is irreversible. All messages will be deleted.
    Consider using archive instead.
    """
    service = ConversationService(db)
    try:
        await service.delete_conversation(conversation_id, current_user.id)
        return None
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
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stream chat with the agent.
    
    **Returns:** Server-Sent Events (SSE) stream of text chunks.
    """
    from fastapi.responses import StreamingResponse
    from pydantic_deep import create_deep_agent, discover_container_files, get_default_sandbox_config
    from pydantic_deep.deps import DeepAgentDeps
    from pydantic_deep.backends.sandbox import DockerSandbox
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
    # Get allowed skill names for permission filtering (needed for both new and reused sandbox)
    from src.services.skill_service import SkillService
    from src.config import settings
    from pydantic_deep.toolsets.skills import discover_skills_from_directory
    
    skill_service = SkillService(db)
    allowed_skill_names = skill_service.get_allowed_skill_names(current_user.id)
    logger.info("User skill access", user_id=current_user.id, skill_count=len(allowed_skill_names), skills=allowed_skill_names)
    
    # Calculate effective skills (intersection of frontend selection and user permissions)
    if body.skills == "auto":
        effective_skill_names = allowed_skill_names
    else:
        # Frontend selection must be a subset of user permissions
        effective_skill_names = [s for s in body.skills if s in allowed_skill_names]
    
    logger.info("Effective skills calculated",
        user_id=current_user.id,
        requested=body.skills,
        permitted=allowed_skill_names,
        effective=effective_skill_names
    )
    
    # Discover skill metadata from skills directory (for system prompt injection)
    loaded_skills = discover_skills_from_directory(
        skills_dir=settings.BASE_DIR / "skills",
        skill_names=effective_skill_names if effective_skill_names else None
    )
    logger.info("Loaded skills metadata", skill_count=len(loaded_skills), skills=[s["name"] for s in loaded_skills])
    
    if conversation_id in _sandbox_manager:
        sandbox = _sandbox_manager[conversation_id]
        logger.debug("Reusing sandbox", conversation_id=conversation_id)
    else:
        # Create sandbox with automatic volume mounting, image config, and skill filtering
        sandbox = DockerSandbox(
            user_id=current_user.id,
            conversation_id=conversation_id,
            upload_path=body.upload_path,  # Optional custom upload path
            session_id=f"{current_user.id}:{conversation_id}",  # Name container as user_id:conversation_id
            image_config=get_default_sandbox_config(),  # 注入环境能力描述到系统提示
            allowed_skill_names=effective_skill_names,  # 只挂载有效的技能目录（交集后）
        )
        _sandbox_manager[conversation_id] = sandbox
        logger.info("Created sandbox", conversation_id=conversation_id, session_id=f"{current_user.id}:{conversation_id}")

    # Discover files in container
    file_paths = discover_container_files(sandbox)
    logger.debug("Discovered container files", file_count=len(file_paths))

    # Create DeepAgentDeps with sandbox backend and file paths
    deps = DeepAgentDeps(
        backend=sandbox,
        user_id=current_user.id,
        conversation_id=conversation_id,
        file_paths=file_paths  # Inject container file paths
    )

    # Create Agent (history cleanup disabled to prevent infinite loops)
    mcp_tool_filter = None if body.mcp_tools == "auto" else body.mcp_tools
    
    agent = create_deep_agent(
        model=model,
        backend=sandbox,
        include_subagents=body.enable_subagents,  # Enable subagents based on request
        enable_permission_filtering=False,
        enable_mcp_tools=True,
        mcp_tool_names=mcp_tool_filter,  # Frontend-selected MCP tools
        skill_names=effective_skill_names if effective_skill_names else None,  # Effective skills (intersection)
        skills=loaded_skills,  # Pass skill metadata for system prompt injection
    )

    import json

    # --- Title Generation Setup ---
    # Retrieve conversation to check if title generation is needed
    # We check synchronously here because it's fast and determines if we need the overhead
    conv = await service.get_conversation(conversation_id, current_user.id)
    
    # Shared buffer to pass generated text to background task
    # Using a list as a mutable container
    shared_buffer = [] if (conv and service.should_generate_title(conv)) else None
    
    if shared_buffer is not None:
        # Add background task
        # IMPORTANT: We must NOT pass the 'db' session to background task as it will be closed
        background_tasks.add_task(
            background_generate_title,
            conversation_id=conversation_id,
            user_id=current_user.id,
            user_message=body.message,
            shared_buffer=shared_buffer
        )

    # Streaming generator
    async def event_generator():
        try:
            async for chunk in service.chat_stream(
                conversation_id=conversation_id,
                user_message=body.message,
                user_id=current_user.id,
                deps=deps,
                agent=agent
            ):
                # Collect text responses for title generation if enabled
                if shared_buffer is not None and chunk.get("type") == "text":
                    content = chunk.get("content", "")
                    if content:
                        shared_buffer.append(content)
                
                # SSE format: data: <json_content>\n\n
                yield f"data: {json.dumps(chunk, default=str)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        
        # NOTE: sandbox.stop() is handled by BackgroundTasks to avoid blocking the response completion

    # Add sandbox cleanup to background tasks
    # This ensures the container is stopped AFTER the response is fully sent to the client
    # resolving the "hanging connection" issue.
    background_tasks.add_task(
        background_stop_sandbox,
        sandbox=sandbox,
        conversation_id=conversation_id
    )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


async def background_generate_title(
    conversation_id: int, 
    user_id: int,
    user_message: str, 
    shared_buffer: list[str]
):
    """
    Background task to generate conversation title.
    
    It uses a shared buffer to get the full assistant response which was collected 
    during the streaming process.
    """
    if not shared_buffer:
        return

    assistant_response = "".join(shared_buffer)
    if not assistant_response.strip():
        return

    # Create a NEW database session for the background task
    # We cannot reuse the dependency session as it's scoped to the request
    from src.database import SessionLocal
    
    logger.info("Starting background title generation", conversation_id=conversation_id)
    
    with SessionLocal() as db:
        service = ConversationService(db)
        # Double check if title is still needed (race condition check)
        conv = await service.get_conversation(conversation_id, user_id)
        if conv and service.should_generate_title(conv):
            await service.generate_title_async(
                conversation_id=conversation_id,
                user_message=user_message,
                assistant_response=assistant_response
            )


def background_stop_sandbox(sandbox: "DockerSandbox", conversation_id: int):
    """
    Background task to stop the sandbox container.
    This runs after the response is sent, so strict termination speed is less critical,
    but we should still log it.
    """
    if sandbox._container is not None:
        logger.debug("Stopping container in background", conversation_id=conversation_id)
        sandbox.stop()
