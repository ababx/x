from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Position:
    x: float  # meters
    y: float  # meters
    heading: float  # radians


class MotorController(ABC):
    @abstractmethod
    def set_velocities(self, left: float, right: float) -> None:
        """Set left and right wheel velocities in m/s."""

    @abstractmethod
    def stop(self) -> None:
        """Immediately stop all motors."""

    @abstractmethod
    def get_position(self) -> Position:
        """Get estimated position from odometry."""

    @abstractmethod
    def reset_position(self) -> None:
        """Reset position to origin."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if hardware is connected and ready."""
