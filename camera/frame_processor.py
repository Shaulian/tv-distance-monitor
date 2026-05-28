import cv2
import numpy as np


class FrameProcessor:
    def process(
        self, left: np.ndarray, right: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        h_l, w_l = left.shape[:2]
        h_r, w_r = right.shape[:2]

        if h_l == h_r and w_l == w_r:
            return left, right

        target_h = min(h_l, h_r)
        target_w = min(w_l, w_r)
        target = (target_w, target_h)  # cv2 uses (width, height)

        left_out = (
            left
            if (h_l, w_l) == (target_h, target_w)
            else cv2.resize(left, target, interpolation=cv2.INTER_AREA)
        )
        right_out = (
            right
            if (h_r, w_r) == (target_h, target_w)
            else cv2.resize(right, target, interpolation=cv2.INTER_AREA)
        )
        return left_out, right_out
