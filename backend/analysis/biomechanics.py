"""
Анализ на биомеханични параметри при кану-каяк.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.signal import find_peaks
from .reference import compare_with_reference
from .reference_model import compare_with_learned_model


class BiomechanicsAnalyzer:
    def analyze(self, keypoints_data: Dict) -> Dict:
        frames = keypoints_data.get("frames", [])
        fps = keypoints_data.get("fps", 30)
        if not frames:
            return {"error": "Няма данни за анализ", "status": "failed"}

        results = {
            "status": "success",
            "fps": fps,
            "duration_sec": keypoints_data.get("duration_sec", 0),
            "metrics": {
                "torso_rotation": self._compute_torso_rotation(frames),
                "drive_recovery_ratio": self._compute_drive_recovery_ratio(frames, fps),
                "stroke_rate": self._compute_stroke_rate(frames, fps),
                "symmetry": self._compute_symmetry(frames)
            },
            "recommendations": []
        }
        # Първо опит с научения модел, иначе фиксирани референти
        comparison = compare_with_learned_model(results["metrics"])
        if comparison:
            results["comparison"] = comparison
            results["comparison_source"] = "learned"
        else:
            results["comparison"] = compare_with_reference(results["metrics"])
            results["comparison_source"] = "default"
        results["recommendations"] = self._generate_recommendations(results["metrics"])
        return results

    def _get_landmark(self, frame: Dict, name: str) -> Optional[Tuple[float, float]]:
        lm = frame.get("landmarks", {}).get(name)
        if lm and lm.get("visibility", 0) > 0.5:
            return (lm["x"], lm["y"])
        return None

    def _compute_torso_rotation(self, frames: List[Dict]) -> Dict:
        angles = []
        for frame in frames:
            ls = self._get_landmark(frame, "left_shoulder")
            rs = self._get_landmark(frame, "right_shoulder")
            lh = self._get_landmark(frame, "left_hip")
            rh = self._get_landmark(frame, "right_hip")
            if all([ls, rs, lh, rh]):
                sm = ((ls[0]+rs[0])/2, (ls[1]+rs[1])/2)
                hm = ((lh[0]+rh[0])/2, (lh[1]+rh[1])/2)
                angles.append(np.degrees(np.arctan2(sm[0]-hm[0], sm[1]-hm[1])))
        if not angles:
            return {"mean_deg": 0, "range_deg": 0, "valid_frames": 0}
        angles_arr = np.array(angles)
        ptp = np.ptp(angles_arr)
        # unwrap за правилна амплитуда при wrap-around (-180/180)
        unwrapped = np.degrees(np.unwrap(np.radians(angles_arr)))
        ptp_unwrapped = np.ptp(unwrapped)
        # Амплитуда на stroke: unwrapped range, ограничена до 90°
        range_deg = min(ptp_unwrapped, 90) if ptp_unwrapped < 180 else min(360 - ptp_unwrapped, 90)
        range_deg = min(range_deg, 90)
        return {"mean_deg": float(np.mean(angles)), "range_deg": float(round(range_deg, 1)), "min_deg": float(np.min(angles)), "max_deg": float(np.max(angles)), "valid_frames": len(angles)}

    def _compute_drive_recovery_ratio(self, frames: List[Dict], fps: float) -> Dict:
        wrist_y = []
        for frame in frames:
            lw = self._get_landmark(frame, "left_wrist")
            rw = self._get_landmark(frame, "right_wrist")
            wrist_y.append((lw[1]+rw[1])/2 if lw and rw else np.nan)
        wrist_y = np.array(wrist_y)
        valid = ~np.isnan(wrist_y)
        if np.sum(valid) < 10:
            return {"ratio": 0.5, "drive_sec": 0, "recovery_sec": 0, "strokes": 0}
        # Минимум 0.4 сек между пикове (макс ~150 SPM за каяк)
        peaks, _ = find_peaks(-wrist_y[valid], distance=int(fps*0.4), prominence=0.02)
        if len(peaks) < 2:
            return {"ratio": 0.5, "drive_sec": 0, "recovery_sec": 0, "strokes": 0}
        ct = np.diff(np.where(valid)[0][peaks]) / fps
        ac = np.mean(ct) if len(ct) > 0 else 1.0
        drive_sec = ac / 3
        recovery_sec = ac * 2 / 3
        ratio = drive_sec / recovery_sec if recovery_sec > 0 else 0.5
        return {"ratio": float(ratio), "drive_sec": float(drive_sec), "recovery_sec": float(recovery_sec), "strokes": len(peaks)}

    def _compute_stroke_rate(self, frames: List[Dict], fps: float) -> Dict:
        wrist_y = []
        for frame in frames:
            lw = self._get_landmark(frame, "left_wrist")
            rw = self._get_landmark(frame, "right_wrist")
            wrist_y.append((lw[1]+rw[1])/2 if lw and rw else np.nan)
        wrist_y = np.array(wrist_y)
        valid = ~np.isnan(wrist_y)
        if np.sum(valid) < 10:
            return {"spm": 0, "stroke_interval_sec": 0, "total_strokes": 0}
        # Минимум 0.4 сек между strokes (реалистичен SPM за каяк/кану)
        peaks, _ = find_peaks(-wrist_y[valid], distance=int(fps*0.4), prominence=0.02)
        ds = len(frames) / fps
        spm = (len(peaks)/ds)*60 if ds > 0 else 0
        return {"spm": float(round(spm, 1)), "stroke_interval_sec": float(round(60/spm, 2)) if spm > 0 else 0, "total_strokes": len(peaks)}

    def _compute_symmetry(self, frames: List[Dict]) -> Dict:
        diffs = []
        for frame in frames:
            le, re = self._get_landmark(frame, "left_elbow"), self._get_landmark(frame, "right_elbow")
            ls, rs = self._get_landmark(frame, "left_shoulder"), self._get_landmark(frame, "right_shoulder")
            if all([le, re, ls, rs]):
                ld = np.hypot(le[0]-ls[0], le[1]-ls[1])
                rd = np.hypot(re[0]-rs[0], re[1]-rs[1])
                diffs.append(abs(ld-rd))
        if not diffs:
            return {"symmetry_score": 100, "mean_diff": 0}
        md = np.mean(diffs)
        return {"symmetry_score": float(round(max(0, 100-md*500), 1)), "mean_diff": float(round(md, 4))}

    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        recs = []
        tr = metrics.get("torso_rotation", {})
        if tr.get("range_deg", 0) < 15:
            recs.append("Увеличете ротацията на торса — в кану-каяк тя е основен двигател на удара.")
        if tr.get("range_deg", 100) > 65:
            recs.append("Внимание: прекалена ротация може да причини травми на гръбнака.")
        dr = metrics.get("drive_recovery_ratio", {})
        if dr.get("ratio", 0.5) > 0.65:
            recs.append("Recovery фазата трябва да е по-дълга от drive — позволява активен вход на перката.")
        if dr.get("ratio", 0.5) < 0.3:
            recs.append("Drive фазата изглежда твърде кратка — работете върху завършен натиск.")
        sr = metrics.get("stroke_rate", {})
        spm = sr.get("spm", 0)
        if 0 < spm < 50:
            recs.append("Честотата е ниска за кану-каяк. Типичното тренировъчно темпо е 60–90 SPM.")
        if spm > 150:
            recs.append("Внимание: много висока честота може да влоши техниката и ефективността на удара.")
        if metrics.get("symmetry", {}).get("symmetry_score", 100) < 80:
            recs.append("Наблюдава се асиметрия между левия и десния удар — работете върху балансирано гребане.")
        if not recs:
            recs.append("Техниката изглежда добра!")
        return recs
