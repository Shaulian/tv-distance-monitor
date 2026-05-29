import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from camera.stereo_calibration import CalibrationError, StereoCalibrator

DUMMY = np.zeros((480, 640, 3), dtype=np.uint8)


def _det(cx, cy=240):
    return [(0, 0, 50, 100, cx, cy)]


def _camera_mgr(left=DUMMY, right=DUMMY):
    mgr = MagicMock()
    mgr.read_frames.return_value = (left, right)
    return mgr


# --- calibrate_diamond: linear fit accuracy ---


def test_calibrate_diamond_slope_and_intercept_within_1_percent():
    # True relationship: distance = 0.0 + 0.05 * disparity
    # 4 positions (frames_per_point=1 to keep side_effect list short):
    #   dist=0.5 → disp=10: cx_l=325, cx_r=315
    #   dist=1.0 → disp=20: cx_l=330, cx_r=310
    #   dist=1.5 → disp=30: cx_l=335, cx_r=305
    #   dist=2.0 → disp=40: cx_l=340, cx_r=300
    detect_returns = [
        _det(325),
        _det(315),
        _det(330),
        _det(310),
        _det(335),
        _det(305),
        _det(340),
        _det(300),
    ]
    with patch("camera.stereo_calibration.PersonDetector") as MockDet:
        MockDet.return_value.detect.side_effect = detect_returns
        calib = StereoCalibrator().calibrate_diamond(
            _camera_mgr(),
            lambda i, n: None,
            distances_m=(0.5, 1.0, 1.5, 2.0),
            frames_per_point=1,
        )
    assert calib["valid"] is True
    assert calib["slope"] == pytest.approx(0.05, rel=0.01)
    assert calib["intercept"] == pytest.approx(0.0, abs=0.005)


# --- calibrate_diamond: ui_callback ---


def test_calibrate_diamond_calls_ui_callback_once_per_point():
    detect_returns = [
        _det(325),
        _det(315),
        _det(330),
        _det(310),
        _det(335),
        _det(305),
        _det(340),
        _det(300),
    ]
    callback = MagicMock()
    with patch("camera.stereo_calibration.PersonDetector") as MockDet:
        MockDet.return_value.detect.side_effect = detect_returns
        StereoCalibrator().calibrate_diamond(
            _camera_mgr(),
            callback,
            distances_m=(0.5, 1.0, 1.5, 2.0),
            frames_per_point=1,
        )
    assert callback.call_count == 4
    assert callback.call_args_list == [call(0, 4), call(1, 4), call(2, 4), call(3, 4)]


# --- calibrate_diamond: CalibrationError ---


def test_calibrate_diamond_raises_when_no_detections_at_all():
    with patch("camera.stereo_calibration.PersonDetector") as MockDet:
        MockDet.return_value.detect.return_value = []
        with pytest.raises(CalibrationError):
            StereoCalibrator().calibrate_diamond(_camera_mgr(), lambda i, n: None)


def test_calibrate_diamond_raises_when_only_one_valid_point():
    # Only position 0 yields a detection; positions 1-3 get empty lists
    detect_returns = [_det(325), _det(315)] + [[], []] * 3  # pos 0: valid  # pos 1-3: no detections
    with patch("camera.stereo_calibration.PersonDetector") as MockDet:
        MockDet.return_value.detect.side_effect = detect_returns
        with pytest.raises(CalibrationError):
            StereoCalibrator().calibrate_diamond(
                _camera_mgr(),
                lambda i, n: None,
                distances_m=(0.5, 1.0, 1.5, 2.0),
                frames_per_point=1,
            )


def test_calibrate_diamond_succeeds_with_exactly_two_valid_points():
    detect_returns = [
        _det(325),
        _det(315),  # pos 0: valid
        _det(330),
        _det(310),
    ] + [  # pos 1: valid
        [],
        [],
    ] * 2  # pos 2-3: no detections
    with patch("camera.stereo_calibration.PersonDetector") as MockDet:
        MockDet.return_value.detect.side_effect = detect_returns
        calib = StereoCalibrator().calibrate_diamond(
            _camera_mgr(),
            lambda i, n: None,
            distances_m=(0.5, 1.0, 1.5, 2.0),
            frames_per_point=1,
        )
    assert calib["valid"] is True


# --- save_reference_scene ---


def test_save_reference_scene_creates_two_png_files(tmp_path):
    with patch("camera.stereo_calibration.cv2.imwrite") as mock_write:
        StereoCalibrator().save_reference_scene(_camera_mgr(), tmp_path)
    assert mock_write.call_count == 2
    paths_written = [call.args[0] for call in mock_write.call_args_list]
    assert any("reference_cam0.png" in p for p in paths_written)
    assert any("reference_cam1.png" in p for p in paths_written)


def test_save_reference_scene_returns_paths_in_dict(tmp_path):
    with patch("camera.stereo_calibration.cv2.imwrite"):
        result = StereoCalibrator().save_reference_scene(_camera_mgr(), tmp_path)
    assert "reference_cam0_path" in result
    assert "reference_cam1_path" in result
    assert result["reference_cam0_path"].endswith("reference_cam0.png")
    assert result["reference_cam1_path"].endswith("reference_cam1.png")


def test_save_reference_scene_paths_are_inside_dest_dir(tmp_path):
    with patch("camera.stereo_calibration.cv2.imwrite"):
        result = StereoCalibrator().save_reference_scene(_camera_mgr(), tmp_path)
    assert Path(result["reference_cam0_path"]).parent == tmp_path
    assert Path(result["reference_cam1_path"]).parent == tmp_path


def test_save_reference_scene_overwrites_existing_files(tmp_path):
    # imwrite is always called regardless of whether file already exists
    (tmp_path / "reference_cam0.png").write_bytes(b"old")
    (tmp_path / "reference_cam1.png").write_bytes(b"old")
    with patch("camera.stereo_calibration.cv2.imwrite") as mock_write:
        StereoCalibrator().save_reference_scene(_camera_mgr(), tmp_path)
    assert mock_write.call_count == 2
