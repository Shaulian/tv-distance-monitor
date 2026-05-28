# Epics & User Stories — TV Distance Monitor

## How to Read This Document

Each **Epic** is a major feature area. Each **Story** is a unit of work deliverable in a single development session. Stories include:
- **As a** [who] **I want** [what] **so that** [why]
- **Acceptance Criteria (AC)** — testable conditions that must all pass before the story is done
- **Notes** — implementation hints, constraints, or decisions to document as ADRs

Stories are ordered by dependency: earlier stories must be complete before later ones that depend on them.

---

## Epic 1: Project Foundation

> Set up the project skeleton, tooling, dependencies, and CI so every subsequent story starts from a clean, working baseline.

---

### Story 1.1 — Project Skeleton & Dependencies

**As a** developer  
**I want** a working Python project with all dependencies installed  
**So that** I can immediately run code and tests without setup friction

**AC:**
- [x] `requirements.txt` lists all dependencies with pinned versions: `opencv-python`, `numpy`, `pyttsx3`, `pystray`, `pytest`, `pytest-cov`, `black`, `ruff`
- [x] `venv` activates cleanly on both macOS and Windows
- [x] `python -c "import cv2, numpy, pyttsx3, pystray"` exits with no errors
- [x] `pytest --collect-only` runs with zero errors (even with no tests yet)
- [x] `black --check .` and `ruff check .` pass on the empty skeleton
- [x] `docs/decisions/ADR-001-language-and-tooling.md` exists, documenting Python 3.11, OpenCV, pyttsx3, pystray choices

**Notes:** Pin dependency versions at the time of install. Do not use `>=` without an upper bound for major packages.

---

### Story 1.2 — Settings Module

**As a** developer  
**I want** a settings module that loads and saves configuration from disk  
**So that** all other modules can read/write persistent state without reimplementing file I/O

