"""
Роутер за референтни видеа и обучение на модел.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pathlib import Path
import uuid
import shutil

from config import REFERENCE_VIDEOS_DIR

router = APIRouter()
ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


@router.get("/videos")
async def list_reference_videos():
    """Списък с качени референтни видеа."""
    videos = []
    for f in REFERENCE_VIDEOS_DIR.iterdir():
        if f.suffix.lower() in ALLOWED_EXTENSIONS:
            videos.append({"filename": f.name, "path": str(f)})
    return {"videos": videos, "count": len(videos)}


@router.post("/videos")
async def upload_reference_video(file: UploadFile = File(...)):
    """Качва референтно видео (с правилна техника)."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Неподдържан формат. Разрешени: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    video_id = str(uuid.uuid4())
    file_path = REFERENCE_VIDEOS_DIR / f"{video_id}{suffix}"

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Грешка при запис: {str(e)}")

    return {
        "id": video_id,
        "filename": file.filename,
        "message": "Референтното видео е качено. Натиснете 'Обучи модел' за да го включите."
    }


@router.delete("/videos/{filename}")
async def delete_reference_video(filename: str):
    """Изтрива референтно видео."""
    file_path = REFERENCE_VIDEOS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Видео не е намерено")
    file_path.unlink()
    return {"message": "Видео изтрито"}


@router.post("/train")
async def train_model(background_tasks: BackgroundTasks):
    """
    Стартира обучение на модела от всички референтни видеа.
    Може да отнеме минути при много видеа.
    """
    from analysis.reference_model import get_reference_video_paths

    paths = get_reference_video_paths()
    if not paths:
        raise HTTPException(
            status_code=400,
            detail="Няма референтни видеа. Качете поне едно видео с правилна техника."
        )

    background_tasks.add_task(_run_training)
    return {
        "status": "training",
        "message": f"Обучението е стартирано от {len(paths)} видео. Изчакайте 1-5 минути.",
        "n_videos": len(paths)
    }


def _run_training():
    from analysis.reference_model import train_model_from_videos
    train_model_from_videos()


@router.get("/model")
async def get_model_status():
    """Връща статуса на научения модел."""
    from analysis.reference_model import load_reference_model

    model = load_reference_model()
    if not model:
        return {
            "trained": False,
            "message": "Моделът не е обучен. Качете референтни видеа и натиснете 'Обучи модел'."
        }

    return {
        "trained": True,
        "n_videos": model.get("n_videos", 0),
        "n_successful": model.get("n_successful", 0),
        "metrics": model.get("metrics", {}),
        "message": f"Моделът е обучен от {model.get('n_successful', 0)} видео."
    }
