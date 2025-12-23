import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.config import UPLOAD_DIR
from src.database import UploadedFileModel, get_db

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a file to the server and record it in the database.
    """
    try:
        # Generate a unique filename to prevent collisions
        file_ext = Path(file.filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        # Save the file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Record in database
        db_file = UploadedFileModel(
            filename=file.filename,
            file_path=str(file_path),
            content_type=file.content_type,
            size=file_path.stat().st_size
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)

        return {
            "id": db_file.id,
            "filename": db_file.filename,
            "stored_path": db_file.file_path,
            "message": "File uploaded successfully"
        }

    except Exception as e:
        # Cleanup if needed (omitted for brevity)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
