from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

from camera.drift_detector import DriftDetector, DriftDetectorError

_BLANK = np.zeros((480, 640), dtype=np.uint8)


def _camera_mgr(left=None, right=None):
    mgr = MagicMock()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    mgr.read_frames.return_value = (
        left if left is not None else frame,
        right if right is not None else frame,
    )
    return mgr


def _camera_none():
    mgr = MagicMock()
    mgr.read_frames.return_value = (None, None)
    return mgr


def _detector(tmp_path, slope=1.0, write_refs=True):
    ref0 = tmp_path / "reference_cam0.png"
    ref1 = tmp_path / "reference_cam1.png"
    if write_refs:
        cv2.imwrite(str(ref0), _BLANK)
        cv2.imwrite(str(ref1), _BLANK)
    return DriftDetector(
        {"reference_cam0_path": str(ref0), "reference_cam1_path": str(ref1)},
        {"slope": slope},
    )


# --- Error cases ---


def test_missing_reference_raises(tmp_path):
    d = _detector(tmp_path, write_refs=False)
    with pytest.raises(DriftDetectorError):
        d.check(_camera_mgr())


def test_empty_path_raises():
    d = DriftDetector({"reference_cam0_path": "", "reference_cam1_path": ""}, {"slope": 1.0})
    with pytest.raises(DriftDetectorError):
        d.check(_camera_mgr())


def test_none_path_raises():
    d = DriftDetector({"reference_cam0_path": None, "reference_cam1_path": None}, {"slope": 1.0})
    with pytest.raises(DriftDetectorError):
        d.check(_camera_mgr())


# --- Severity thresholds ---


def test_zero_shift_returns_none(tmp_path):
    d = _detector(tmp_path, slope=1.0)
    with patch("camera.drift_detector.cv2.phaseCorrelate") as mock_pc:
        mock_pc.return_value = ((0.0, 0.0), 1.0)
        drift_cm, severity = d.check(_camera_mgr())
    assert drift_cm == pytest.approx(0.0)
    assert severity == "none"


def test_10px_shift_slope_1_returns_minor(tmp_path):
    d = _detector(tmp_path, slope=1.0)
    with patch("camera.drift_detector.cv2.phaseCorrelate") as mock_pc:
        mock_pc.return_value = ((10.0, 0.0), 1.0)
        drift_cm, severity = d.check(_camera_mgr())
    assert drift_cm == pytest.approx(10.0)
    assert severity == "minor"


def test_30px_shift_slope_1_returns_significant(tmp_path):
    d = _detector(tmp_path, slope=1.0)
    with patch("camera.drift_detector.cv2.phaseCorrelate") as mock_pc:
        mock_pc.return_value = ((30.0, 0.0), 1.0)
        drift_cm, severity = d.check(_camera_mgr())
    assert drift_cm == pytest.approx(30.0)
    assert severity == "significant"


def test_30px_shift_low_slope_returns_minor(tmp_path):
    d = _detector(tmp_path, slope=0.4)
    with patch("camera.drift_detector.cv2.phaseCorrelate") as mock_pc:
        mock_pc.return_value = ((30.0, 0.0), 1.0)
        drift_cm, severity = d.check(_camera_mgr())
    # drift_cm = 0.4 * 30 = 12.0 → minor
    assert drift_cm == pytest.approx(12.0)
    assert severity == "minor"


def test_4px_shift_slope_1_returns_none(tmp_path):
    d = _detector(tmp_path, slope=1.0)
    with patch("camera.drift_detector.cv2.phaseCorrelate") as mock_pc:
        mock_pc.return_value = ((4.0, 0.0), 1.0)
        drift_cm, severity = d.check(_camera_mgr())
    assert drift_cm == pytest.approx(4.0)
    assert severity == "none"


# --- Frame handling ---


def test_none_frames_give_zero_drift(tmp_path):
    d = _detector(tmp_path, slope=1.0)
    drift_cm, severity = d.check(_camera_none())
    assert drift_cm == 0.0
    assert severity == "none"


def test_max_drift_taken_across_cameras(tmp_path):
    d = _detector(tmp_path, slope=1.0)
    with patch("camera.drift_detector.cv2.phaseCorrelate") as mock_pc:
        # cam0: 5px, cam1: 25px → max is 25
        mock_pc.side_effect = [((5.0, 0.0), 1.0), ((25.0, 0.0), 1.0)]
        drift_cm, severity = d.check(_camera_mgr())
    assert drift_cm == pytest.approx(25.0)
    assert severity == "significant"


def test_slope_zero_always_returns_none(tmp_path):
    d = _detector(tmp_path, slope=0.0)
    with patch("camera.drift_detector.cv2.phaseCorrelate") as mock_pc:
        mock_pc.return_value = ((100.0, 100.0), 1.0)
        drift_cm, severity = d.check(_camera_mgr())
    assert drift_cm == 0.0
    assert severity == "none"


def test_diagonal_shift_uses_hypot(tmp_path):
    d = _detector(tmp_path, slope=1.0)
    with patch("camera.drift_detector.cv2.phaseCorrelate") as mock_pc:
        # shift (3, 4) → hypot = 5 → drift_cm = 5.0 (boundary none/minor)
        mock_pc.return_value = ((3.0, 4.0), 1.0)
        drift_cm, severity = d.check(_camera_mgr())
    assert drift_cm == pytest.approx(5.0)
    assert severity == "minor"  # 5.0 is not < 5.0, so → minor
