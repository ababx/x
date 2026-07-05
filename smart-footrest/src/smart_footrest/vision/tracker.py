from __future__ import annotations

import logging
from dataclasses import dataclass

from smart_footrest.config import TrackingConfig
from smart_footrest.vision.detector import FootDetection

logger = logging.getLogger(__name__)


@dataclass
class TrackedPosition:
    x: float  # meters, relative to camera/footrest origin
    y: float  # meters
    valid: bool  # whether we have a usable position
    person_seated: bool
    foot_present: bool
    confidence: float
    frames_since_detection: int


class PositionTracker:
    def __init__(self, config: TrackingConfig):
        self._config = config
        self._smooth_x: float | None = None
        self._smooth_y: float | None = None
        self._last_valid_x = 0.0
        self._last_valid_y = 0.0
        self._frames_without_detection = 0
        self._prev_x = 0.0
        self._prev_y = 0.0

    def update(self, detection: FootDetection) -> TrackedPosition:
        if detection.foot_present and detection.confidence > 0:
            raw_x = (detection.foot_center_x - 0.5) / self._config.pixels_per_meter * 1000.0
            raw_y = detection.foot_center_y / self._config.pixels_per_meter * 1000.0

            alpha = self._config.smoothing_alpha
            if self._smooth_x is None:
                self._smooth_x = raw_x
                self._smooth_y = raw_y
            else:
                self._smooth_x = alpha * raw_x + (1 - alpha) * self._smooth_x
                self._smooth_y = alpha * raw_y + (1 - alpha) * self._smooth_y

            self._last_valid_x = self._smooth_x
            self._last_valid_y = self._smooth_y
            self._frames_without_detection = 0

            return TrackedPosition(
                x=self._smooth_x,
                y=self._smooth_y,
                valid=True,
                person_seated=detection.person_seated,
                foot_present=True,
                confidence=detection.confidence,
                frames_since_detection=0,
            )

        self._frames_without_detection += 1

        if self._frames_without_detection <= self._config.dropout_hold_frames:
            return TrackedPosition(
                x=self._last_valid_x,
                y=self._last_valid_y,
                valid=True,
                person_seated=detection.person_seated,
                foot_present=False,
                confidence=0.0,
                frames_since_detection=self._frames_without_detection,
            )

        return TrackedPosition(
            x=0.0, y=0.0, valid=False,
            person_seated=False, foot_present=False,
            confidence=0.0,
            frames_since_detection=self._frames_without_detection,
        )

    def reset(self):
        self._smooth_x = None
        self._smooth_y = None
        self._last_valid_x = 0.0
        self._last_valid_y = 0.0
        self._frames_without_detection = self._config.dropout_hold_frames + 1
