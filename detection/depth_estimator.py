_VERTICAL_MATCH_PX = 20


class DepthEstimator:
    def __init__(self, calibration: dict):
        self._slope = calibration["slope"]
        self._intercept = calibration["intercept"]

    def estimate_distance(
        self,
        detections_left: list,
        detections_right: list,
    ) -> float | None:
        best: float | None = None
        for *_, cxl, cyl in detections_left:
            for *_, cxr, cyr in detections_right:
                if abs(cyl - cyr) > _VERTICAL_MATCH_PX:
                    continue
                distance = self._intercept + self._slope * (cxl - cxr)
                if best is None or distance < best:
                    best = distance
        return best
