import math

from smart_footrest.config import MotionConfig
from smart_footrest.motion.controller import Position
from smart_footrest.motion.planner import MotionPlanner


def test_at_target_returns_zero(motion_config):
    planner = MotionPlanner(motion_config)
    pos = Position(x=0.5, y=0.5, heading=0.0)
    cmd = planner.compute(pos, target_x=0.5, target_y=0.5, dt=0.05)
    assert cmd.at_target is True
    assert cmd.left_velocity == 0.0
    assert cmd.right_velocity == 0.0


def test_moves_toward_target(motion_config):
    planner = MotionPlanner(motion_config)
    pos = Position(x=0.0, y=0.0, heading=0.0)
    cmd = planner.compute(pos, target_x=0.5, target_y=0.0, dt=0.05)
    assert cmd.at_target is False
    assert cmd.left_velocity > 0 or cmd.right_velocity > 0


def test_speed_capped(motion_config):
    planner = MotionPlanner(motion_config)
    pos = Position(x=0.0, y=0.0, heading=0.0)
    # Large distance to push speed to max
    cmd = planner.compute(pos, target_x=10.0, target_y=0.0, dt=0.05)
    assert abs(cmd.left_velocity) <= motion_config.max_speed
    assert abs(cmd.right_velocity) <= motion_config.max_speed


def test_deadband(motion_config):
    config = MotionConfig(
        kp=0.001, kd=0.0, max_speed=0.1,
        min_speed=0.01, acceleration_limit=10.0,
        position_tolerance=0.03, adjustment_threshold=0.08,
    )
    planner = MotionPlanner(config)
    pos = Position(x=0.0, y=0.0, heading=0.0)
    cmd = planner.compute(pos, target_x=0.04, target_y=0.0, dt=0.05)
    # Very small error with tiny kp should produce velocity below deadband
    assert cmd.left_velocity == 0.0 or cmd.at_target


def test_planner_reset(motion_config):
    planner = MotionPlanner(motion_config)
    pos = Position(x=0.0, y=0.0, heading=0.0)
    planner.compute(pos, target_x=1.0, target_y=0.0, dt=0.05)
    planner.reset()
    assert planner._prev_error_dist == 0.0
