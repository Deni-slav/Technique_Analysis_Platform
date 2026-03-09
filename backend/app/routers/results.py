"""
Роутер за получаване на резултати от анализа.
"""
from fastapi import APIRouter, HTTPException
import json

from config import OUTPUT_DIR

router = APIRouter()


@router.get("/{video_id}")
async def get_results(video_id: str):
    output_path = OUTPUT_DIR / f"{video_id}.json"

    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Резултатите все още не са готови или анализът не е стартиран."
        )

    with open(output_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    return results
