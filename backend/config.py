"""Конфигурация на пътищата за проекта."""
from pathlib import Path

# Корен на проекта (RowingAnalysis/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = PROJECT_ROOT / "uploads"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
REFERENCE_VIDEOS_DIR = PROJECT_ROOT / "reference_videos"
REFERENCE_MODEL_PATH = PROJECT_ROOT / "reference_model.json"

# Създаване на директориите при стартиране
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
REFERENCE_VIDEOS_DIR.mkdir(exist_ok=True)