**AC:**
- [x] `config/settings.py` implements `load_settings()` and `save_settings(data)`
- [x] Settings file path resolves to `%APPDATA%\TVDistanceMonitor\settings.json` on Windows and `~/.TVDistanceMonitor/settings.json` on macOS (via `pathlib.Path`)
- [x] Missing settings file returns default values without raising an exception
- [x] Unknown keys in the file are preserved (forward-compatibility: don't strip unrecognised keys)
- [x] Round-trip test: `save_settings(load_settings())` produces identical output
- [x] Unit tests in `tests/unit/test_settings.py` cover: defaults, missing file, partial file, round-trip, invalid JSON
- [x] `docs/decisions/ADR-002-settings-storage.md` documents the path choice and JSON format

---

## Epic 2: Camera Foundation

> Open, read, and manage the two USB cameras reliably, including graceful handling of missing or disconnecting cameras.

---

### Story 2.1 — Camera Manager: Open & Read

**As a** developer  
**I want** a camera manager that opens both USB cameras and returns frame pairs  
**So that** all other camera-dependent modules have a single, reliable source of frames

**AC:**
- [ ] `camera/camera_manager.py` implements `CameraManager` with `open_cameras()`, `read_frames()`, `release()`
- [ ] `open_cameras()` retries with exponential backoff (500ms, 1s, 2s…) for up to 10 seconds
- [ ] Returns `(True, 2)`, `(True, 1)`, or `(False, 0)` correctly for both-open, one-open, none-open cases
- [ ] `read_frames()` returns `(None, frame)` or `(frame, None)` when one camera drops mid-run
- [ ] `/check-cameras` skill passes
- [ ] Unit tests mock `cv2.VideoCapture` and verify backoff timing and return values
- [ ] `AppState.num_cameras_online` is updated correctly after `open_cameras()`

---

### Story 2.2 — Camera Manager: Degraded Mode & Recovery

**As a** caregiver  
**I want** the app to detect when a camera disconnects and attempt to reconnect automatically  
**So that** the app self-heals without requiring manual restart

**AC:**
- [ ] When a live camera drops mid-run, `AppState.num_cameras_online` decrements within one frame cycle
- [ ] `AppState.alert_paused` is set to `True` immediately on disconnect
- [ ] A background retry loop attempts reconnection every 5 seconds (configurable)
- [ ] On reconnection, `alert_paused` is cleared and normal monitoring resumes
- [ ] An audio notification fires every 5 minutes while camera is offline (reuses `AlertManager`)
- [ ] Unit test: simulate a camera dropping (mock `read_frames()` returning None) and verify state transitions
- [ ] `docs/decisions/ADR-003-degraded-mode-behavior.md` documents why alerting is paused (not guessed) when one camera is offline

---

### Story 2.3 — Frame Processor: Resolution Normalisation

**As a** developer  
**I want** the frame processor to normalise two frames to the same resolution before processing  
**So that** stereo matching works correctly even when cameras have different native resolutions

**AC:**
- [ ] `camera/frame_processor.py` implements `FrameProcessor.process(left, right)`
- [ ] Both frames are resized to `min(height_left, height_right)` × `min(width_left, width_right)` using `cv2.INTER_AREA`
- [ ] If both frames are the same resolution, no resize occurs (performance: avoid unnecessary copy)
- [ ] Unit tests: same-res pair passes through unchanged; different-res pair is downsampled to smaller; output shapes match
- [ ] No display/preview logic in this module (single responsibility)

---

## Epic 3: Person Detection

> Detect people in camera frames and provide bounding boxes and centroids for depth estimation.

---

### Story 3.1 — HOG Person Detector

**As a** developer  
**I want** a person detector that returns bounding boxes and centroids from a frame  
**So that** the depth estimator has per-person positions to work with

**AC:**
- [ ] `detection/person_detector.py` implements `PersonDetector.detect(frame)` returning list of `(x, y, w, h, cx, cy)`
- [ ] Uses OpenCV's built-in HOG + default people detector (no external model file required)
- [ ] Processes every 3rd frame; returns last result for skipped frames (reduces CPU ~66%)
- [ ] Returns empty list (not None) when no person detected
- [ ] Unit test with a fixture frame containing a person: detector returns ≥ 1 result
- [ ] Unit test with a blank/empty fixture frame: detector returns `[]`
- [ ] `/test` skill passes
- [ ] `docs/decisions/ADR-004-person-detection-approach.md` documents choice of HOG vs. ML models (MediaPipe, YOLO) and why HOG was chosen (offline, no model file, good enough for close-range)

---

## Epic 4: Stereo Depth Estimation

> Compute distance from the TV using disparity between the two cameras.

---

### Story 4.1 — Depth Estimator: Person Matching & Distance

**As a** developer  
**I want** a depth estimator that matches persons across two camera frames and returns distance  
**So that** the app can determine whether someone is too close to the TV

**AC:**
- [ ] `detection/depth_estimator.py` implements `DepthEstimator(calibration_dict)` and `estimate_distance(detections_left, detections_right)`
- [ ] Person matching heuristic: same person if bounding box vertical centres are within 20px
- [ ] Disparity = `cx_left - cx_right` (horizontal centroid difference)
- [ ] Distance = `intercept + slope * disparity` using calibration curve
- [ ] Returns `None` if no matching pair found
- [ ] Unit tests: known disparity → verify distance within 5%; no right detections → returns `None`; multiple persons → returns closest (smallest distance)
- [ ] `docs/decisions/ADR-005-depth-estimation-method.md` documents the disparity approach and why structured-light / ToF sensors were out of scope

---

## Epic 5: Calibration

> Allow the user to calibrate the stereo rig once, storing the disparity-to-distance curve.

---

### Story 5.1 — Stereo Calibrator: Diamond Method

**As a** caregiver  
**I want** to calibrate the cameras by standing at 4 points around the TV  
**So that** the app can accurately measure how far I (or a child) am from the screen

**AC:**
- [ ] `camera/stereo_calibration.py` implements `StereoCalibrator.calibrate_diamond(camera_manager, ui_callback)`
- [ ] Captures 5 frames at each of the 4 diamond points and averages centroids
- [ ] Fits a linear least-squares curve: `distance_m = intercept + slope * disparity`
- [ ] `ui_callback` is called after each point with `(point_index, total_points)` so the UI can show progress
- [ ] Calibration result stored in settings with `calibration.valid = True`
- [ ] Unit test: 4 synthetic (disparity, distance) pairs → verify slope and intercept within 1% of expected values
- [ ] Unit test: fewer than 2 valid detections raises `CalibrationError`
- [ ] `docs/decisions/ADR-006-calibration-method.md` documents the diamond method, why 4 points, and the linear fit assumption

---

### Story 5.2 — Reference Scene Capture

**As a** developer  
**I want** a reference scene (one empty-room frame per camera) saved at calibration time  
**So that** startup drift detection has a baseline to compare against

**AC:**
- [ ] After diamond calibration, `StereoCalibrator.save_reference_scene(camera_manager, dest_dir)` saves `reference_cam0.png` and `reference_cam1.png`
- [ ] Settings stores paths as `calibration.reference_cam0_path` and `reference_cam1_path`
- [ ] If files already exist, they are overwritten (recalibration refreshes the reference)
- [ ] Unit test: method saves two PNG files to `tmp_path`; paths are stored in returned calibration dict

---

## Epic 6: Drift Detection

> Detect at startup whether cameras have physically moved since calibration.

---

### Story 6.1 — Drift Detector: Pixel Shift to Severity

**As a** developer  
**I want** a startup check that measures camera movement and classifies it as none/minor/significant  
**So that** the app can warn the user or pause alerting if cameras are no longer in their calibrated positions

**AC:**
- [ ] `camera/drift_detector.py` implements `DriftDetector(reference_paths, calibration_dict)`
- [ ] `check(camera_manager)` returns `(drift_cm: float, severity: str)` where severity ∈ `{'none', 'minor', 'significant'}`
- [ ] Uses `cv2.phaseCorrelate` on grayscale frames to get `(dx, dy)` per camera
- [ ] `drift_cm = |slope| * hypot(dx, dy)`; takes max across both cameras
- [ ] Thresholds: `< 5 cm` = `'none'`; `5–20 cm` = `'minor'`; `> 20 cm` = `'significant'`
- [ ] Unit tests: shift reference image 0px → `'none'`; shift 30px (simulate minor) → `'minor'` or `'significant'` depending on slope; reference image path missing → raises `DriftDetectorError`
- [ ] `docs/decisions/ADR-007-drift-detection-thresholds.md` documents the 5 cm / 20 cm thresholds, the phaseCorrelate choice, and why a physical marker was not required

---

## Epic 7: Audio Alerts

> Play TTS announcements when a child is too close, when a camera is offline, or when drift is detected.

---

### Story 7.1 — Alert Manager

**As a** caregiver  
**I want** the app to announce a voice alert when my child is too close to the TV  
**So that** I am notified even when not watching the screen

**AC:**
- [ ] `audio/alert_manager.py` implements `AlertManager.run(app_state_lock, app_state)` as a blocking loop suitable for a daemon thread
- [ ] Announces `alert_message` while `person_too_close` is True; waits 3 seconds between announcements (`alert_cooldown_seconds`)
- [ ] Sleeps (no CPU) when `person_too_close` is False
- [ ] When `alert_paused` is True: speaks "Camera offline — check the connection" (or "Recalibration required") every 5 minutes; does not speak distance alerts
- [ ] When `position_drift_warning` is True: speaks the drift warning exactly once, then clears the flag
- [ ] Unit tests (mocking pyttsx3): verify `say()` called on transition to `person_too_close = True`; not called when `alert_paused = True`; drift warning spoken exactly once
- [ ] `docs/decisions/ADR-008-tts-library.md` documents choice of pyttsx3 over cloud TTS

---

## Epic 8: Tray Application

> Integrate all components into a Windows system tray app with settings UI.

---

### Story 8.1 — App State & Threading Model

**As a** developer  
**I want** a shared `AppState` dataclass protected by a lock  
**So that** the camera thread and alert thread can communicate safely without race conditions

**AC:**
- [ ] `main.py` (or `state.py`) defines `AppState` with all fields from the plan
- [ ] All reads and writes use `with app_state_lock:`
- [ ] Unit test: two threads writing and reading simultaneously do not produce inconsistent state (simple concurrency smoke test)

---

### Story 8.2 — Tray Icon & Menu

**As a** user  
**I want** a system tray icon that shows the current app status  
**So that** I can see at a glance whether monitoring is active, degraded, or needs attention

**AC:**
- [ ] `tray/tray_app.py` implements `TrayApp` using pystray
- [ ] Tray icon has 4 visual states: OK (green), Too Close (red), Degraded/Offline (orange), Uncalibrated (grey)
- [ ] Right-click menu shows: Status (read-only), Settings, Quit
- [ ] Icon state updates on every `AppState` change (polling or event-driven)
- [ ] Manual test on macOS: tray icon appears and menu is clickable
- [ ] Manual test on Windows: same; icon visible in system tray area

---

### Story 8.3 — Settings Window

**As a** caregiver  
**I want** a settings window where I can calibrate the cameras and adjust the minimum safe distance  
**So that** I can configure the app for my specific TV and room layout

**AC:**
- [ ] `tray/settings_window.py` implements `SettingsWindow` using Tkinter
- [ ] Shows live dual-camera preview (side-by-side, 640×480 each)
- [ ] Shows calibration status banner (red "NOT CALIBRATED" or green "Calibrated")
- [ ] "Calibrate" / "Recalibrate" button triggers `StereoCalibrator.calibrate_diamond()` with a progress indicator
- [ ] Distance slider: 0.5–3.0 m, default 1.5 m, updates `AppState.min_safe_distance_m` on change
- [ ] Frame Capture Interval slider: 50–500 ms, updates `AppState.frame_capture_interval_ms` live
- [ ] Drift threshold spinners: minor (default 5 cm), significant (default 20 cm)
- [ ] "Test Alert" button plays TTS once without affecting alert state
- [ ] "Save" persists all settings to disk
- [ ] Manual test: window opens, sliders respond, preview shows live frames

---

### Story 8.4 — Main Entry Point & Startup Sequence

**As a** user  
**I want** the app to start automatically at login and reach a ready state within 15 seconds  
**So that** monitoring is always active when the TV is in use

**AC:**
- [ ] `main.py` follows the startup sequence from the plan: load settings → check calibration → open cameras (with backoff) → drift check → start threads → run tray
- [ ] On first run (no calibration): tray shows grey, notification fires, cameras open for preview only
- [ ] On subsequent runs (calibrated): drift check runs; result sets `alert_paused` or `position_drift_warning` accordingly
- [ ] App reaches monitoring state within 15 seconds of launch on a normal Windows boot
- [ ] Manual test: run `python main.py` on macOS; tray icon appears; settings window opens

---

## Epic 9: Packaging & Release

> Package the app as a Windows `.exe` and set up autostart.

---

### Story 9.1 — PyInstaller Packaging

**As a** maintainer  
**I want** a single `.exe` that bundles the app and all its dependencies  
**So that** installation on Windows requires no Python knowledge

**AC:**
- [ ] `pyinstaller --onefile main.py` produces a working `.exe`
- [ ] All assets (icons, any data files) are included in the bundle
- [ ] `.exe` runs on a clean Windows machine (no Python installed)
- [ ] `docs/decisions/ADR-009-packaging.md` documents PyInstaller choice vs. cx_Freeze

---

### Story 9.2 — Windows Autostart

**As a** user  
**I want** the app to start automatically when Windows boots  
**So that** I don't have to remember to launch it manually

**AC:**
- [ ] App registers itself in `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` on first launch (or via installer)
- [ ] Can be disabled from the tray menu ("Disable Autostart")
- [ ] Manual test: reboot Windows → app appears in tray without manual launch

---

## Epic 10: Documentation & Quality

> Ensure the codebase is documented, decisions are recorded, and the project is maintainable.

---

### Story 10.1 — ADR Completion

**As a** future maintainer  
**I want** a record of every significant technical decision  
**So that** I understand why the code is the way it is without digging through git history

**AC:**
- [ ] All ADRs listed in stories 1.1–9.1 are written and merged (`docs/decisions/ADR-00N-*.md`)
- [ ] Each ADR contains: Context, Options Considered, Decision, Consequences
- [ ] `docs/decisions/README.md` lists all ADRs with a one-line summary

---

### Story 10.2 — Manual Test Checklist

**As a** maintainer  
**I want** a step-by-step Windows manual test checklist  
**So that** I can verify the app works end-to-end before every release

**AC:**
- [ ] `docs/manual-test-checklist.md` exists with a checkbox list covering all manual scenarios from the testing strategy
- [ ] Checklist is version-stamped (each release gets a dated run of the checklist)

---

### Story 10.3 — CHANGELOG & Release Process

**As a** maintainer  
**I want** a CHANGELOG and a documented release process  
**So that** users know what changed and I have a repeatable shipping procedure

**AC:**
- [ ] `CHANGELOG.md` exists following Keep a Changelog format
- [ ] `docs/release-process.md` documents: version bump, CHANGELOG update, PyInstaller build, Windows test, tag and distribute
