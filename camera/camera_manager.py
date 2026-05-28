import threading
import time

import cv2


class CameraManager:
    def __init__(self):
        self._caps: list = [None, None]

    def open_cameras(self, app_state=None) -> tuple[bool, int]:
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

    def read_frames(self) -> tuple:
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
