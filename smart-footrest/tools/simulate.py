#!/usr/bin/env python3
"""2D simulation: visualizes the footrest tracking a simulated foot target."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import math
import time

from smart_footrest.config import load_config
from smart_footrest.motion.drivers.mock import MockController
from smart_footrest.motion.planner import MotionPlanner, MotionCommand
from smart_footrest.safety.monitor import SafetyMonitor
from smart_footrest.state.machine import StateMachine, State
from smart_footrest.vision.tracker import TrackedPosition

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle
    _MPL = True
except ImportError:
    _MPL = False


def simulate_foot_path(t: float) -> tuple[float, float]:
    """Simulates a foot position that moves slowly over time."""
    x = 0.3 + 0.1 * math.sin(t * 0.5)
    y = 0.4 + 0.05 * math.cos(t * 0.3)
    return x, y


def run_simulation(duration: float = 20.0, dt: float = 0.05):
    config = load_config()
    motors = MockController()
    planner = MotionPlanner(config.motion)
    safety = SafetyMonitor(config.safety)
    sm = StateMachine(config.control, config.motion)

    footrest_xs, footrest_ys = [], []
    target_xs, target_ys = [], []
    times = []
    states = []

    t = 0.0
    person_present = False

    print(f"Running {duration}s simulation (dt={dt}s)...")
    print("Scenario: person sits at t=2s, stays until t=15s, leaves")

    while t < duration:
        # Simulate person arriving at t=2, leaving at t=15
        if 2.0 <= t <= 15.0:
            person_present = True
            fx, fy = simulate_foot_path(t)
        else:
            person_present = False
            fx, fy = 0.0, 0.0

        tracked = TrackedPosition(
            x=fx, y=fy, valid=person_present,
            person_seated=person_present, foot_present=person_present,
            confidence=0.9 if person_present else 0.0,
            frames_since_detection=0 if person_present else 100,
        )

        position = motors.get_position()

        if sm.motors_allowed:
            command = planner.compute(position, sm.context.target_x, sm.context.target_y, dt)
        else:
            command = MotionCommand(0.0, 0.0, at_target=True)

        command = safety.clamp_command(command)
        status = safety.check(position, command)
        if not status.safe:
            sm.emergency_stop()
            motors.stop()
            print(f"  t={t:.1f}s SAFETY: {status.violation}")
            break

        sm.update(tracked, command.at_target)

        if sm.motors_allowed:
            motors.set_velocities(command.left_velocity, command.right_velocity)
        else:
            motors.stop()

        footrest_xs.append(position.x)
        footrest_ys.append(position.y)
        target_xs.append(fx)
        target_ys.append(fy)
        times.append(t)
        states.append(sm.state.name)

        if int(t / dt) % int(1.0 / dt) == 0:
            print(f"  t={t:.1f}s state={sm.state.name} pos=({position.x:.3f},{position.y:.3f}) target=({fx:.3f},{fy:.3f})")

        t += dt

    print(f"\nSimulation complete. Final state: {sm.state.name}")
    print(f"Motor commands issued: {len(motors.command_log)}")

    if _MPL:
        save_plot(times, footrest_xs, footrest_ys, target_xs, target_ys, states)
    else:
        print("(Install matplotlib for trajectory plot: pip install matplotlib)")


def save_plot(times, fx, fy, tx, ty, states):
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    axes[0].plot(tx, ty, "r--", label="Foot target", alpha=0.7)
    axes[0].plot(fx, fy, "b-", label="Footrest position", linewidth=2)
    axes[0].set_xlabel("X (meters)")
    axes[0].set_ylabel("Y (meters)")
    axes[0].set_title("Top-Down View: Footrest Tracking")
    axes[0].legend()
    axes[0].set_aspect("equal")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(times, fx, "b-", label="Footrest X")
    axes[1].plot(times, tx, "r--", label="Target X")
    axes[1].set_xlabel("Time (s)")
    axes[1].set_ylabel("X Position (meters)")
    axes[1].set_title("Position Over Time")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    out = os.path.join(os.path.dirname(__file__), "..", "simulation_output.png")
    plt.savefig(out, dpi=100)
    print(f"Plot saved to {out}")


if __name__ == "__main__":
    run_simulation()
