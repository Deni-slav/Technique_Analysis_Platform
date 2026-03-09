"""
Роутер за качване на видео файлове.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import uuid
import shutil

from config import UPLOAD_DIR

router = APIRouter()
ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


@router.post("/")
async def upload_video(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдържан формат. Разрешени: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    video_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{video_id}{suffix}"

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Грешка при запис: {str(e)}")

    return {
        "video_id": video_id,
        "filename": file.filename,
        "path": str(file_path)
    }
