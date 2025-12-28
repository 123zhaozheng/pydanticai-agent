"""API endpoints for file uploads."""

import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


# ===== Response Models =====


class UploadResponse(BaseModel):
    """Response model for file upload."""

    filename: str
    size: int
    path: str  # Host path
    container_path: str  # Path in Docker container


class FileListItem(BaseModel):
    """File information in list response."""

    filename: str
    size: int
    container_path: str
    created_at: datetime


# ===== Helper Functions =====


from src.config import settings

def get_upload_directory(user_id: int, conversation_id: int) -> Path:
    """Get upload directory path for a user's conversation.

    Args:
        user_id: User ID.
        conversation_id: Conversation ID.

    Returns:
        Path object for the upload directory.
    """
    upload_dir = settings.UPLOAD_DIR / str(user_id) / str(conversation_id)
    return upload_dir


# ===== Endpoints =====


@router.post("/{conversation_id}", response_model=UploadResponse)
async def upload_file(
    conversation_id: int,
    file: UploadFile = File(...),
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db),
):
    """
    Upload a file to the specified conversation.

    Files are saved to: `{base_dir}/uploads/{user_id}/{conversation_id}/{filename}`

    The file will be available in the Docker container at: `/workspace/uploads/{filename}`

    Args:
        conversation_id: Conversation ID to upload file to.
        file: File to upload.
        user_id: User ID (from auth token).
        db: Database session.

    Returns:
        Upload response with file details.

    Raises:
        HTTPException: If conversation not found or doesn't belong to user.
    """
    # Verify conversation exists and belongs to user
    service = ConversationService(db)
    conversation = await service.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(
            status_code=404, detail="Conversation not found or access denied"
        )

    # Get upload directory and create it if needed
    upload_dir = get_upload_directory(user_id, conversation_id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Build file path
    file_path = upload_dir / file.filename

    # Save file
    try:
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    return UploadResponse(
        filename=file.filename,
        size=len(content),
        path=str(file_path),
        container_path=f"/workspace/uploads/{file.filename}",
    )


@router.get("/{conversation_id}/files", response_model=list[FileListItem])
async def list_uploaded_files(
    conversation_id: int,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db),
):
    """
    List all uploaded files for a conversation.

    Args:
        conversation_id: Conversation ID.
        user_id: User ID (from auth token).
        db: Database session.

    Returns:
        List of uploaded files with metadata.

    Raises:
        HTTPException: If conversation not found or doesn't belong to user.
    """
    # Verify conversation exists and belongs to user
    service = ConversationService(db)
    conversation = await service.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(
            status_code=404, detail="Conversation not found or access denied"
        )

    # Get upload directory
    upload_dir = get_upload_directory(user_id, conversation_id)

    if not upload_dir.exists():
        return []

    # List files
    files = []
    for file_path in upload_dir.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append(
                FileListItem(
                    filename=file_path.name,
                    size=stat.st_size,
                    container_path=f"/workspace/uploads/{file_path.name}",
                    created_at=datetime.fromtimestamp(stat.st_ctime),
                )
            )

    # Sort by creation time (newest first)
    files.sort(key=lambda x: x.created_at, reverse=True)

    return files


@router.delete("/{conversation_id}/files/{filename}")
async def delete_uploaded_file(
    conversation_id: int,
    filename: str,
    user_id: int = 1,  # TODO: Get from JWT token
    db: Session = Depends(get_db),
):
    """
    Delete an uploaded file.

    Args:
        conversation_id: Conversation ID.
        filename: Name of file to delete.
        user_id: User ID (from auth token).
        db: Database session.

    Returns:
        Success message.

    Raises:
        HTTPException: If conversation or file not found.
    """
    # Verify conversation exists and belongs to user
    service = ConversationService(db)
    conversation = await service.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(
            status_code=404, detail="Conversation not found or access denied"
        )

    # Get file path
    upload_dir = get_upload_directory(user_id, conversation_id)
    file_path = upload_dir / filename

    # Security check: ensure file is within upload directory
    try:
        file_path.resolve().relative_to(upload_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Delete file
    try:
        file_path.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {e}")

    return {"message": f"File '{filename}' deleted successfully"}
