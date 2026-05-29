from unittest.mock import MagicMock, patch


from camera.camera_manager import CameraManager
from state import AppState


def _mock_cap(opened: bool, read_ok: bool = True):
    cap = MagicMock()
    cap.isOpened.return_value = opened
    frame = MagicMock() if read_ok else None
    cap.read.return_value = (read_ok, frame)
    return cap


class TestOneCameraMode:
    def test_open_cameras_one_camera_mode_opens_only_index_0(self):
        """--one-camera must never open index 1."""
        mgr = CameraManager(one_camera_mode=True)
        with patch("cv2.VideoCapture", side_effect=[_mock_cap(True)]) as mock_vc:
            mgr.open_cameras()
            indices = [call.args[0] for call in mock_vc.call_args_list]
        assert indices == [0], "Only index 0 should be opened in one-camera mode"

    def test_open_cameras_one_camera_sets_num_cameras_online_to_1(self):
        state = AppState()
        mgr = CameraManager(one_camera_mode=True)
        with patch("cv2.VideoCapture", return_value=_mock_cap(True)):
            mgr.open_cameras(state)
        assert state.num_cameras_online == 1

    def test_open_cameras_one_camera_failure_sets_num_cameras_online_to_0(self):
        state = AppState()
        mgr = CameraManager(one_camera_mode=True)
        with patch("cv2.VideoCapture", return_value=_mock_cap(False)):
            mgr.open_cameras(state)
        assert state.num_cameras_online == 0

    def test_read_frames_returns_frame_and_none_in_one_camera_mode(self):
        mgr = CameraManager(one_camera_mode=True)
        with patch("cv2.VideoCapture", return_value=_mock_cap(True)):
            mgr.open_cameras()
        left, right = mgr.read_frames()
        assert left is not None
        assert right is None

    def test_normal_mode_still_opens_both_cameras(self):
        """Default (two-camera) mode must open indices 0 and 1."""
        mgr = CameraManager(one_camera_mode=False)
        caps = [_mock_cap(True), _mock_cap(True)]
        with patch("cv2.VideoCapture", side_effect=caps) as mock_vc:
            # Patch time so the retry loop doesn't spin for 10 s
            with patch("time.sleep"), patch("time.monotonic", side_effect=[0.0, 0.0, 11.0]):
                mgr.open_cameras()
            indices = [call.args[0] for call in mock_vc.call_args_list]
        assert 0 in indices and 1 in indices
