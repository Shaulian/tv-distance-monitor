import threading
from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest

from camera.camera_manager import CameraManager
from state import AppState

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


# --- detect_and_handle_drop ---


def test_drop_decrements_num_cameras_online():
    app_state = AppState(num_cameras_online=2, alert_paused=False)
    lock = threading.Lock()
    CameraManager().detect_and_handle_drop((None, DUMMY_FRAME), app_state, lock)
    assert app_state.num_cameras_online == 1


def test_drop_sets_alert_paused():
    app_state = AppState(num_cameras_online=2, alert_paused=False)
    lock = threading.Lock()
    CameraManager().detect_and_handle_drop((None, DUMMY_FRAME), app_state, lock)
    assert app_state.alert_paused is True


def test_both_drop_sets_num_cameras_to_zero():
    app_state = AppState(num_cameras_online=2, alert_paused=False)
    lock = threading.Lock()
    CameraManager().detect_and_handle_drop((None, None), app_state, lock)
    assert app_state.num_cameras_online == 0
    assert app_state.alert_paused is True


def test_no_drop_does_not_change_state():
    app_state = AppState(num_cameras_online=2, alert_paused=False)
    lock = threading.Lock()
    CameraManager().detect_and_handle_drop((DUMMY_FRAME, DUMMY_FRAME), app_state, lock)
    assert app_state.num_cameras_online == 2
    assert app_state.alert_paused is False


def test_drop_when_already_one_online_decrements_to_zero():
    app_state = AppState(num_cameras_online=1, alert_paused=True)
    lock = threading.Lock()
    CameraManager().detect_and_handle_drop((None, None), app_state, lock)
    assert app_state.num_cameras_online == 0


# --- read_frames invalidates cap on failed read ---


def test_read_frames_invalidates_cap_slot_on_failed_read():
    cap_l = MagicMock()
    cap_l.isOpened.return_value = True
    cap_l.read.return_value = (False, None)
    cap_r = _opened_cap()

    with patch("camera.camera_manager.cv2.VideoCapture", side_effect=[cap_l, cap_r]), \
         patch("camera.camera_manager.time.monotonic", return_value=0.0), \
         patch("camera.camera_manager.time.sleep"):
        mgr = CameraManager()
        mgr.open_cameras()
        mgr.read_frames()

    assert mgr._caps[0] is None  # invalidated so reconnect loop will retry it
    assert mgr._caps[1] is not None


# --- _reconnect_once ---


def test_reconnect_once_restores_num_cameras_online():
    app_state = AppState(num_cameras_online=1, alert_paused=True)
    lock = threading.Lock()

    with patch("camera.camera_manager.cv2.VideoCapture", side_effect=[_opened_cap(), _opened_cap()]), \
         patch("camera.camera_manager.time.monotonic", return_value=0.0), \
         patch("camera.camera_manager.time.sleep"):
        mgr = CameraManager()
        mgr._caps = [_opened_cap(), None]  # cam0 open, cam1 gone
        mgr._reconnect_once(app_state, lock)

    assert app_state.num_cameras_online == 2


def test_reconnect_once_clears_alert_paused_on_full_reconnect():
    app_state = AppState(num_cameras_online=1, alert_paused=True)
    lock = threading.Lock()

    with patch("camera.camera_manager.cv2.VideoCapture", side_effect=[_opened_cap()]), \
         patch("camera.camera_manager.time.monotonic", return_value=0.0), \
         patch("camera.camera_manager.time.sleep"):
        mgr = CameraManager()
        mgr._caps = [_opened_cap(), None]
        mgr._reconnect_once(app_state, lock)

    assert app_state.alert_paused is False


def test_reconnect_once_keeps_alert_paused_when_only_partial_reconnect():
    app_state = AppState(num_cameras_online=0, alert_paused=True)
    lock = threading.Lock()

    # Only cam0 reconnects, cam1 still fails → count=1, alert stays paused
    with patch("camera.camera_manager.cv2.VideoCapture", side_effect=[_opened_cap(), _closed_cap()]), \
         patch("camera.camera_manager.time.monotonic", side_effect=[0.0, 10.1]), \
         patch("camera.camera_manager.time.sleep"):
        mgr = CameraManager()
        mgr._caps = [None, None]
        mgr._reconnect_once(app_state, lock)

    assert app_state.num_cameras_online == 1
    assert app_state.alert_paused is True


def test_reconnect_once_skips_when_both_already_online():
    app_state = AppState(num_cameras_online=2, alert_paused=False)
    lock = threading.Lock()
    mgr = CameraManager()

    with patch.object(mgr, "open_cameras") as mock_open:
        mgr._reconnect_once(app_state, lock)

    mock_open.assert_not_called()


# --- run_reconnect_loop ---


def test_run_reconnect_loop_sleeps_for_configured_interval():
    app_state = AppState(num_cameras_online=1, alert_paused=True)
    lock = threading.Lock()
    stop = threading.Event()
    mgr = CameraManager()

    with patch("camera.camera_manager.time.sleep") as mock_sleep, \
         patch.object(mgr, "_reconnect_once", side_effect=lambda *a: stop.set()):
        t = threading.Thread(target=mgr.run_reconnect_loop, args=(app_state, lock, 5, stop))
        t.start()
        t.join(timeout=2.0)

    mock_sleep.assert_called_with(5)


def test_run_reconnect_loop_exits_when_stop_is_set():
    app_state = AppState(num_cameras_online=2)
    lock = threading.Lock()
    stop = threading.Event()
    stop.set()  # stop immediately
    mgr = CameraManager()

    with patch("camera.camera_manager.time.sleep"):
        t = threading.Thread(target=mgr.run_reconnect_loop, args=(app_state, lock, 5, stop))
        t.start()
        t.join(timeout=1.0)

    assert not t.is_alive()
