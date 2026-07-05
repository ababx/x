from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from smart_footrest.config import SafetyConfig
from smart_footrest.motion.controller import Position
from smart_footrest.motion.planner import MotionCommand

logger = logging.getLogger(__name__)


@dataclass
class SafetyStatus:
    safe: bool
    violation: str | None = None


class SafetyMonitor:
    def __init__(self, config: SafetyConfig):
        self._config = config
        self._last_loop_time = time.monotonic()
        self._motor_command_start: float | None = None
        self._motors_active = False

    def check(self, position: Position, command: MotionCommand) -> SafetyStatus:
        now = time.monotonic()

        # Watchdog: detect stalled control loop
        loop_dt = now - self._last_loop_time
        self._last_loop_time = now
        if loop_dt > self._config.watchdog_timeout:
            return SafetyStatus(safe=False, violation=f"Watchdog: loop stalled for {loop_dt:.2f}s")

        # Geofence
        if abs(position.x) > self._config.geofence_x:
            return SafetyStatus(safe=False, violation=f"Geofence X: {position.x:.2f}m exceeds {self._config.geofence_x}m")
        if abs(position.y) > self._config.geofence_y:
            return SafetyStatus(safe=False, violation=f"Geofence Y: {position.y:.2f}m exceeds {self._config.geofence_y}m")

        # Speed limit
        speed = max(abs(command.left_velocity), abs(command.right_velocity))
        if speed > self._config.max_speed_hard_limit:
            return SafetyStatus(safe=False, violation=f"Speed: {speed:.3f} m/s exceeds hard limit {self._config.max_speed_hard_limit}")

        # Motor command timeout
        is_commanding = not command.at_target and speed > 0
        if is_commanding:
            if not self._motors_active:
                self._motor_command_start = now
                self._motors_active = True
            elif self._motor_command_start is not None:
                duration = now - self._motor_command_start
                if duration > self._config.motor_command_timeout:
                    return SafetyStatus(safe=False, violation=f"Motor timeout: continuous command for {duration:.1f}s")
        else:
            self._motors_active = False
            self._motor_command_start = None

        return SafetyStatus(safe=True)

    def clamp_command(self, command: MotionCommand) -> MotionCommand:
        limit = self._config.max_speed_hard_limit
        left = max(-limit, min(limit, command.left_velocity))
        right = max(-limit, min(limit, command.right_velocity))
        return MotionCommand(left_velocity=left, right_velocity=right, at_target=command.at_target)

    def reset(self):
        self._last_loop_time = time.monotonic()
        self._motor_command_start = None
        self._motors_active = False
