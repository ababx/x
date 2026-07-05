from smart_footrest.config import TrackingConfig
from smart_footrest.vision.detector import FootDetection
from smart_footrest.vision.tracker import PositionTracker


def test_tracker_updates_on_detection(tracking_config):
    tracker = PositionTracker(tracking_config)
    det = FootDetection(
        foot_present=True, foot_center_x=0.5, foot_center_y=0.5,
        person_seated=True, confidence=0.9,
    )
    result = tracker.update(det)
    assert result.valid is True
    assert result.foot_present is True
    assert result.frames_since_detection == 0


def test_tracker_holds_position_during_dropout(tracking_config):
    tracker = PositionTracker(tracking_config)
    det = FootDetection(
        foot_present=True, foot_center_x=0.5, foot_center_y=0.5,
        person_seated=True, confidence=0.9,
    )
    tracker.update(det)

    no_det = FootDetection(
        foot_present=False, foot_center_x=0.0, foot_center_y=0.0,
        person_seated=True, confidence=0.0,
    )

    for i in range(tracking_config.dropout_hold_frames):
        result = tracker.update(no_det)
        assert result.valid is True
        assert result.frames_since_detection == i + 1


def test_tracker_invalidates_after_hold_expires(tracking_config):
    tracker = PositionTracker(tracking_config)
    det = FootDetection(
        foot_present=True, foot_center_x=0.5, foot_center_y=0.5,
        person_seated=True, confidence=0.9,
    )
    tracker.update(det)

    no_det = FootDetection(
        foot_present=False, foot_center_x=0.0, foot_center_y=0.0,
        person_seated=False, confidence=0.0,
    )

    for _ in range(tracking_config.dropout_hold_frames + 1):
        result = tracker.update(no_det)

    assert result.valid is False


def test_tracker_smoothing():
    config = TrackingConfig(smoothing_alpha=0.5, dropout_hold_frames=5, pixels_per_meter=500.0)
    tracker = PositionTracker(config)

    det1 = FootDetection(
        foot_present=True, foot_center_x=0.5, foot_center_y=0.5,
        person_seated=True, confidence=0.9,
    )
    r1 = tracker.update(det1)

    det2 = FootDetection(
        foot_present=True, foot_center_x=0.7, foot_center_y=0.5,
        person_seated=True, confidence=0.9,
    )
    r2 = tracker.update(det2)

    # With alpha=0.5, the smoothed value should be between the two raw values
    assert r1.x != r2.x


def test_tracker_reset(tracking_config):
    tracker = PositionTracker(tracking_config)
    det = FootDetection(
        foot_present=True, foot_center_x=0.5, foot_center_y=0.5,
        person_seated=True, confidence=0.9,
    )
    tracker.update(det)
    tracker.reset()

    no_det = FootDetection(
        foot_present=False, foot_center_x=0.0, foot_center_y=0.0,
        person_seated=False, confidence=0.0,
    )
    result = tracker.update(no_det)
    assert result.valid is False
