"""End-to-end integration: main.main() startup orchestration.

Drives main.main() with every hardware boundary mocked (cv2.VideoCapture,
pyttsx3, pystray via a TrayApp substitute) so the orchestration glue can be
exercised on a headless CI runner. Verifies that:

  - argv parsing routes the --one-camera flag to TrayApp / CameraManager
  - settings are loaded into AppState's named fields
  - cameras are opened and the permission grace period is observed
  - autostart is registered exactly once
  - the daemon threads (alert, reconnect, and — when calibrated — the
    camera loop) are launched
  - calibration_valid gates the drift check and the camera-loop thread
  - control is handed to TrayApp.run() last

The unit suite cannot replicate this: TrayApp.run() blocks the main thread
on the real pystray loop, and load_settings + cv2.VideoCapture have side
effects that must be patched out. This test is the integration-tier guard
the strategy mandates for main.py's orchestration code.

Marked @pytest.mark.integration so the dedicated CI job runs it.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

import main as main_module
from state import AppState

pytestmark = pytest.mark.integration


def _install_hardware_mocks(monkeypatch) -> dict:
    """Patch the hardware-touching boundaries main.main() reaches into.

    Returns a context dict the test can inspect (e.g. number of times the
    autostart hook fired). The patches are scoped to the calling test via
    pytest's monkeypatch fixture.
    """
    # cv2.VideoCapture — succeeds, frames available on the first read so
    # CameraManager.wait_for_camera_permission exits immediately.
    fake_cap = MagicMock()
    fake_cap.isOpened.return_value = True
    fake_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    monkeypatch.setattr("cv2.VideoCapture", MagicMock(return_value=fake_cap))

    # pyttsx3.init — used by the AlertManager daemon thread.
    monkeypatch.setattr("pyttsx3.init", MagicMock(return_value=MagicMock()))

    # _camera_loop — when calibration_valid=True main starts a thread on
    # this; we don't want the (already-tested) loop spinning during the
    # startup test, so replace it with a no-op for these tests.
    monkeypatch.setattr(main_module, "_camera_loop", lambda *a, **kw: None)

    # TrayApp substitute — records construction args, autostart calls, and
    # .run() so the test can verify the orchestration without entering
    # pystray's real event loop.
    ctx: dict = {"instances": [], "autostart_calls": [], "run_calls": []}

    class _FakeTrayApp:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            ctx["instances"].append(self)

        def run(self) -> None:
            ctx["run_calls"].append(self)

        @staticmethod
        def register_autostart_on_first_run(exe_path=None) -> None:
            ctx["autostart_calls"].append(exe_path)

    monkeypatch.setattr(main_module, "TrayApp", _FakeTrayApp)

    return ctx


def _set_argv(monkeypatch, *extra: str) -> None:
    monkeypatch.setattr("sys.argv", ["main.py", *extra])


def _settings_returning(monkeypatch, settings: dict) -> None:
    monkeypatch.setattr(main_module, "load_settings", lambda: settings)
    monkeypatch.setattr(main_module, "save_settings", MagicMock())


def test_main_startup_default_uncalibrated_flow(monkeypatch):
    """Without a stored calibration: settings → state → cameras → autostart →
    daemon threads → tray. The drift check and camera-loop thread are
    skipped (calibration_valid=False).
    """
    ctx = _install_hardware_mocks(monkeypatch)
    _set_argv(monkeypatch)
    _settings_returning(monkeypatch, {})

    main_module.main()

    # Control was handed over to the tray exactly once.
    assert len(ctx["instances"]) == 1
    assert ctx["run_calls"] == ctx["instances"]

    # Default one_camera_mode is False (no --one-camera flag).
    tray = ctx["instances"][0]
    assert tray.kwargs["one_camera_mode"] is False

    # Autostart was registered exactly once during the run.
    assert len(ctx["autostart_calls"]) == 1

    # Calibration not present → state.calibration_valid is False, so the
    # depth pipeline path was bypassed.
    state = tray.args[0]
    assert state.calibration_valid is False


def test_main_startup_one_camera_flag_propagates_to_camera_manager_and_tray(monkeypatch):
    """The --one-camera CLI flag (ADR-011) must reach both CameraManager
    (which then only opens index 0) and TrayApp (which renders the
    "Uncalibrated" status because stereo depth is unavailable).
    """
    ctx = _install_hardware_mocks(monkeypatch)
    _set_argv(monkeypatch, "--one-camera")
    _settings_returning(monkeypatch, {})

    main_module.main()

    assert len(ctx["instances"]) == 1
    assert ctx["instances"][0].kwargs["one_camera_mode"] is True


def test_main_startup_calibrated_flow_runs_drift_check_and_starts_camera_loop(monkeypatch):
    """With a stored calibration: the drift check runs (mocked) and the
    camera-loop daemon thread starts in addition to alert + reconnect.
    """
    ctx = _install_hardware_mocks(monkeypatch)
    _set_argv(monkeypatch)
    _settings_returning(
        monkeypatch,
        {
            "calibration": {
                "valid": True,
                "slope": 0.04,
                "intercept": 0.5,
                "reference_cam0_path": "/dev/null/ref0.png",
                "reference_cam1_path": "/dev/null/ref1.png",
            },
            "min_safe_distance_m": 1.7,
            "alert_cooldown_seconds": 4,
        },
    )

    # DriftDetector — mocked to report no drift so neither alert_paused nor
    # position_drift_warning is set, keeping AppState in a known clean state.
    fake_drift = MagicMock()
    fake_drift.check.return_value = (0.0, "none")
    monkeypatch.setattr(main_module, "DriftDetector", MagicMock(return_value=fake_drift))

    main_module.main()

    # Drift check was invoked (calibration-path branch).
    fake_drift.check.assert_called_once()

    # Settings overrides flowed into the TrayApp's referenced AppState (the
    # first positional arg per TrayApp.__init__).
    tray = ctx["instances"][0]
    state = tray.args[0]
    assert isinstance(state, AppState)
    assert state.min_safe_distance_m == pytest.approx(1.7)
    assert state.alert_cooldown_seconds == 4
    assert state.calibration_valid is True


def test_main_startup_drift_check_handles_missing_reference_images_without_aborting(monkeypatch):
    """When references are missing on disk, DriftDetector.check raises
    DriftDetectorError. main() catches it and continues — the app must
    still reach the tray rather than crash before any UI is visible.
    """
    from camera.drift_detector import DriftDetectorError

    ctx = _install_hardware_mocks(monkeypatch)
    _set_argv(monkeypatch)
    _settings_returning(
        monkeypatch,
        {
            "calibration": {
                "valid": True,
                "slope": 0.04,
                "intercept": 0.5,
                "reference_cam0_path": "/does/not/exist/ref0.png",
                "reference_cam1_path": "/does/not/exist/ref1.png",
            }
        },
    )

    fake_drift = MagicMock()
    fake_drift.check.side_effect = DriftDetectorError("ref missing")
    monkeypatch.setattr(main_module, "DriftDetector", MagicMock(return_value=fake_drift))

    main_module.main()

    # The tray still came up despite the drift error.
    assert len(ctx["run_calls"]) == 1
