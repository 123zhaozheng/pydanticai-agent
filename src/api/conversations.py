"""API endpoints for Conversations management."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

from src.database import get_db
from src.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


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
