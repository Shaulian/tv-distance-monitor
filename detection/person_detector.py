import cv2


class PersonDetector:
    def __init__(self):
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self._frame_count = 0
        self._last_result: list = []

    def detect(self, frame) -> list:
        if self._frame_count % 3 != 0:
            self._frame_count += 1
            return self._last_result

        self._frame_count += 1
        boxes, _ = self._hog.detectMultiScale(frame, winStride=(8, 8), padding=(4, 4), scale=1.05)

        result = []
        for x, y, w, h in boxes:
            cx = x + w // 2
            cy = y + h // 2
            result.append((int(x), int(y), int(w), int(h), int(cx), int(cy)))

        self._last_result = result
        return result
