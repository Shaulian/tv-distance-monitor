from pathlib import Path

import cv2
import numpy as np

from detection.person_detector import PersonDetector

DIAMOND_DISTANCES_M = (0.5, 1.0, 1.5, 2.0)


class CalibrationError(Exception):
    pass


class StereoCalibrator:
    def calibrate_diamond(
        self,
        camera_manager,
        ui_callback,
        distances_m=DIAMOND_DISTANCES_M,
        frames_per_point: int = 5,
    ) -> dict:
        # Per ADR-015: one PersonDetector per camera. PersonDetector's
        # frame-skip cache is per-instance; sharing one across both cameras
        # collapses stereo disparity to 0 and corrupts the calibration curve.
        detector_left = PersonDetector()
        detector_right = PersonDetector()
        points: list[tuple[float, float]] = []  # (disparity, distance_m)

        for i, distance_m in enumerate(distances_m):
            ui_callback(i, len(distances_m))
            disparities: list[float] = []

            for _ in range(frames_per_point):
                left, right = camera_manager.read_frames()
                if left is None or right is None:
                    continue
                dets_l = detector_left.detect(left)
                dets_r = detector_right.detect(right)
                if not dets_l or not dets_r:
                    continue
                cx_l = dets_l[0][4]
                cx_r = dets_r[0][4]
                disparities.append(float(cx_l - cx_r))

            if disparities:
                points.append((sum(disparities) / len(disparities), distance_m))

        if len(points) < 2:
            raise CalibrationError(
                f"Calibration needs ≥2 valid detections, got {len(points)}. "
                "Ensure both cameras can see you at each calibration point."
            )

        disparities_arr = np.array([p[0] for p in points])
        distances_arr = np.array([p[1] for p in points])
        slope, intercept = np.polyfit(disparities_arr, distances_arr, 1)

        return {
            "valid": True,
            "slope": float(slope),
            "intercept": float(intercept),
        }

    def save_reference_scene(self, camera_manager, dest_dir) -> dict:
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)

        left, right = camera_manager.read_frames()

        path0 = dest / "reference_cam0.png"
        path1 = dest / "reference_cam1.png"

        cv2.imwrite(str(path0), left)
        cv2.imwrite(str(path1), right)

        return {
            "reference_cam0_path": str(path0),
            "reference_cam1_path": str(path1),
        }
