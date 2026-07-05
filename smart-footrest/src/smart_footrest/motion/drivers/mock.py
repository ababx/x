from __future__ import annotations

import logging
import math
import time

from smart_footrest.motion.controller import MotorController, Position

logger = logging.getLogger(__name__)

WHEEL_BASE = 0.2  # meters between wheels


class MockController(MotorController):
    """Simulates differential drive with simple physics integration."""

    def __init__(self, wheel_base: float = WHEEL_BASE):
        self._wheel_base = wheel_base
        self._left_vel = 0.0
        self._right_vel = 0.0
        self._x = 0.0
        self._y = 0.0
        self._heading = 0.0
        self._last_update = time.monotonic()
        self._command_log: list[dict] = []

    def set_velocities(self, left: float, right: float) -> None:
        self._integrate()
        self._left_vel = left
        self._right_vel = right
        self._command_log.append({
            "time": time.monotonic(),
            "left": left,
            "right": right,
        })
        logger.debug("Mock motors: left=%.3f right=%.3f", left, right)

    def stop(self) -> None:
        self._integrate()
        self._left_vel = 0.0
        self._right_vel = 0.0
        logger.debug("Mock motors: stopped")

    def get_position(self) -> Position:
        self._integrate()
        return Position(x=self._x, y=self._y, heading=self._heading)

    def reset_position(self) -> None:
        self._x = 0.0
        self._y = 0.0
        self._heading = 0.0
        self._left_vel = 0.0
        self._right_vel = 0.0
        self._last_update = time.monotonic()

    def is_available(self) -> bool:
        return True

    def _integrate(self) -> None:
        now = time.monotonic()
        dt = now - self._last_update
        self._last_update = now

        if dt <= 0 or (self._left_vel == 0 and self._right_vel == 0):
            return

        v = (self._left_vel + self._right_vel) / 2.0
        omega = (self._right_vel - self._left_vel) / self._wheel_base

        self._x += v * math.cos(self._heading) * dt
        self._y += v * math.sin(self._heading) * dt
        self._heading += omega * dt

    @property
    def command_log(self) -> list[dict]:
        return list(self._command_log)
