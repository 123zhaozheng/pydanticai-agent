"""API endpoints for Todos management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.auth import CurrentUser, get_current_user
from src.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/conversations/{conversation_id}/todos", tags=["todos"])


class TodoUpdate(BaseModel):
    """Request model for updating todos (full replacement)."""
    todos: list[dict] = Field(..., description="Complete list of todos to replace existing ones")


@router.get("", response_model=list[dict])
async def get_todos(
    conversation_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all todos for a conversation.
    
    **Response:** List of todo objects with keys: content, status, active_form
    """
    service = ConversationService(db)
    try:
        todos = await service.get_todos(conversation_id, current_user.id)
        return todos
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("", response_model=list[dict])
async def update_todos(
    conversation_id: int,
    body: TodoUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Replace entire todos list for a conversation.
    
    **WARNING:** Only call when agent is NOT running.
    
    **Request Body:**
    ```json
    {
      "todos": [
        {
          "content": "任务内容",
          "status": "pending|in_progress|completed",
          "active_form": "正在执行的描述"
        }
      ]
    }
    ```
    """
    service = ConversationService(db)
    try:
        updated = await service.update_todos(conversation_id, current_user.id, body.todos)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
