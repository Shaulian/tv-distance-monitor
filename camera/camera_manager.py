import threading
import time

import cv2


class CameraManager:
    def __init__(
        self,
        one_camera_mode: bool = False,
        left_camera_index: int = 0,
        right_camera_index: int = 1,
    ):
        self._one_camera_mode = one_camera_mode
        self._left_idx = left_camera_index
        self._right_idx = right_camera_index
        # Indexed by physical camera index; size covers both indices.
        size = max(left_camera_index, right_camera_index) + 1
        self._caps: list = [None] * size

    def open_cameras(self, app_state=None) -> tuple[bool, int]:
        if self._one_camera_mode:
            return self._open_one_camera(app_state)

        deadline = time.monotonic() + 10.0
        delay = 0.5

        while True:
            for i in (self._left_idx, self._right_idx):
                if self._caps[i] is None or not self._caps[i].isOpened():
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        self._caps[i] = cap
                    else:
                        cap.release()

            count = sum(
                1
                for i in (self._left_idx, self._right_idx)
                if self._caps[i] is not None and self._caps[i].isOpened()
            )
            if count == 2:
                break

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break

            time.sleep(min(delay, remaining))
            delay *= 2

        count = sum(
            1
            for i in (self._left_idx, self._right_idx)
            if self._caps[i] is not None and self._caps[i].isOpened()
        )

        if app_state is not None:
            app_state.num_cameras_online = count

        return (count > 0, count)

    def _open_one_camera(self, app_state=None) -> tuple[bool, int]:
        cap = cv2.VideoCapture(self._left_idx)
        if cap.isOpened():
            self._caps[self._left_idx] = cap
            count = 1
        else:
            cap.release()
            count = 0
        if app_state is not None:
            app_state.num_cameras_online = count
        return (count > 0, count)

    def _read_single(self, idx: int):
        cap = self._caps[idx] if idx < len(self._caps) else None
        if cap is not None and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                self._caps[idx] = None
                return None
            return frame
        return None

    def read_frames(self) -> tuple:
        if self._one_camera_mode:
            cap = self._caps[self._left_idx] if self._left_idx < len(self._caps) else None
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    self._caps[self._left_idx] = None
                    return (None, None)
                return (frame, None)
            return (None, None)

        return (self._read_single(self._left_idx), self._read_single(self._right_idx))

    def detect_and_handle_drop(self, frames: tuple, app_state, lock: threading.Lock) -> None:
        left, right = frames
        online = sum(1 for f in (left, right) if f is not None)
        with lock:
            if online < app_state.num_cameras_online:
                app_state.num_cameras_online = online
                app_state.alert_paused = True

    def _reconnect_once(self, app_state, lock: threading.Lock) -> None:
        with lock:
            if app_state.num_cameras_online == 2:
                return
        _, count = self.open_cameras()
        with lock:
            app_state.num_cameras_online = count
            if count == 2:
                app_state.alert_paused = False

    def run_reconnect_loop(
        self, app_state, lock: threading.Lock, interval: int = 5, _stop: threading.Event = None
    ) -> None:
        while _stop is None or not _stop.is_set():
            time.sleep(interval)
            self._reconnect_once(app_state, lock)

    def wait_for_camera_permission(
        self, app_state, timeout: float = 5.0, interval: float = 0.5
    ) -> None:
        """Wait up to `timeout` seconds for a camera that opened but yields no frames yet.

        On macOS the system permission dialog is shown on the first capture attempt;
        cv2.VideoCapture.read() returns (False, None) until access is granted.
        """
        cap = self._caps[self._left_idx] if self._left_idx < len(self._caps) else None
        if cap is None or not cap.isOpened():
            return

        ret, _ = cap.read()
        if ret:
            return

        app_state.awaiting_camera_permission = True
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            time.sleep(interval)
            ret, _ = cap.read()
            if ret:
                app_state.awaiting_camera_permission = False
                return

        app_state.awaiting_camera_permission = False
        app_state.num_cameras_online = 0

    def release(self) -> None:
        for cap in self._caps:
            if cap is not None:
                cap.release()
        self._caps = [None] * len(self._caps)
