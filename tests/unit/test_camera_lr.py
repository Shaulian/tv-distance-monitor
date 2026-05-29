"""Tests for camera left/right index assignment in CameraManager and settings helpers."""

from unittest.mock import MagicMock, patch

import numpy as np

from camera.camera_manager import CameraManager
from config.settings import DEFAULTS
from tray.settings_subprocess import swap_camera

FRAME_A = np.zeros((480, 640, 3), dtype=np.uint8)
FRAME_B = np.ones((480, 640, 3), dtype=np.uint8) * 128


def _cap(frame):
    c = MagicMock()
    c.isOpened.return_value = True
    c.read.return_value = (True, frame)
    return c


def _closed_cap():
    c = MagicMock()
    c.isOpened.return_value = False
    return c


# ── settings defaults ──────────────────────────────────────────────────────────


def test_settings_defaults_include_left_camera_index():
    assert "left_camera_index" in DEFAULTS
    assert DEFAULTS["left_camera_index"] == 0


def test_settings_defaults_include_right_camera_index():
    assert "right_camera_index" in DEFAULTS
    assert DEFAULTS["right_camera_index"] == 1


# ── CameraManager: custom L/R indices ─────────────────────────────────────────


def test_camera_manager_opens_custom_left_index():
    """left_camera_index=1 → VideoCapture(1) must be called (not VideoCapture(0) first)."""
    mgr = CameraManager(left_camera_index=1, right_camera_index=0)
    caps = {0: _cap(FRAME_A), 1: _cap(FRAME_B)}
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=lambda i: caps[i]),
        patch("camera.camera_manager.time.sleep"),
        patch("camera.camera_manager.time.monotonic", side_effect=[0.0, 0.0, 11.0]),
    ):
        mgr.open_cameras()
    # both indices opened — verify by checking read_frames returns correctly
    left, right = mgr.read_frames()
    assert np.array_equal(left, FRAME_B), "left frame should come from camera index 1"
    assert np.array_equal(right, FRAME_A), "right frame should come from camera index 0"


def test_read_frames_default_indices_unchanged():
    """Default left=0, right=1 must preserve existing behaviour."""
    mgr = CameraManager(left_camera_index=0, right_camera_index=1)
    caps = {0: _cap(FRAME_A), 1: _cap(FRAME_B)}
    with (
        patch("camera.camera_manager.cv2.VideoCapture", side_effect=lambda i: caps[i]),
        patch("camera.camera_manager.time.sleep"),
        patch("camera.camera_manager.time.monotonic", side_effect=[0.0, 0.0, 11.0]),
    ):
        mgr.open_cameras()
    left, right = mgr.read_frames()
    assert np.array_equal(left, FRAME_A)
    assert np.array_equal(right, FRAME_B)


def test_one_camera_mode_uses_left_index():
    """--one-camera respects left_camera_index, not always 0."""
    mgr = CameraManager(one_camera_mode=True, left_camera_index=1, right_camera_index=0)
    with patch("camera.camera_manager.cv2.VideoCapture", return_value=_cap(FRAME_B)) as mock_vc:
        mgr.open_cameras()
        called_index = mock_vc.call_args[0][0]
    assert called_index == 1


# ── swap_camera pure function ─────────────────────────────────────────────────


def test_swap_camera_changing_left_to_right_index_swaps():
    left, right = swap_camera(old_left=0, old_right=1, changed="left", new_val=1)
    assert left == 1 and right == 0


def test_swap_camera_changing_right_to_left_index_swaps():
    left, right = swap_camera(old_left=0, old_right=1, changed="right", new_val=0)
    assert left == 1 and right == 0


def test_swap_camera_no_collision_no_swap():
    """If new value doesn't collide with the other side, just update and keep the other."""
    # Two-camera scenario where indices could be 0 and 1; no collision
    left, right = swap_camera(old_left=0, old_right=1, changed="left", new_val=0)
    assert left == 0 and right == 1


def test_swap_camera_result_always_distinct():
    """Left and right must never end up equal after a swap."""
    for changed, new_val in [("left", 1), ("right", 0), ("left", 0), ("right", 1)]:
        left, right = swap_camera(0, 1, changed, new_val)
        assert left != right, f"collision after swap_camera(0,1,{changed!r},{new_val})"
