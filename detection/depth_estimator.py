_VERTICAL_MATCH_PX = 20
_MAX_PLAUSIBLE_DISTANCE_M = 10.0


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

    def assess_proximity(
        self,
        detections_left: list,
        detections_right: list,
        min_safe_distance_m: float,
    ) -> tuple[bool, str]:
        """Decide whether a person is too close, with a fail-safe default.

        Returns (person_too_close, reason). Reason is one of:
          "no_person"     — neither camera saw a person; no alert.
          "ok"            — stereo distance computed and within sanity bounds.
          "unmatched"     — at least one camera saw a person but no trusted
                            stereo match → fail-safe person_too_close=True.
          "out_of_range"  — distance computed but physically implausible
                            (≤ 0 m or > 10 m) → fail-safe person_too_close=True.

        Per ADR-016 ("degrade loud, not silent"), the dangerous failure
        direction for a child-distance monitor is silence; ambiguity must
        trigger an alert, never suppress one.
        """
        if not detections_left and not detections_right:
            return (False, "no_person")

        distance = self.estimate_distance(detections_left, detections_right)
        if distance is None:
            return (True, "unmatched")

        if distance <= 0.0 or distance > _MAX_PLAUSIBLE_DISTANCE_M:
            return (True, "out_of_range")

        return (distance < min_safe_distance_m, "ok")
