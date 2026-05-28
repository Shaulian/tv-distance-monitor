import math
from pathlib import Path

import cv2
import numpy as np


class DriftDetectorError(Exception):
    pass


class DriftDetector:
    def __init__(self, reference_paths: dict, calibration: dict):
        cam0 = reference_paths.get("reference_cam0_path") or ""
        cam1 = reference_paths.get("reference_cam1_path") or ""
        self._ref0_path: Path | None = Path(cam0) if cam0 else None
        self._ref1_path: Path | None = Path(cam1) if cam1 else None
        self._slope = abs(calibration.get("slope") or 0.0)

    def check(self, camera_manager) -> tuple[float, str]:
        if not self._ref0_path or not self._ref0_path.exists():
            raise DriftDetectorError(f"Reference image not found: {self._ref0_path}")
        if not self._ref1_path or not self._ref1_path.exists():
            raise DriftDetectorError(f"Reference image not found: {self._ref1_path}")

        ref0 = cv2.imread(str(self._ref0_path), cv2.IMREAD_GRAYSCALE)
        ref1 = cv2.imread(str(self._ref1_path), cv2.IMREAD_GRAYSCALE)
        if ref0 is None:
            raise DriftDetectorError(f"Could not load reference image: {self._ref0_path}")
        if ref1 is None:
            raise DriftDetectorError(f"Could not load reference image: {self._ref1_path}")

        left, right = camera_manager.read_frames()
        max_shift = 0.0
        for ref, frame in ((ref0, left), (ref1, right)):
            if frame is None:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
            if gray.shape != ref.shape:
                gray = cv2.resize(gray, (ref.shape[1], ref.shape[0]))
            shift, _ = cv2.phaseCorrelate(ref.astype(np.float64), gray.astype(np.float64))
            max_shift = max(max_shift, math.hypot(shift[0], shift[1]))

        drift_cm = self._slope * max_shift
        if drift_cm < 5.0:
            severity = "none"
        elif drift_cm <= 20.0:
            severity = "minor"
        else:
            severity = "significant"
        return (drift_cm, severity)
