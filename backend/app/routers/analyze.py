"""
Роутер за стартиране на анализ на видео.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
import json

from config import UPLOAD_DIR, OUTPUT_DIR

router = APIRouter()


@router.post("/{video_id}")
async def analyze_video(video_id: str, background_tasks: BackgroundTasks):
    video_path = None
    for ext in [".mp4", ".avi", ".mov", ".mkv", ".webm"]:
        candidate = UPLOAD_DIR / f"{video_id}{ext}"
        if candidate.exists():
            video_path = candidate
            break

    if not video_path:
        raise HTTPException(status_code=404, detail="Видео не е намерено")

    output_path = OUTPUT_DIR / f"{video_id}.json"
    background_tasks.add_task(run_analysis, str(video_path), str(output_path))

    return {
        "video_id": video_id,
        "status": "processing",
        "message": "Анализът е стартиран. Изчакайте няколко секунди и проверете резултатите."
    }


def run_analysis(video_path: str, output_path: str):
    try:
        from analysis.pose_extractor import PoseExtractor
        from analysis.biomechanics import BiomechanicsAnalyzer

        extractor = PoseExtractor()
        keypoints_data = extractor.process_video(video_path)

        analyzer = BiomechanicsAnalyzer()
        results = analyzer.analyze(keypoints_data)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    except Exception as e:
        error_result = {"error": str(e), "status": "failed"}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(error_result, f, ensure_ascii=False, indent=2)
