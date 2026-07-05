import pytest
import numpy as np

from smart_footrest.config import (
    AppConfig, CameraConfig, DetectionConfig, TrackingConfig,
    MotionConfig, SafetyConfig, ControlConfig,
)
from smart_footrest.vision.detector import FootDetection


@pytest.fixture
def default_config():
    return AppConfig()


@pytest.fixture
def camera_config():
    return CameraConfig(width=640, height=480, fps=30)


@pytest.fixture
def detection_config():
    return DetectionConfig()


@pytest.fixture
def tracking_config():
    return TrackingConfig()


@pytest.fixture
def motion_config():
    return MotionConfig()


@pytest.fixture
def safety_config():
    return SafetyConfig()


@pytest.fixture
def control_config():
    return ControlConfig()


@pytest.fixture
def blank_frame():
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def seated_detection():
    return FootDetection(
        foot_present=True,
        foot_center_x=0.5,
        foot_center_y=0.8,
        person_seated=True,
        confidence=0.9,
        left_ankle=(0.45, 0.75),
        right_ankle=(0.55, 0.75),
    )


@pytest.fixture
def no_detection():
    return FootDetection(
        foot_present=False,
        foot_center_x=0.0,
        foot_center_y=0.0,
        person_seated=False,
        confidence=0.0,
    )
