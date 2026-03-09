"""
Обучение на референтен модел от набор от видеа с правилна техника.
Моделът извлича статистики (средно, std) от референтните видеа
и се използва за сравнение при анализ на нови видеа.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from config import REFERENCE_VIDEOS_DIR, REFERENCE_MODEL_PATH


def get_reference_video_paths() -> List[Path]:
    """Връща списък с пътища към референтни видеа."""
    exts = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    paths = []
    for f in REFERENCE_VIDEOS_DIR.iterdir():
        if f.suffix.lower() in exts:
            paths.append(f)
    return paths


def train_model_from_videos() -> Dict:
    """
    Обработва всички референтни видеа, извлича метрики и изгражда
    статистически модел (средно, std, min, max) за всяка метрика.
    """
    from analysis.pose_extractor import PoseExtractor
    from analysis.biomechanics import BiomechanicsAnalyzer

    video_paths = get_reference_video_paths()
    if not video_paths:
        return {
            "status": "no_videos",
            "message": "Няма референтни видеа. Качете видеа с правилна техника.",
            "metrics": {}
        }

    extractor = PoseExtractor()
    analyzer = BiomechanicsAnalyzer()

    all_metrics = {
        "torso_rotation": [],
        "drive_recovery_ratio": [],
        "stroke_rate": [],
        "symmetry": []
    }

    for video_path in video_paths:
        try:
            keypoints_data = extractor.process_video(str(video_path))
            results = analyzer.analyze(keypoints_data)

            if results.get("status") != "success":
                continue

            m = results.get("metrics", {})
            all_metrics["torso_rotation"].append(m.get("torso_rotation", {}).get("range_deg", 0))
            all_metrics["drive_recovery_ratio"].append(m.get("drive_recovery_ratio", {}).get("ratio", 0.5))
            all_metrics["stroke_rate"].append(m.get("stroke_rate", {}).get("spm", 0))
            all_metrics["symmetry"].append(m.get("symmetry", {}).get("symmetry_score", 100))

        except Exception:
            continue

    # Изграждане на модела
    model = {
        "status": "trained",
        "n_videos": len(video_paths),
        "n_successful": sum(1 for v in all_metrics["torso_rotation"] if v is not None),
        "metrics": {}
    }

    for key, values in all_metrics.items():
        values = [v for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))]
        if values:
            arr = np.array(values)
            model["metrics"][key] = {
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr)) if len(arr) > 1 else 0.1,
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "n_samples": len(values)
            }
        else:
            defaults = {
                "torso_rotation": {"mean": 35, "std": 5, "min": 25, "max": 50, "n_samples": 0},
                "drive_recovery_ratio": {"mean": 0.4, "std": 0.05, "min": 0.33, "max": 0.5, "n_samples": 0},
                "stroke_rate": {"mean": 24, "std": 4, "min": 18, "max": 32, "n_samples": 0},
                "symmetry": {"mean": 95, "std": 5, "min": 80, "max": 100, "n_samples": 0}
            }
            model["metrics"][key] = defaults.get(key, {"mean": 0, "std": 1, "min": 0, "max": 100, "n_samples": 0})

    # Запис на модела
    with open(REFERENCE_MODEL_PATH, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=2)

    return model


def load_reference_model() -> Optional[Dict]:
    """Зарежда научения референтен модел."""
    if not REFERENCE_MODEL_PATH.exists():
        return None
    with open(REFERENCE_MODEL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def compare_with_learned_model(metrics: Dict) -> Dict:
    """
    Сравнява метриките с научения модел.
    Връща оценка 0-100 за всяка метрика спрямо mean ± std.
    """
    model = load_reference_model()
    if not model or model.get("status") != "trained" or not model.get("metrics"):
        return None  # Ще се използват фиксирани референти

    comparison = {}
    model_metrics = model["metrics"]

    mapping = {
        "torso_rotation": ("torso_rotation", "range_deg"),
        "drive_recovery_ratio": ("drive_recovery_ratio", "ratio"),
        "stroke_rate": ("stroke_rate", "spm"),
        "symmetry": ("symmetry", "symmetry_score")
    }

    for key, (metric_key, field) in mapping.items():
        if key not in model_metrics:
            continue

        ref = model_metrics[key]
        value = metrics.get(metric_key, {}).get(field, ref["mean"])

        # Оценка: колко стандартни отклонения е от средното
        std = max(ref["std"], 0.01)
        z_score = abs(value - ref["mean"]) / std
        # z=0 -> 100, z=2 -> ~40, z=3 -> ~10
        score = max(0, min(100, 100 - z_score * 30))

        comparison[key] = {
            "value": value,
            "optimal": ref["mean"],
            "learned_from": ref.get("n_samples", 0),
            "in_range": ref["min"] <= value <= ref["max"],
            "score": round(score, 1)
        }

    return comparison
