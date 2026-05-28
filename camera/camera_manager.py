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
        for cap in self._caps:
            if cap is not None and cap.isOpened():
                ret, frame = cap.read()
                frames.append(frame if ret else None)
            else:
                frames.append(None)
        return (frames[0], frames[1])

    def release(self) -> None:
        for cap in self._caps:
            if cap is not None:
                cap.release()
        self._caps = [None, None]
