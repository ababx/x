from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class CameraConfig:
    device_index: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    use_picamera: bool = False


@dataclass
class DetectionConfig:
    min_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    seated_angle_threshold: float = 120.0
    foot_present_confidence: float = 0.4


@dataclass
class TrackingConfig:
    smoothing_alpha: float = 0.3
    dropout_hold_frames: int = 15
    pixels_per_meter: float = 500.0


@dataclass
class MotionConfig:
    kp: float = 1.2
    kd: float = 0.3
    max_speed: float = 0.1
    min_speed: float = 0.01
    acceleration_limit: float = 0.2
    position_tolerance: float = 0.03
    adjustment_threshold: float = 0.08


@dataclass
class SafetyConfig:
    geofence_x: float = 1.0
    geofence_y: float = 1.0
    watchdog_timeout: float = 0.5
    motor_command_timeout: float = 2.0
    max_speed_hard_limit: float = 0.15


@dataclass
class ControlConfig:
    loop_rate_hz: int = 20
    stable_detection_frames: int = 10
    person_lost_frames: int = 30


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str | None = None


@dataclass
class AppConfig:
    camera: CameraConfig = field(default_factory=CameraConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    motion: MotionConfig = field(default_factory=MotionConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    control: ControlConfig = field(default_factory=ControlConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


_SECTION_MAP = {
    "camera": CameraConfig,
    "detection": DetectionConfig,
    "tracking": TrackingConfig,
    "motion": MotionConfig,
    "safety": SafetyConfig,
    "control": ControlConfig,
    "logging": LoggingConfig,
}


def load_config(path: str | Path | None = None) -> AppConfig:
    if path is None:
        path = Path(__file__).resolve().parent.parent.parent / "config" / "default.yaml"
    else:
        path = Path(path)

    if not path.exists():
        return AppConfig()

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    sections = {}
    for key, cls in _SECTION_MAP.items():
        section_data = raw.get(key, {})
        if isinstance(section_data, dict):
            sections[key] = cls(**section_data)
        else:
            sections[key] = cls()

    return AppConfig(**sections)
