from __future__ import annotations

import logging
from enum import Enum, auto
from dataclasses import dataclass

from smart_footrest.config import ControlConfig, MotionConfig
from smart_footrest.vision.tracker import TrackedPosition

logger = logging.getLogger(__name__)


class State(Enum):
    STARTUP = auto()
    IDLE = auto()
    PERSON_DETECTED = auto()
    MOVING = auto()
    POSITIONED = auto()
    ADJUSTING = auto()
    RETRACTING = auto()
    E_STOP = auto()


@dataclass
class StateContext:
    target_x: float = 0.0
    target_y: float = 0.0
    frames_in_state: int = 0
    stable_detection_count: int = 0
    frames_without_person: int = 0


class StateMachine:
    def __init__(self, control_config: ControlConfig, motion_config: MotionConfig):
        self._control = control_config
        self._motion = motion_config
        self._state = State.STARTUP
        self._ctx = StateContext()
        self._motors_allowed = False

    @property
    def state(self) -> State:
        return self._state

    @property
    def context(self) -> StateContext:
        return self._ctx

    @property
    def motors_allowed(self) -> bool:
        return self._motors_allowed

    def emergency_stop(self):
        self._transition(State.E_STOP)

    def reset_from_estop(self):
        if self._state == State.E_STOP:
            self._transition(State.IDLE)

    def update(self, tracked: TrackedPosition, at_target: bool) -> State:
        self._ctx.frames_in_state += 1
        handler = _STATE_HANDLERS.get(self._state)
        if handler:
            handler(self, tracked, at_target)
        return self._state

    def _transition(self, new_state: State):
        if new_state == self._state:
            return
        logger.info("State: %s -> %s", self._state.name, new_state.name)
        old = self._state
        self._state = new_state
        self._ctx.frames_in_state = 0
        self._motors_allowed = new_state in (State.MOVING, State.ADJUSTING, State.RETRACTING)

        if new_state == State.E_STOP:
            self._motors_allowed = False

        if new_state in (State.IDLE, State.STARTUP):
            self._ctx.stable_detection_count = 0
            self._ctx.frames_without_person = 0

    def _handle_startup(self, tracked: TrackedPosition, at_target: bool):
        self._transition(State.IDLE)

    def _handle_idle(self, tracked: TrackedPosition, at_target: bool):
        if tracked.valid and tracked.person_seated and tracked.foot_present:
            self._transition(State.PERSON_DETECTED)

    def _handle_person_detected(self, tracked: TrackedPosition, at_target: bool):
        if not tracked.valid or not tracked.person_seated:
            self._transition(State.IDLE)
            return

        self._ctx.stable_detection_count += 1
        self._ctx.target_x = tracked.x
        self._ctx.target_y = tracked.y

        if self._ctx.stable_detection_count >= self._control.stable_detection_frames:
            self._transition(State.MOVING)

    def _handle_moving(self, tracked: TrackedPosition, at_target: bool):
        if not tracked.person_seated and not tracked.foot_present:
            self._ctx.frames_without_person += 1
            if self._ctx.frames_without_person >= self._control.person_lost_frames:
                self._transition(State.RETRACTING)
            return

        self._ctx.frames_without_person = 0

        if tracked.valid:
            self._ctx.target_x = tracked.x
            self._ctx.target_y = tracked.y

        if at_target:
            self._transition(State.POSITIONED)

    def _handle_positioned(self, tracked: TrackedPosition, at_target: bool):
        if not tracked.person_seated and not tracked.foot_present:
            self._ctx.frames_without_person += 1
            if self._ctx.frames_without_person >= self._control.person_lost_frames:
                self._transition(State.RETRACTING)
            return

        self._ctx.frames_without_person = 0

        if tracked.valid:
            dx = abs(tracked.x - self._ctx.target_x)
            dy = abs(tracked.y - self._ctx.target_y)
            if dx > self._motion.adjustment_threshold or dy > self._motion.adjustment_threshold:
                self._ctx.target_x = tracked.x
                self._ctx.target_y = tracked.y
                self._transition(State.ADJUSTING)

    def _handle_adjusting(self, tracked: TrackedPosition, at_target: bool):
        if not tracked.person_seated and not tracked.foot_present:
            self._ctx.frames_without_person += 1
            if self._ctx.frames_without_person >= self._control.person_lost_frames:
                self._transition(State.RETRACTING)
            return

        self._ctx.frames_without_person = 0

        if tracked.valid:
            self._ctx.target_x = tracked.x
            self._ctx.target_y = tracked.y

        if at_target:
            self._transition(State.POSITIONED)

    def _handle_retracting(self, tracked: TrackedPosition, at_target: bool):
        self._ctx.target_x = 0.0
        self._ctx.target_y = 0.0

        if tracked.valid and tracked.person_seated and tracked.foot_present:
            self._transition(State.PERSON_DETECTED)
            return

        if at_target:
            self._transition(State.IDLE)

    def _handle_estop(self, tracked: TrackedPosition, at_target: bool):
        pass


_STATE_HANDLERS = {
    State.STARTUP: StateMachine._handle_startup,
    State.IDLE: StateMachine._handle_idle,
    State.PERSON_DETECTED: StateMachine._handle_person_detected,
    State.MOVING: StateMachine._handle_moving,
    State.POSITIONED: StateMachine._handle_positioned,
    State.ADJUSTING: StateMachine._handle_adjusting,
    State.RETRACTING: StateMachine._handle_retracting,
    State.E_STOP: StateMachine._handle_estop,
}
