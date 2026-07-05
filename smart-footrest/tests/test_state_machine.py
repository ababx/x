import pytest

from smart_footrest.config import ControlConfig, MotionConfig
from smart_footrest.state.machine import StateMachine, State
from smart_footrest.vision.tracker import TrackedPosition


def make_tracked(valid=True, seated=True, foot=True, x=0.5, y=0.5):
    return TrackedPosition(
        x=x, y=y, valid=valid, person_seated=seated,
        foot_present=foot, confidence=0.9 if valid else 0.0,
        frames_since_detection=0,
    )


def make_no_person():
    return TrackedPosition(
        x=0.0, y=0.0, valid=False, person_seated=False,
        foot_present=False, confidence=0.0, frames_since_detection=100,
    )


@pytest.fixture
def sm():
    return StateMachine(ControlConfig(stable_detection_frames=3, person_lost_frames=5), MotionConfig())


def test_startup_to_idle(sm):
    assert sm.state == State.STARTUP
    sm.update(make_no_person(), at_target=False)
    assert sm.state == State.IDLE


def test_idle_to_person_detected(sm):
    sm.update(make_no_person(), at_target=False)  # STARTUP -> IDLE
    sm.update(make_tracked(), at_target=False)
    assert sm.state == State.PERSON_DETECTED


def test_person_detected_to_moving(sm):
    sm.update(make_no_person(), at_target=False)  # -> IDLE
    sm.update(make_tracked(), at_target=False)  # -> PERSON_DETECTED

    for _ in range(3):
        sm.update(make_tracked(), at_target=False)

    assert sm.state == State.MOVING


def test_moving_to_positioned(sm):
    sm.update(make_no_person(), at_target=False)  # -> IDLE
    sm.update(make_tracked(), at_target=False)  # -> PERSON_DETECTED
    for _ in range(3):
        sm.update(make_tracked(), at_target=False)  # -> MOVING

    sm.update(make_tracked(), at_target=True)
    assert sm.state == State.POSITIONED


def test_positioned_to_adjusting(sm):
    sm.update(make_no_person(), at_target=False)  # -> IDLE
    sm.update(make_tracked(), at_target=False)  # -> PERSON_DETECTED
    for _ in range(3):
        sm.update(make_tracked(), at_target=False)  # -> MOVING
    sm.update(make_tracked(), at_target=True)  # -> POSITIONED

    # Move feet beyond adjustment threshold
    moved = make_tracked(x=0.5 + 0.15, y=0.5)
    sm.update(moved, at_target=False)
    assert sm.state == State.ADJUSTING


def test_retracting_when_person_leaves(sm):
    sm.update(make_no_person(), at_target=False)  # -> IDLE
    sm.update(make_tracked(), at_target=False)  # -> PERSON_DETECTED
    for _ in range(3):
        sm.update(make_tracked(), at_target=False)  # -> MOVING

    for _ in range(5):
        sm.update(make_no_person(), at_target=False)

    assert sm.state == State.RETRACTING


def test_retracting_to_idle(sm):
    sm.update(make_no_person(), at_target=False)  # -> IDLE
    sm.update(make_tracked(), at_target=False)  # -> PERSON_DETECTED
    for _ in range(3):
        sm.update(make_tracked(), at_target=False)  # -> MOVING
    for _ in range(5):
        sm.update(make_no_person(), at_target=False)  # -> RETRACTING

    sm.update(make_no_person(), at_target=True)
    assert sm.state == State.IDLE


def test_emergency_stop_from_any_state(sm):
    sm.update(make_no_person(), at_target=False)  # -> IDLE
    sm.emergency_stop()
    assert sm.state == State.E_STOP
    assert sm.motors_allowed is False


def test_reset_from_estop(sm):
    sm.update(make_no_person(), at_target=False)  # -> IDLE
    sm.emergency_stop()
    sm.reset_from_estop()
    assert sm.state == State.IDLE


def test_motors_only_allowed_in_motion_states(sm):
    sm.update(make_no_person(), at_target=False)  # -> IDLE
    assert sm.motors_allowed is False

    sm.update(make_tracked(), at_target=False)  # -> PERSON_DETECTED
    assert sm.motors_allowed is False

    for _ in range(3):
        sm.update(make_tracked(), at_target=False)  # -> MOVING
    assert sm.motors_allowed is True
