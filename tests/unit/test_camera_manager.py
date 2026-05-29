import numpy as np
import pytest
from unittest.mock import MagicMock, call, patch

from camera.camera_manager import CameraManager

DUMMY_FRAME = np.zeros((480, 640, 3), dtype=np.uint8)


def _opened_cap(frame=None):
    f = DUMMY_FRAME if frame is None else frame
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.read.return_value = (True, f)
    return cap


def _closed_cap():
    cap = MagicMock()
    cap.isOpened.return_value = False
    return cap


# --- open_cameras: return values ---


def test_open_cameras_both_open():
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=[_opened_cap(), _opened_cap()]),
        patch("camera.camera_manager.time.monotonic", return_value=0.0),
        patch("camera.camera_manager.time.sleep"),
    ):
        result = CameraManager().open_cameras()
    assert result == (True, 2)


def test_open_cameras_one_open():
    # cam0 opens; cam1 never opens; timeout triggers after one retry
    caps = [_opened_cap(), _closed_cap(), _closed_cap()]
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=caps),
        patch("camera.camera_manager.time.monotonic", side_effect=[0.0, 0.1, 10.1]),
        patch("camera.camera_manager.time.sleep"),
    ):
        result = CameraManager().open_cameras()
    assert result == (True, 1)


def test_open_cameras_none_open():
    # both fail; deadline already passed after first attempt
    caps = [_closed_cap(), _closed_cap()]
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=caps),
        patch("camera.camera_manager.time.monotonic", side_effect=[0.0, 10.1]),
        patch("camera.camera_manager.time.sleep") as mock_sleep,
    ):
        result = CameraManager().open_cameras()
    assert result == (False, 0)
    mock_sleep.assert_not_called()


# --- open_cameras: exponential backoff ---


def test_open_cameras_first_retry_sleeps_500ms():
    # both fail round 1, both succeed round 2
    caps = [_closed_cap(), _closed_cap(), _opened_cap(), _opened_cap()]
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=caps),
        patch("camera.camera_manager.time.monotonic", side_effect=[0.0, 0.1]),
        patch("camera.camera_manager.time.sleep") as mock_sleep,
    ):
        CameraManager().open_cameras()
    mock_sleep.assert_called_once_with(0.5)


def test_open_cameras_backoff_doubles_on_second_retry():
    # fail, fail, succeed on 3rd attempt → sleep(0.5) then sleep(1.0)
    caps = [
        _closed_cap(),
        _closed_cap(),
        _closed_cap(),
        _closed_cap(),
        _opened_cap(),
        _opened_cap(),
    ]
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=caps),
        patch("camera.camera_manager.time.monotonic", side_effect=[0.0, 0.1, 0.7]),
        patch("camera.camera_manager.time.sleep") as mock_sleep,
    ):
        CameraManager().open_cameras()
    assert mock_sleep.call_args_list == [call(0.5), call(1.0)]


def test_open_cameras_sleep_capped_by_remaining_time():
    # delay would be 0.5 but only 0.3s remains → sleep 0.3
    caps = [_closed_cap(), _closed_cap(), _opened_cap(), _opened_cap()]
    # remaining = 10.0 - 9.7 = 0.3
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=caps),
        patch("camera.camera_manager.time.monotonic", side_effect=[0.0, 9.7]),
        patch("camera.camera_manager.time.sleep") as mock_sleep,
    ):
        CameraManager().open_cameras()
    mock_sleep.assert_called_once_with(pytest.approx(0.3, abs=1e-9))


# --- open_cameras: app_state ---


def test_open_cameras_updates_app_state_num_cameras_online():
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=[_opened_cap(), _opened_cap()]),
        patch("camera.camera_manager.time.monotonic", return_value=0.0),
        patch("camera.camera_manager.time.sleep"),
    ):
        app_state = MagicMock()
        CameraManager().open_cameras(app_state=app_state)
    assert app_state.num_cameras_online == 2


def test_open_cameras_app_state_reflects_partial_open():
    caps = [_opened_cap(), _closed_cap(), _closed_cap()]
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=caps),
        patch("camera.camera_manager.time.monotonic", side_effect=[0.0, 0.1, 10.1]),
        patch("camera.camera_manager.time.sleep"),
    ):
        app_state = MagicMock()
        CameraManager().open_cameras(app_state=app_state)
    assert app_state.num_cameras_online == 1


def test_open_cameras_no_app_state_does_not_raise():
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=[_opened_cap(), _opened_cap()]),
        patch("camera.camera_manager.time.monotonic", return_value=0.0),
        patch("camera.camera_manager.time.sleep"),
    ):
        CameraManager().open_cameras()  # must not raise


# --- read_frames ---


def test_read_frames_returns_both_frames_when_both_open():
    frame_l = np.ones((480, 640, 3), dtype=np.uint8)
    frame_r = np.full((480, 640, 3), 128, dtype=np.uint8)
    with (
        patch(
            "camera.camera_manager.cv2.VideoCapture",
            side_effect=[_opened_cap(frame_l), _opened_cap(frame_r)],
        ),
        patch("camera.camera_manager.time.monotonic", return_value=0.0),
        patch("camera.camera_manager.time.sleep"),
    ):
        mgr = CameraManager()
        mgr.open_cameras()
        left, right = mgr.read_frames()
    assert left is not None
    assert right is not None


def test_read_frames_left_drops_returns_none_frame():
    cap_l = MagicMock()
    cap_l.isOpened.return_value = True
    cap_l.read.return_value = (False, None)
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=[cap_l, _opened_cap()]),
        patch("camera.camera_manager.time.monotonic", return_value=0.0),
        patch("camera.camera_manager.time.sleep"),
    ):
        mgr = CameraManager()
        mgr.open_cameras()
        left, right = mgr.read_frames()
    assert left is None
    assert right is not None


def test_read_frames_right_drops_returns_frame_none():
    cap_r = MagicMock()
    cap_r.isOpened.return_value = True
    cap_r.read.return_value = (False, None)
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=[_opened_cap(), cap_r]),
        patch("camera.camera_manager.time.monotonic", return_value=0.0),
        patch("camera.camera_manager.time.sleep"),
    ):
        mgr = CameraManager()
        mgr.open_cameras()
        left, right = mgr.read_frames()
    assert left is not None
    assert right is None


def test_read_frames_before_open_returns_none_none():
    left, right = CameraManager().read_frames()
    assert left is None
    assert right is None


# --- release ---


def test_release_calls_release_on_both_caps():
    cap0, cap1 = _opened_cap(), _opened_cap()
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=[cap0, cap1]),
        patch("camera.camera_manager.time.monotonic", return_value=0.0),
        patch("camera.camera_manager.time.sleep"),
    ):
        mgr = CameraManager()
        mgr.open_cameras()
        mgr.release()
    cap0.release.assert_called_once()
    cap1.release.assert_called_once()


def test_release_resets_state_so_read_frames_returns_none_none():
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=[_opened_cap(), _opened_cap()]),
        patch("camera.camera_manager.time.monotonic", return_value=0.0),
        patch("camera.camera_manager.time.sleep"),
    ):
        mgr = CameraManager()
        mgr.open_cameras()
        mgr.release()
    left, right = mgr.read_frames()
    assert left is None
    assert right is None
