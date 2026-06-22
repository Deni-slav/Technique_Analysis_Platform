"""
Референтни стойности за правилна техника при кану-каяк.
"""
from typing import Dict


REFERENCE_VALUES = {
    "torso_rotation": {
        "range_deg": {"min": 30, "max": 65, "optimal": 45},
        "description": "Ротация на торса (градуси)"
    },
    "drive_recovery_ratio": {
        "ratio": {"min": 0.33, "max": 0.55, "optimal": 0.42},
        "description": "Съотношение drive:recovery"
    },
    "stroke_rate": {
        "spm": {"min": 55, "max": 95, "optimal": 70},
        "description": "Честота на загребвания (SPM)"
    },
    "symmetry": {
        "symmetry_score": {"min": 80, "max": 100, "optimal": 95},
        "description": "Симетрия (0-100)"
    }
}


def compare_with_reference(metrics: Dict) -> Dict:
    comparison = {}

    tr = metrics.get("torso_rotation", {})
    ref_tr = REFERENCE_VALUES["torso_rotation"]["range_deg"]
    comparison["torso_rotation"] = _score_in_range(
        tr.get("range_deg", 0), ref_tr["min"], ref_tr["max"], ref_tr["optimal"]
    )

    dr = metrics.get("drive_recovery_ratio", {})
    ref_dr = REFERENCE_VALUES["drive_recovery_ratio"]["ratio"]
    comparison["drive_recovery_ratio"] = _score_in_range(
        dr.get("ratio", 0.5), ref_dr["min"], ref_dr["max"], ref_dr["optimal"]
    )

    sr = metrics.get("stroke_rate", {})
    ref_sr = REFERENCE_VALUES["stroke_rate"]["spm"]
    comparison["stroke_rate"] = _score_in_range(
        sr.get("spm", 0), ref_sr["min"], ref_sr["max"], ref_sr["optimal"]
    )

    sym = metrics.get("symmetry", {})
    ref_sym = REFERENCE_VALUES["symmetry"]["symmetry_score"]
    comparison["symmetry"] = _score_in_range(
        sym.get("symmetry_score", 0), ref_sym["min"], ref_sym["max"], ref_sym["optimal"]
    )

    return comparison


def _score_in_range(value: float, vmin: float, vmax: float, optimal: float) -> Dict:
    if vmin <= value <= vmax:
        dist = abs(value - optimal)
        range_size = max(vmax - vmin, 0.001)
        score = max(0, 100 - (dist / range_size) * 30)
    else:
        if value < vmin:
            score = max(0, 50 - (vmin - value) * 2)
        else:
            score = max(0, 50 - (value - vmax) * 2)

    return {
        "value": value,
        "optimal": optimal,
        "in_range": vmin <= value <= vmax,
        "score": round(min(100, max(0, score)), 1)
    }
