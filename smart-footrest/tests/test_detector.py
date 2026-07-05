import numpy as np

from smart_footrest.vision.detector import MockDetector, FootDetection, _NO_DETECTION


def test_mock_detector_returns_sequence():
    dets = [
        FootDetection(foot_present=True, foot_center_x=0.5, foot_center_y=0.8,
                       person_seated=True, confidence=0.9),
        FootDetection(foot_present=False, foot_center_x=0.0, foot_center_y=0.0,
                       person_seated=False, confidence=0.0),
    ]
    detector = MockDetector(dets)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    result1 = detector.detect(frame)
    assert result1.foot_present is True
    assert result1.confidence == 0.9

    result2 = detector.detect(frame)
    assert result2.foot_present is False

    result3 = detector.detect(frame)
    assert result3.foot_present is False
    assert result3 == _NO_DETECTION


def test_mock_detector_empty():
    detector = MockDetector()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = detector.detect(frame)
    assert result.foot_present is False


def test_foot_detection_dataclass():
    det = FootDetection(
        foot_present=True,
        foot_center_x=0.5,
        foot_center_y=0.7,
        person_seated=True,
        confidence=0.85,
        left_ankle=(0.4, 0.7),
        right_ankle=(0.6, 0.7),
    )
    assert det.left_ankle == (0.4, 0.7)
    assert det.right_ankle == (0.6, 0.7)
