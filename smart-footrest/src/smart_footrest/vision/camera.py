from __future__ import annotations

import logging
from typing import Protocol

import cv2
import numpy as np

from smart_footrest.config import CameraConfig

logger = logging.getLogger(__name__)


class Camera(Protocol):
    def read(self) -> tuple[bool, np.ndarray]: ...
    def release(self) -> None: ...
    @property
    def is_opened(self) -> bool: ...


class OpenCVCamera:
    def __init__(self, config: CameraConfig):
        self._config = config
        self._cap: cv2.VideoCapture | None = None

    def open(self) -> bool:
        self._cap = cv2.VideoCapture(self._config.device_index)
        if not self._cap.isOpened():
            logger.error("Failed to open camera at index %d", self._config.device_index)
            return False
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._config.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._config.height)
        self._cap.set(cv2.CAP_PROP_FPS, self._config.fps)
        logger.info(
            "Camera opened: %dx%d @ %d fps",
            self._config.width, self._config.height, self._config.fps,
        )
        return True

    def read(self) -> tuple[bool, np.ndarray]:
        if self._cap is None or not self._cap.isOpened():
            return False, np.empty(0)
        return self._cap.read()

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    @property
    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.release()


class MockCamera:
    """Generates synthetic frames for testing without a real camera."""

    def __init__(self, config: CameraConfig, frames: list[np.ndarray] | None = None):
        self._config = config
        self._frames = frames
        self._index = 0
        self._opened = True

    def read(self) -> tuple[bool, np.ndarray]:
        if not self._opened:
            return False, np.empty(0)

        if self._frames and self._index < len(self._frames):
            frame = self._frames[self._index]
            self._index += 1
            return True, frame

        frame = np.zeros(
            (self._config.height, self._config.width, 3), dtype=np.uint8
        )
        return True, frame

    def release(self) -> None:
        self._opened = False

    @property
    def is_opened(self) -> bool:
        return self._opened

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.release()


def create_camera(config: CameraConfig, mock: bool = False, mock_frames: list[np.ndarray] | None = None) -> OpenCVCamera | MockCamera:
    if mock:
        return MockCamera(config, frames=mock_frames)
    return OpenCVCamera(config)
