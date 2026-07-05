#!/usr/bin/env python3
"""Visual camera test: opens webcam, runs MediaPipe Pose, overlays foot landmarks."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import cv2
import numpy as np

from smart_footrest.config import load_config
from smart_footrest.vision.detector import FootDetector

LANDMARK_COLOR = (0, 255, 0)
CENTER_COLOR = (0, 0, 255)
TEXT_COLOR = (255, 255, 255)


def main():
    config = load_config()
    cap = cv2.VideoCapture(config.camera.device_index)
    if not cap.isOpened():
        print(f"Error: cannot open camera at index {config.camera.device_index}")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.camera.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.camera.height)

    detector = FootDetector(config.detection)
    print("Camera test running. Press 'q' to quit.")

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        detection = detector.detect(frame)
        h, w = frame.shape[:2]

        if detection.foot_present:
            cx = int(detection.foot_center_x * w)
            cy = int(detection.foot_center_y * h)
            cv2.circle(frame, (cx, cy), 10, CENTER_COLOR, -1)
            cv2.putText(frame, f"Feet: ({cx}, {cy})", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_COLOR, 2)

            if detection.left_ankle:
                lx, ly = int(detection.left_ankle[0] * w), int(detection.left_ankle[1] * h)
                cv2.circle(frame, (lx, ly), 6, LANDMARK_COLOR, -1)
                cv2.putText(frame, "L", (lx + 8, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.5, LANDMARK_COLOR, 1)

            if detection.right_ankle:
                rx, ry = int(detection.right_ankle[0] * w), int(detection.right_ankle[1] * h)
                cv2.circle(frame, (rx, ry), 6, LANDMARK_COLOR, -1)
                cv2.putText(frame, "R", (rx + 8, ry), cv2.FONT_HERSHEY_SIMPLEX, 0.5, LANDMARK_COLOR, 1)

        seated_text = "SEATED" if detection.person_seated else "STANDING/ABSENT"
        cv2.putText(frame, seated_text, (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_COLOR, 2)
        cv2.putText(frame, f"Confidence: {detection.confidence:.2f}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, TEXT_COLOR, 2)

        cv2.imshow("Smart Footrest - Camera Test", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    detector.close()


if __name__ == "__main__":
    main()
