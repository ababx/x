import time

from smart_footrest.config import SafetyConfig
from smart_footrest.motion.controller import Position
from smart_footrest.motion.planner import MotionCommand
from smart_footrest.safety.monitor import SafetyMonitor


def test_safe_within_limits(safety_config):
    monitor = SafetyMonitor(safety_config)
    pos = Position(x=0.0, y=0.0, heading=0.0)
    cmd = MotionCommand(left_velocity=0.05, right_velocity=0.05, at_target=False)
    status = monitor.check(pos, cmd)
    assert status.safe is True


def test_geofence_x_violation(safety_config):
    monitor = SafetyMonitor(safety_config)
    pos = Position(x=1.5, y=0.0, heading=0.0)
    cmd = MotionCommand(left_velocity=0.0, right_velocity=0.0, at_target=True)
    status = monitor.check(pos, cmd)
    assert status.safe is False
    assert "Geofence X" in status.violation


def test_geofence_y_violation(safety_config):
    monitor = SafetyMonitor(safety_config)
    pos = Position(x=0.0, y=1.5, heading=0.0)
    cmd = MotionCommand(left_velocity=0.0, right_velocity=0.0, at_target=True)
    status = monitor.check(pos, cmd)
    assert status.safe is False
    assert "Geofence Y" in status.violation


def test_speed_violation(safety_config):
    monitor = SafetyMonitor(safety_config)
    pos = Position(x=0.0, y=0.0, heading=0.0)
    cmd = MotionCommand(left_velocity=0.5, right_velocity=0.5, at_target=False)
    status = monitor.check(pos, cmd)
    assert status.safe is False
    assert "Speed" in status.violation


def test_clamp_command(safety_config):
    monitor = SafetyMonitor(safety_config)
    cmd = MotionCommand(left_velocity=1.0, right_velocity=-1.0, at_target=False)
    clamped = monitor.clamp_command(cmd)
    assert abs(clamped.left_velocity) <= safety_config.max_speed_hard_limit
    assert abs(clamped.right_velocity) <= safety_config.max_speed_hard_limit


def test_reset(safety_config):
    monitor = SafetyMonitor(safety_config)
    monitor.reset()
    pos = Position(x=0.0, y=0.0, heading=0.0)
    cmd = MotionCommand(left_velocity=0.0, right_velocity=0.0, at_target=True)
    status = monitor.check(pos, cmd)
    assert status.safe is True
