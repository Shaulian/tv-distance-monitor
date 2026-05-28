"""TV Distance Monitor — main entry point."""

from __future__ import annotations

import sys
import threading
import time

from audio.alert_manager import AlertManager
from camera.camera_manager import CameraManager
from camera.drift_detector import DriftDetector, DriftDetectorError
from camera.frame_processor import FrameProcessor
from camera.stereo_calibration import StereoCalibrator
from config.settings import load_settings, save_settings
from detection.depth_estimator import DepthEstimator
from detection.person_detector import PersonDetector
from state import AppState
from tray.tray_app import TrayApp

__version__ = "0.1.0"


def _camera_loop(
    camera_manager: CameraManager,
    frame_processor: FrameProcessor,
    detector: PersonDetector,
    depth_estimator: DepthEstimator,
    app_state: AppState,
    lock: threading.Lock,
    stop: threading.Event,
) -> None:
    while not stop.is_set():
        with lock:
            interval_ms = app_state.frame_capture_interval_ms
            paused = app_state.alert_paused

        frames = camera_manager.read_frames()
        camera_manager.detect_and_handle_drop(frames, app_state, lock)
        left, right = frames

        if left is not None and right is not None and not paused:
            left_n, right_n = frame_processor.process(left, right)
            dets_l = detector.detect(left_n)
            dets_r = detector.detect(right_n)
            distance = depth_estimator.estimate_distance(dets_l, dets_r)
            with lock:
                app_state.person_too_close = (
                    distance is not None and distance < app_state.min_safe_distance_m
                )

        time.sleep(interval_ms / 1000)


def main() -> None:
    settings = load_settings()
    calibration: dict = settings.get("calibration", {})

    state = AppState()
    state.min_safe_distance_m = settings.get("min_safe_distance_m", 1.5)
    state.frame_capture_interval_ms = settings.get("frame_capture_interval_ms", 100)
    state.alert_cooldown_seconds = settings.get("alert_cooldown_seconds", 3)
    state.alert_message = settings.get("alert_message", "Please move back from the TV")
    state.drift_threshold_minor_cm = settings.get("drift_threshold_minor_cm", 5.0)
    state.drift_threshold_significant_cm = settings.get("drift_threshold_significant_cm", 20.0)
    state.calibration_valid = bool(calibration.get("valid", False))

    lock = threading.Lock()
    stop = threading.Event()

    camera_manager = CameraManager()
    camera_manager.open_cameras(state)

    if state.calibration_valid:
        try:
            drift_checker = DriftDetector(calibration, calibration)
            _, severity = drift_checker.check(camera_manager)
            if severity == "significant":
                state.alert_paused = True
            elif severity == "minor":
                state.position_drift_warning = True
        except DriftDetectorError:
            pass  # reference images missing → skip drift check; not a hard error

    # Register autostart on first launch (Windows only)
    TrayApp.register_autostart_on_first_run()

    # Alert daemon thread
    threading.Thread(
        target=AlertManager().run,
        args=(lock, state),
        daemon=True,
    ).start()

    # Camera reconnect daemon thread
    threading.Thread(
        target=camera_manager.run_reconnect_loop,
        args=(state, lock, settings.get("camera_retry_interval_seconds", 5)),
        daemon=True,
    ).start()

    # Camera processing daemon thread (only when calibrated)
    if state.calibration_valid:
        depth_estimator = DepthEstimator(calibration)
        threading.Thread(
            target=_camera_loop,
            args=(
                camera_manager,
                FrameProcessor(),
                PersonDetector(),
                depth_estimator,
                state,
                lock,
                stop,
            ),
            daemon=True,
        ).start()

    calibrator = StereoCalibrator()

    def on_settings() -> None:
        from tray.settings_window import SettingsWindow

        def on_save(data: dict) -> None:
            settings.update(data)
            save_settings(settings)

        SettingsWindow(state, lock, camera_manager, calibrator, on_save=on_save).show()

    def on_quit() -> None:
        stop.set()
        camera_manager.release()
        sys.exit(0)

    TrayApp(state, lock, on_settings, on_quit).run()


if __name__ == "__main__":
    main()
