from unittest.mock import MagicMock, patch


from camera.camera_manager import CameraManager
from state import AppState


def _mock_cap_with_read_sequence(read_results: list):
    """Cap that is opened and returns successive (ret, frame) tuples from read_results."""
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.read.side_effect = read_results
    return cap


class TestCameraPermissionGracePeriod:
    def test_flag_false_by_default(self):
        assert AppState().awaiting_camera_permission is False

    def test_no_grace_period_needed_when_frames_arrive_immediately(self):
        """If camera returns frames on first read, flag stays False."""
        state = AppState()
        mgr = CameraManager(one_camera_mode=True)
        frame = MagicMock()
        cap = _mock_cap_with_read_sequence([(True, frame)])
        with patch("cv2.VideoCapture", return_value=cap):
            mgr.open_cameras(state)

        with patch("time.sleep"):
            mgr.wait_for_camera_permission(state, timeout=5.0, interval=0.5)

        assert state.awaiting_camera_permission is False
        assert state.num_cameras_online == 1

    def test_flag_set_while_waiting_then_cleared_when_frames_arrive(self):
        """Flag is True during the wait, then False once a frame is returned."""
        state = AppState()
        mgr = CameraManager(one_camera_mode=True)
        frame = MagicMock()
        # First two reads: no frame (permission denied); third: frame received
        cap = _mock_cap_with_read_sequence([(False, None), (False, None), (True, frame)])
        with patch("cv2.VideoCapture", return_value=cap):
            mgr.open_cameras(state)

        flag_during_wait = []

        def capture_flag(seconds):
            flag_during_wait.append(state.awaiting_camera_permission)

        with patch("time.sleep", side_effect=capture_flag):
            mgr.wait_for_camera_permission(state, timeout=5.0, interval=0.5)

        assert True in flag_during_wait, "Flag should have been True during at least one retry"
        assert state.awaiting_camera_permission is False, "Flag should be cleared after success"

    def test_flag_cleared_and_degraded_after_timeout(self):
        """If permission is never granted, flag is cleared and num_cameras_online is 0."""
        state = AppState()
        mgr = CameraManager(one_camera_mode=True)
        cap = _mock_cap_with_read_sequence([(False, None)] * 20)
        with patch("cv2.VideoCapture", return_value=cap):
            mgr.open_cameras(state)

        with patch("time.sleep"):
            with patch("time.monotonic", side_effect=[0.0] + [i * 0.5 for i in range(1, 15)]):
                mgr.wait_for_camera_permission(state, timeout=5.0, interval=0.5)

        assert state.awaiting_camera_permission is False
        assert state.num_cameras_online == 0

    def test_no_wait_when_no_camera_opened(self):
        """If camera failed to open entirely, grace period is skipped."""
        state = AppState()
        mgr = CameraManager(one_camera_mode=True)
        cap = MagicMock()
        cap.isOpened.return_value = False
        with patch("cv2.VideoCapture", return_value=cap):
            mgr.open_cameras(state)

        with patch("time.sleep") as mock_sleep:
            mgr.wait_for_camera_permission(state, timeout=5.0, interval=0.5)

        mock_sleep.assert_not_called()
        assert state.awaiting_camera_permission is False
