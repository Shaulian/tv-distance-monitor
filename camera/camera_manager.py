import threading
import time

import cv2


class CameraManager:
    def __init__(self, one_camera_mode: bool = False):
        self._one_camera_mode = one_camera_mode
        self._caps: list = [None, None]

    def open_cameras(self, app_state=None) -> tuple[bool, int]:
        if self._one_camera_mode:
            return self._open_one_camera(app_state)

        deadline = time.monotonic() + 10.0
        delay = 0.5

        while True:
            for i in range(2):
                if self._caps[i] is None or not self._caps[i].isOpened():
                    cap = cv2.VideoCapture(i)
                    if cap.isOpened():
                        self._caps[i] = cap
                    else:
                        cap.release()

            count = sum(1 for c in self._caps if c is not None and c.isOpened())
            if count == 2:
                break

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break

            time.sleep(min(delay, remaining))
            delay *= 2

        count = sum(1 for c in self._caps if c is not None and c.isOpened())

        if app_state is not None:
            app_state.num_cameras_online = count

        return (count > 0, count)

    def _open_one_camera(self, app_state=None) -> tuple[bool, int]:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            self._caps[0] = cap
            count = 1
        else:
            cap.release()
            count = 0
        if app_state is not None:
            app_state.num_cameras_online = count
        return (count > 0, count)

    def wait_for_camera_permission(
        self, app_state, timeout: float = 5.0, interval: float = 0.5
    ) -> None:
        """Wait up to `timeout` seconds for a camera that opened but yields no frames yet.

        On macOS the system permission dialog is shown on the first capture attempt;
        cv2.VideoCapture.read() returns (False, None) until access is granted.
        """
        cap = self._caps[0]
        if cap is None or not cap.isOpened():
            return  # camera didn't open at all; nothing to wait for

        ret, _ = cap.read()
        if ret:
            return  # frames already arriving; no permission delay

        app_state.awaiting_camera_permission = True
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            time.sleep(interval)
            ret, _ = cap.read()
            if ret:
                app_state.awaiting_camera_permission = False
                return

        # Timeout reached; permission was never granted
        app_state.awaiting_camera_permission = False
        app_state.num_cameras_online = 0

    def read_frames(self) -> tuple:
        if self._one_camera_mode:
            cap = self._caps[0]
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    self._caps[0] = None
                    return (None, None)
                return (frame, None)
            return (None, None)

        frames = []
        for i, cap in enumerate(self._caps):
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    self._caps[i] = None  # invalidate so reconnect loop retries it
                    frames.append(None)
                else:
                    frames.append(frame)
            else:
                frames.append(None)
        return (frames[0], frames[1])

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

    def release(self) -> None:
        for cap in self._caps:
            if cap is not None:
                cap.release()
        self._caps = [None, None]
