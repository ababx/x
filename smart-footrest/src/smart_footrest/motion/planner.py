from __future__ import annotations

import math
from dataclasses import dataclass

from smart_footrest.config import MotionConfig
from smart_footrest.motion.controller import Position


@dataclass
class MotionCommand:
    left_velocity: float  # m/s
    right_velocity: float  # m/s
    at_target: bool


class MotionPlanner:
    WHEEL_BASE = 0.2  # meters

    def __init__(self, config: MotionConfig):
        self._config = config
        self._prev_error_dist = 0.0
        self._prev_error_angle = 0.0
        self._prev_left = 0.0
        self._prev_right = 0.0

    def compute(self, current: Position, target_x: float, target_y: float, dt: float) -> MotionCommand:
        dx = target_x - current.x
        dy = target_y - current.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < self._config.position_tolerance:
            self._prev_error_dist = 0.0
            self._prev_error_angle = 0.0
            return MotionCommand(left_velocity=0.0, right_velocity=0.0, at_target=True)

        target_angle = math.atan2(dy, dx)
        angle_error = target_angle - current.heading
        angle_error = math.atan2(math.sin(angle_error), math.cos(angle_error))

        if dt > 0:
            d_dist = (distance - self._prev_error_dist) / dt
            d_angle = (angle_error - self._prev_error_angle) / dt
        else:
            d_dist = 0.0
            d_angle = 0.0

        linear_vel = self._config.kp * distance + self._config.kd * d_dist
        angular_vel = self._config.kp * angle_error + self._config.kd * d_angle

        linear_vel = max(-self._config.max_speed, min(self._config.max_speed, linear_vel))

        left = linear_vel - angular_vel * self.WHEEL_BASE / 2.0
        right = linear_vel + angular_vel * self.WHEEL_BASE / 2.0

        left = self._apply_limits(left, self._prev_left, dt)
        right = self._apply_limits(right, self._prev_right, dt)

        self._prev_error_dist = distance
        self._prev_error_angle = angle_error
        self._prev_left = left
        self._prev_right = right

        return MotionCommand(left_velocity=left, right_velocity=right, at_target=False)

    def _apply_limits(self, vel: float, prev_vel: float, dt: float) -> float:
        if dt > 0:
            max_change = self._config.acceleration_limit * dt
            vel = max(prev_vel - max_change, min(prev_vel + max_change, vel))

        vel = max(-self._config.max_speed, min(self._config.max_speed, vel))

        if abs(vel) < self._config.min_speed:
            vel = 0.0

        return vel

    def reset(self):
        self._prev_error_dist = 0.0
        self._prev_error_angle = 0.0
        self._prev_left = 0.0
        self._prev_right = 0.0
