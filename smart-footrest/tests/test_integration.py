"""Integration test: full control loop with mock camera and motors."""

from smart_footrest.config import AppConfig, ControlConfig, MotionConfig
from smart_footrest.motion.drivers.mock import MockController
from smart_footrest.motion.planner import MotionPlanner, MotionCommand
from smart_footrest.safety.monitor import SafetyMonitor
from smart_footrest.state.machine import StateMachine, State
from smart_footrest.vision.detector import FootDetection, MockDetector
from smart_footrest.vision.tracker import PositionTracker


def run_loop(state_machine, tracker, planner, motors, safety, detector, n_ticks, dt=0.05):
    """Run the control loop for n_ticks and return final state."""
    import numpy as np
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    for _ in range(n_ticks):
        detection = detector.detect(frame)
        tracked = tracker.update(detection)
        position = motors.get_position()

        if state_machine.motors_allowed:
            command = planner.compute(
                position,
                state_machine.context.target_x,
                state_machine.context.target_y,
                dt,
            )
        else:
            command = MotionCommand(0.0, 0.0, at_target=True)

        command = safety.clamp_command(command)
        status = safety.check(position, command)
        if not status.safe:
            state_machine.emergency_stop()
            motors.stop()
            break

        state_machine.update(tracked, command.at_target)

        if state_machine.motors_allowed:
            motors.set_velocities(command.left_velocity, command.right_velocity)
        else:
            motors.stop()

    return state_machine.state


def test_full_loop_person_sits_and_leaves():
    config = AppConfig(
        control=ControlConfig(stable_detection_frames=3, person_lost_frames=5),
    )

    seated = FootDetection(
        foot_present=True, foot_center_x=0.5, foot_center_y=0.5,
        person_seated=True, confidence=0.9,
    )
    no_person = FootDetection(
        foot_present=False, foot_center_x=0.0, foot_center_y=0.0,
        person_seated=False, confidence=0.0,
    )

    # Sequence: startup, then person appears for 20 frames, then leaves for 10
    detections = [no_person] + [seated] * 20 + [no_person] * 10
    detector = MockDetector(detections)
    tracker = PositionTracker(config.tracking)
    planner = MotionPlanner(config.motion)
    motors = MockController()
    safety = SafetyMonitor(config.safety)
    sm = StateMachine(config.control, config.motion)

    final_state = run_loop(sm, tracker, planner, motors, safety, detector, len(detections))

    # After person leaves for enough frames, should be retracting or idle
    assert final_state in (State.RETRACTING, State.IDLE)


def test_estop_on_geofence():
    config = AppConfig(control=ControlConfig(stable_detection_frames=1, person_lost_frames=5))

    seated = FootDetection(
        foot_present=True, foot_center_x=0.5, foot_center_y=0.5,
        person_seated=True, confidence=0.9,
    )
    detections = [seated] * 100
    detector = MockDetector(detections)
    tracker = PositionTracker(config.tracking)
    planner = MotionPlanner(config.motion)
    motors = MockController()
    safety = SafetyMonitor(config.safety)
    sm = StateMachine(config.control, config.motion)

    # Manually set motors way out of bounds to trigger geofence
    motors._x = 2.0
    motors._y = 0.0

    final_state = run_loop(sm, tracker, planner, motors, safety, detector, 10)
    assert final_state == State.E_STOP


def test_motors_log_commands():
    config = AppConfig(control=ControlConfig(stable_detection_frames=2, person_lost_frames=5))
    seated = FootDetection(
        foot_present=True, foot_center_x=0.6, foot_center_y=0.5,
        person_seated=True, confidence=0.9,
    )
    detections = [FootDetection(foot_present=False, foot_center_x=0, foot_center_y=0,
                                person_seated=False, confidence=0.0)] + [seated] * 15

    detector = MockDetector(detections)
    tracker = PositionTracker(config.tracking)
    planner = MotionPlanner(config.motion)
    motors = MockController()
    safety = SafetyMonitor(config.safety)
    sm = StateMachine(config.control, config.motion)

    run_loop(sm, tracker, planner, motors, safety, detector, len(detections))
    # Once the state machine starts moving, motor commands should be logged
    assert len(motors.command_log) > 0
