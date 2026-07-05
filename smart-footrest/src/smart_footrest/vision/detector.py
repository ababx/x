from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)

try:
    import mediapipe as mp
    _MP_AVAILABLE = True
except ImportError:
    _MP_AVAILABLE = False

from smart_footrest.config import DetectionConfig


@dataclass
class FootDetection:
    foot_present: bool
    foot_center_x: float  # normalized 0-1 in frame
    foot_center_y: float  # normalized 0-1 in frame
    person_seated: bool
    confidence: float
    left_ankle: tuple[float, float] | None = None
    right_ankle: tuple[float, float] | None = None


_NO_DETECTION = FootDetection(
    foot_present=False, foot_center_x=0.0, foot_center_y=0.0,
    person_seated=False, confidence=0.0,
)


def _angle_between(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    mag_ba = math.sqrt(ba[0] ** 2 + ba[1] ** 2)
    mag_bc = math.sqrt(bc[0] ** 2 + bc[1] ** 2)
    if mag_ba * mag_bc == 0:
        return 0.0
    cos_angle = max(-1.0, min(1.0, dot / (mag_ba * mag_bc)))
    return math.degrees(math.acos(cos_angle))


class FootDetector:
    # MediaPipe Pose landmark indices
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28
    LEFT_HEEL = 29
    RIGHT_HEEL = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX = 32

    def __init__(self, config: DetectionConfig):
        self._config = config
        self._pose = None
        if _MP_AVAILABLE:
            self._pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=1,
                min_detection_confidence=config.min_confidence,
                min_tracking_confidence=config.min_tracking_confidence,
            )

    def detect(self, frame: np.ndarray) -> FootDetection:
        if self._pose is None:
            return _NO_DETECTION

        rgb = frame
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            rgb = np.ascontiguousarray(frame[:, :, ::-1])  # BGR to RGB

        results = self._pose.process(rgb)
        if results.pose_landmarks is None:
            return _NO_DETECTION

        landmarks = results.pose_landmarks.landmark
        return self._extract_foot_data(landmarks)

    def _extract_foot_data(self, landmarks) -> FootDetection:
        def lm(idx):
            l = landmarks[idx]
            return (l.x, l.y, l.visibility)

        left_ankle = lm(self.LEFT_ANKLE)
        right_ankle = lm(self.RIGHT_ANKLE)
        left_heel = lm(self.LEFT_HEEL)
        right_heel = lm(self.RIGHT_HEEL)
        left_foot = lm(self.LEFT_FOOT_INDEX)
        right_foot = lm(self.RIGHT_FOOT_INDEX)

        foot_landmarks = [left_ankle, right_ankle, left_heel, right_heel, left_foot, right_foot]
        avg_visibility = sum(fl[2] for fl in foot_landmarks) / len(foot_landmarks)
        foot_present = avg_visibility >= self._config.foot_present_confidence

        foot_xs = [fl[0] for fl in foot_landmarks]
        foot_ys = [fl[1] for fl in foot_landmarks]
        center_x = sum(foot_xs) / len(foot_xs)
        center_y = sum(foot_ys) / len(foot_ys)

        left_hip = lm(self.LEFT_HIP)
        left_knee = lm(self.LEFT_KNEE)
        right_hip = lm(self.RIGHT_HIP)
        right_knee = lm(self.RIGHT_KNEE)

        left_angle = _angle_between(
            (left_hip[0], left_hip[1]),
            (left_knee[0], left_knee[1]),
            (left_ankle[0], left_ankle[1]),
        )
        right_angle = _angle_between(
            (right_hip[0], right_hip[1]),
            (right_knee[0], right_knee[1]),
            (right_ankle[0], right_ankle[1]),
        )
        avg_angle = (left_angle + right_angle) / 2.0
        person_seated = avg_angle < self._config.seated_angle_threshold

        return FootDetection(
            foot_present=foot_present,
            foot_center_x=center_x,
            foot_center_y=center_y,
            person_seated=person_seated,
            confidence=avg_visibility,
            left_ankle=(left_ankle[0], left_ankle[1]),
            right_ankle=(right_ankle[0], right_ankle[1]),
        )

    def close(self):
        if self._pose is not None:
            self._pose.close()
            self._pose = None


class MockDetector:
    """Returns pre-set detections for testing."""

    def __init__(self, detections: list[FootDetection] | None = None):
        self._detections = detections or []
        self._index = 0

    def detect(self, frame: np.ndarray) -> FootDetection:
        if self._index < len(self._detections):
            det = self._detections[self._index]
            self._index += 1
            return det
        return _NO_DETECTION

    def close(self):
        pass
