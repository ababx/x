from __future__ import annotations

import argparse
import logging
import signal
import sys
import time

from smart_footrest.config import load_config, AppConfig
from smart_footrest.motion.controller import MotorController
from smart_footrest.motion.drivers.mock import MockController
from smart_footrest.motion.planner import MotionPlanner, MotionCommand
from smart_footrest.safety.monitor import SafetyMonitor
from smart_footrest.state.machine import StateMachine, State
from smart_footrest.vision.camera import create_camera
from smart_footrest.vision.detector import FootDetector, MockDetector
from smart_footrest.vision.tracker import PositionTracker

logger = logging.getLogger("smart_footrest")


class FootrestController:
    def __init__(self, config: AppConfig, mock: bool = False):
        self._config = config
        self._mock = mock
        self._running = False

        self._camera = create_camera(config.camera, mock=mock)
        if mock:
            self._detector = MockDetector()
        else:
            self._detector = FootDetector(config.detection)
        self._tracker = PositionTracker(config.tracking)
        self._planner = MotionPlanner(config.motion)
        self._safety = SafetyMonitor(config.safety)
        self._state_machine = StateMachine(config.control, config.motion)

        if mock:
            self._motors: MotorController = MockController()
        else:
            from smart_footrest.motion.drivers.gpio import GPIOController
            self._motors = GPIOController()

    def run(self):
        self._running = True
        loop_period = 1.0 / self._config.control.loop_rate_hz
        last_time = time.monotonic()

        logger.info("Smart footrest starting (mock=%s, rate=%d Hz)", self._mock, self._config.control.loop_rate_hz)

        if hasattr(self._camera, "open"):
            self._camera.open()

        try:
            while self._running:
                loop_start = time.monotonic()
                dt = loop_start - last_time
                last_time = loop_start

                self._tick(dt)

                elapsed = time.monotonic() - loop_start
                sleep_time = loop_period - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        except KeyboardInterrupt:
            logger.info("Shutting down (keyboard interrupt)")
        finally:
            self._shutdown()

    def _tick(self, dt: float):
        # 1. Capture frame
        ok, frame = self._camera.read()
        if not ok:
            logger.warning("Camera read failed")
            return

        # 2. Detect feet
        detection = self._detector.detect(frame)

        # 3. Track position
        tracked = self._tracker.update(detection)

        # 4. Get current motor position
        position = self._motors.get_position()

        # 5. Plan motion (only if state allows motors)
        if self._state_machine.motors_allowed:
            command = self._planner.compute(
                position,
                self._state_machine.context.target_x,
                self._state_machine.context.target_y,
                dt,
            )
        else:
            command = MotionCommand(left_velocity=0.0, right_velocity=0.0, at_target=True)

        # 6. Safety check
        command = self._safety.clamp_command(command)
        safety = self._safety.check(position, command)
        if not safety.safe:
            logger.error("Safety violation: %s", safety.violation)
            self._state_machine.emergency_stop()
            self._motors.stop()
            return

        # 7. Update state machine
        self._state_machine.update(tracked, command.at_target)

        # 8. Execute motor commands
        if self._state_machine.motors_allowed:
            self._motors.set_velocities(command.left_velocity, command.right_velocity)
        else:
            self._motors.stop()

        # 9. Log status periodically
        if self._state_machine.context.frames_in_state % self._config.control.loop_rate_hz == 0:
            logger.info(
                "state=%s pos=(%.2f,%.2f) target=(%.2f,%.2f) tracked=%s",
                self._state_machine.state.name,
                position.x, position.y,
                self._state_machine.context.target_x,
                self._state_machine.context.target_y,
                tracked.valid,
            )

    def stop(self):
        self._running = False

    def _shutdown(self):
        logger.info("Shutting down")
        self._motors.stop()
        self._camera.release()
        self._detector.close()


def main():
    parser = argparse.ArgumentParser(description="Smart Footrest Controller")
    parser.add_argument("--config", type=str, default=None, help="Path to config YAML")
    parser.add_argument("--mock", action="store_true", help="Use mock camera and motors for testing")
    parser.add_argument("--log-level", type=str, default=None, help="Override log level")
    args = parser.parse_args()

    config = load_config(args.config)

    level = args.log_level or config.logging.level
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    controller = FootrestController(config, mock=args.mock)

    def handle_signal(signum, frame):
        logger.info("Signal %d received, stopping", signum)
        controller.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    controller.run()


if __name__ == "__main__":
    main()
