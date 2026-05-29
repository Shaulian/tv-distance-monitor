"""End-to-end integration: camera → frame processor → person detection → depth.

Drives main._camera_loop with the production wiring and a fake camera manager
that yields one stereo frame pair, then triggers the loop's stop event. This
test exercises the exact code path main.py runs in production — a regression
that causes left/right detections to collide (e.g. sharing a PersonDetector
between cameras so the frame-skip cache cross-contaminates) is caught here
and not by the unit suite, where PersonDetector is mocked with isolated fresh
instances.

Marked with @pytest.mark.integration so the dedicated CI job runs it.
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

import numpy as np
import pytest

from camera.frame_processor import FrameProcessor
from detection.depth_estimator import DepthEstimator
from detection.person_detector import PersonDetector
from main import _camera_loop
from state import AppState

pytestmark = pytest.mark.integration


# Calibration tuned so the correct and the buggy answer land on opposite
# sides of the safety threshold:
#   - Correct (disparity 50): distance = 0.5 + 0.04 * 50 = 2.5 m → 2.5 > 1.5 → safe
#   - Buggy   (disparity  0): distance = 0.5 + 0.04 *  0 = 0.5 m → 0.5 < 1.5 → false alarm
_CALIBRATION = {"slope": 0.04, "intercept": 0.5, "valid": True}
_MIN_SAFE_DISTANCE_M = 1.5

# Person bounding boxes — left camera sees the person at cx=200, right at cx=150.
# HOG is patched per detector to return these so the test doesn't depend on
# the (unreliable) ability of HOG to detect a person in a synthetic frame.
_LEFT_BOX = np.array([[180, 100, 40, 200]], dtype=np.int32)  # cx = 200
_RIGHT_BOX = np.array([[130, 100, 40, 200]], dtype=np.int32)  # cx = 150 → disparity 50


def _make_state() -> tuple[AppState, threading.Lock]:
    state = AppState()
    state.num_cameras_online = 2
    state.alert_paused = False
    state.min_safe_distance_m = _MIN_SAFE_DISTANCE_M
    state.frame_capture_interval_ms = 0  # zero sleep between loop iterations
    return state, threading.Lock()


def _one_shot_camera_manager(stop: threading.Event) -> MagicMock:
    """A camera manager that returns one BGR frame pair on its first call,
    then sets the loop's stop event and returns (None, None) so subsequent
    iterations short-circuit and the loop exits at the next while-check.
    """
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    frames_remaining: list[tuple[np.ndarray, np.ndarray]] = [(blank.copy(), blank.copy())]

    def _read_frames() -> tuple:
        if frames_remaining:
            return frames_remaining.pop(0)
        stop.set()
        return (None, None)

    mgr = MagicMock()
    mgr.read_frames.side_effect = _read_frames
    return mgr


def _patched_detector(boxes: np.ndarray) -> PersonDetector:
    detector = PersonDetector()
    detector._hog = MagicMock()
    detector._hog.detectMultiScale.return_value = (boxes, None)
    return detector


def test_production_camera_loop_computes_correct_distance_from_stereo_pair():
    """A person seen at cx=200 (left) and cx=150 (right) yields disparity 50 →
    distance 2.5 m > 1.5 m safe → person_too_close must be False.

    Regression guard for the shared-detector defect: when one PersonDetector
    is reused across both cameras, its per-instance frame-skip cache returns
    the first frame's detection for the second call, disparity collapses to
    0, distance collapses to the calibration intercept (0.5 m), and
    person_too_close is reported True even when the person is safely 2.5 m
    away. Per ADR-015, the loop now takes one detector per camera.
    """
    state, lock = _make_state()
    stop = threading.Event()
    camera_manager = _one_shot_camera_manager(stop)

    detector_left = _patched_detector(_LEFT_BOX)
    detector_right = _patched_detector(_RIGHT_BOX)

    _camera_loop(
        camera_manager,
        FrameProcessor(),
        detector_left,
        detector_right,
        DepthEstimator(_CALIBRATION),
        state,
        lock,
        stop,
    )

    assert state.person_too_close is False, (
        "Pipeline must compute distance from disparity 50 (2.5 m, safe). "
        "If reported True, the camera loop is sharing one PersonDetector "
        "between cameras and the frame-skip cache is collapsing disparity to 0."
    )


def test_camera_loop_signature_takes_one_detector_per_camera():
    """Structural regression guard: ADR-015 specifies one PersonDetector per
    camera. If _camera_loop's signature is ever collapsed back to a single
    `detector` argument, this test fails fast and points at the ADR — well
    before the behavioural test above silently degrades.
    """
    import inspect

    params = inspect.signature(_camera_loop).parameters
    assert "detector_left" in params and "detector_right" in params, (
        "_camera_loop must accept `detector_left` and `detector_right` "
        "(see ADR-015). A single shared detector collapses stereo disparity."
    )
