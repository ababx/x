from __future__ import annotations

import logging

from smart_footrest.motion.controller import MotorController, Position

logger = logging.getLogger(__name__)

# TB6612FNG default pin mapping for RPi 5
DEFAULT_PINS = {
    "left_forward": 17,
    "left_backward": 27,
    "left_pwm": 12,
    "right_forward": 22,
    "right_backward": 23,
    "right_pwm": 13,
    "standby": 25,
}


class GPIOController(MotorController):
    """Real motor control via gpiozero and TB6612FNG driver.

    Only functional on Raspberry Pi. Raises RuntimeError on other platforms.
    """

    def __init__(self, pins: dict[str, int] | None = None):
        self._pins = pins or DEFAULT_PINS
        self._x = 0.0
        self._y = 0.0
        self._heading = 0.0

        try:
            from gpiozero import Motor, DigitalOutputDevice
            self._left_motor = Motor(
                forward=self._pins["left_forward"],
                backward=self._pins["left_backward"],
                enable=self._pins["left_pwm"],
            )
            self._right_motor = Motor(
                forward=self._pins["right_forward"],
                backward=self._pins["right_backward"],
                enable=self._pins["right_pwm"],
            )
            self._standby = DigitalOutputDevice(self._pins["standby"])
            self._standby.on()
            self._available = True
            logger.info("GPIO motor controller initialized")
        except Exception as e:
            logger.warning("GPIO not available: %s — use --mock for testing", e)
            self._available = False
            self._left_motor = None
            self._right_motor = None
            self._standby = None

    def set_velocities(self, left: float, right: float) -> None:
        if not self._available:
            raise RuntimeError("GPIO motors not available — run with --mock")

        max_speed = 0.15
        left_pct = max(-1.0, min(1.0, left / max_speed))
        right_pct = max(-1.0, min(1.0, right / max_speed))

        if left_pct >= 0:
            self._left_motor.forward(abs(left_pct))
        else:
            self._left_motor.backward(abs(left_pct))

        if right_pct >= 0:
            self._right_motor.forward(abs(right_pct))
        else:
            self._right_motor.backward(abs(right_pct))

    def stop(self) -> None:
        if self._available:
            self._left_motor.stop()
            self._right_motor.stop()

    def get_position(self) -> Position:
        return Position(x=self._x, y=self._y, heading=self._heading)

    def reset_position(self) -> None:
        self._x = 0.0
        self._y = 0.0
        self._heading = 0.0

    def is_available(self) -> bool:
        return self._available
