# Changelog

All notable changes to TV Distance Monitor are documented here.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

*(Add changes here as stories are completed. Move to a versioned section at release time.)*

---

## [0.1.0] — 2026-05-28

### Added

- **Story 1.1** — Project skeleton: `requirements.txt`, venv, linting/formatting config (black, ruff), ADR-001
- **Story 1.2** — Settings module: `config/settings.py` with `load_settings()` / `save_settings()`, JSON storage, defaults, round-trip tests, ADR-002
- **Story 2.1** — Camera manager: `camera/camera_manager.py` with exponential-backoff open, `read_frames()`, `release()`, `AppState` integration
- **Story 2.2** — Degraded mode: disconnect detection, `alert_paused` flag, reconnect loop with configurable interval, ADR-003
- **Story 2.3** — Frame processor: `camera/frame_processor.py` resolution normalisation, no-copy fast path when resolutions match
- **Story 3.1** — HOG person detector: `detection/person_detector.py` with frame-skip cache (every 3rd frame), centroid calculation, ADR-004
- **Story 4.1** — Depth estimator: `detection/depth_estimator.py` centroid disparity with linear calibration fit, ADR-005
- **Story 5.1** — Stereo calibrator: `camera/stereo_calibration.py` diamond 4-point method, least-squares linear fit, ADR-006
- **Story 5.2** — Reference scene capture: `save_reference_scene()` saves PNG per camera, paths stored in settings
- **Story 6.1** — Drift detector: `camera/drift_detector.py` using `cv2.phaseCorrelate`, `|slope| × pixel_shift` formula, none/minor/significant thresholds at 5/20 cm, ADR-007
- **Story 7.1** — Alert manager: `audio/alert_manager.py` daemon-thread TTS loop, camera-offline 5-minute repeat, drift warning once-only, cooldown between distance alerts, ADR-008
- **Story 8.1** — App state threading: `AppState` dataclass extended with all fields, thread-safety enforced via `threading.Lock`
- **Story 8.2** — Tray icon: `tray/tray_app.py` pystray integration with 4 visual states (green/red/orange/grey), polling thread, Settings and Quit menu items
- **Story 8.3** — Settings window: `tray/settings_window.py` Tkinter UI with live dual-camera preview, calibration trigger with progress, distance slider, frame-interval slider, drift spinners, Test Alert, Save
- **Story 8.4** — Main entry point: `main.py` startup sequence (load settings → drift check → start daemon threads → run tray), version 0.1.0
- **Story 9.1** — PyInstaller packaging: `tvdm.spec` with hidden imports for pystray/pyttsx3/PIL; CI builds `--noconsole` exe on version tag push, ADR-009
- **Story 9.2** — Windows autostart: `tray/autostart.py` reads/writes `HKCU\…\Run` registry key; first-launch registration; tray "Toggle Autostart" menu item
- **Story 10.1** — ADRs 001–010 all written and indexed in `docs/decisions/README.md`
- **Story 10.2** — Manual test checklist: `docs/manual-test-checklist.md` covers install, first run, camera detection, calibration, alerting, settings, offline, drift, autostart, audio
- **Story 10.3** — CHANGELOG and release process: `CHANGELOG.md` (this file), `docs/release-process.md` with 8-step release procedure

---

<!-- Example release section — copy this template when releasing:

## [1.0.0] — YYYY-MM-DD
### Added
- ...
### Changed
- ...
### Fixed
- ...
### Removed
- ...

-->
