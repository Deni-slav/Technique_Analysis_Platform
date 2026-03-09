"""
Извличане на ключови точки от видео чрез MediaPipe Tasks Pose Landmarker.
"""
import cv2
import numpy as np
import mediapipe as mp
from pathlib import Path
from typing import Dict
import urllib.request

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"


def _get_model_path() -> str:
    """Сваля и връща пътя до модела при първо използване."""
    model_dir = Path(__file__).parent.parent / "models"
    model_dir.mkdir(exist_ok=True)
    model_path = model_dir / "pose_landmarker_lite.task"

    if not model_path.exists():
        urllib.request.urlretrieve(MODEL_URL, model_path)

    return str(model_path)


class PoseExtractor:
    """Извлича ключови точки от видео с гребане."""

    LANDMARKS = {
        "nose": 0,
        "left_shoulder": 11,
        "right_shoulder": 12,
        "left_elbow": 13,
        "right_elbow": 14,
        "left_wrist": 15,
        "right_wrist": 16,
        "left_hip": 23,
        "right_hip": 24,
        "left_knee": 25,
        "right_knee": 26,
    }

    def __init__(self, min_detection_confidence: float = 0.5):
        base_options = python.BaseOptions(model_asset_path=_get_model_path())
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            min_pose_detection_confidence=min_detection_confidence,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)

    def process_video(self, video_path: str) -> Dict:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        frames_data = []
        frame_idx = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_frame = np.ascontiguousarray(rgb_frame)

            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = self.detector.detect(mp_image)

            frame_data = {
                "frame": frame_idx,
                "timestamp": frame_idx / fps,
                "landmarks": {}
            }

            if detection_result.pose_landmarks:
                landmarks_list = detection_result.pose_landmarks[0]
                for name, idx in self.LANDMARKS.items():
                    if idx < len(landmarks_list):
                        lm = landmarks_list[idx]
                        frame_data["landmarks"][name] = {
                            "x": lm.x,
                            "y": lm.y,
                            "z": lm.z,
                            "visibility": getattr(lm, "visibility", 1.0)
                        }

            frames_data.append(frame_data)
            frame_idx += 1

        cap.release()

        return {
            "fps": fps,
            "total_frames": total_frames,
            "duration_sec": total_frames / fps,
            "frames": frames_data
        }
