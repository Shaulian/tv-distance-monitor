# Testing Strategy — TV Distance Monitor

## Philosophy

- Tests exist to verify *behavior*, not implementation. If the behavior is correct, the test passes regardless of how the code is written internally.
- Tests are documentation: a failing test should tell you exactly what broke and why.
- Every bug found in production means a missing test. Add it before fixing the bug.
- Never mock the core logic. Mock only at system boundaries (camera hardware, audio hardware, file I/O).

---

## Test Types

### 1. Unit Tests (primary)

**Tool:** pytest  
**Location:** `tests/unit/`  
**Run on:** every commit (CI)  
**Coverage target:** ≥ 80% line coverage on all non-UI modules

What belongs here:
- Image processing functions (`FrameProcessor`, `DepthEstimator`)
- Calibration math (`StereoCalibrator` — disparity-to-distance curve fitting)
- Drift detection logic (`DriftDetector` — pixel shift → cm → severity bucket)
- Alert state logic (`AlertManager` — cooldown, pause flag, drift-warning-once)
- Settings load/save (`config/settings.py` — round-trip, defaults, missing keys)
- Person matching heuristic (`DepthEstimator.estimate_distance` — matching persons across frames)

What does NOT belong here:
- Anything that opens a real camera
- Anything that calls pyttsx3
- Tkinter UI logic (test manually)

**Mocking rules:**
- `cv2.VideoCapture` → use pre-captured frames stored as `.npz` or `.png` in `tests/fixtures/`
- `pyttsx3.Engine.say()` → mock with `unittest.mock.MagicMock`
- File paths → use `tmp_path` (pytest fixture) for settings and reference images

---

### 2. Integration Tests

**Tool:** pytest (separate markers)  
**Location:** `tests/integration/`  
**Run on:** manually, and optionally on CI (requires cameras or fixtures)  
**Marker:** `@pytest.mark.integration`

What belongs here:
- Camera manager + frame processor + person detector — end-to-end depth estimate on a pre-recorded stereo frame pair
- Settings load → AppState initialization → drift detector (full startup simulation with fixture frames)
- Alert manager responding to AppState transitions (person_too_close flipping True → False → True)

These tests use real module interactions but still mock hardware via fixtures.

---

### 3. Performance Tests

**Tool:** pytest + `time` measurements  
**Location:** `tests/performance/`  
**Run on:** manually before release  
**Marker:** `@pytest.mark.performance`

Targets:
- Frame processing loop must complete in ≤ 80 ms at default settings (100 ms interval → leaves 20 ms headroom)
- Full startup sequence (load settings + open cameras + drift check) ≤ 5 seconds on a cold start
- Memory usage of camera loop must stay below 150 MB after 30 minutes of continuous operation

---

### 4. Manual Tests (Windows-Specific)

**Location:** `docs/manual-test-checklist.md`  
**Run on:** before every release, on real Windows hardware or VM

See `docs/manual-test-checklist.md` for the full checklist. Key areas:
- USB camera detection on Windows
- pystray tray icon render and menu interactions
- pyttsx3 voice availability and audio output
- Autostart on login (registry / Startup folder)
- Camera unplug/replug mid-run
- Drift scenarios: nudge one camera, restart, verify warning

---

## Test File Naming Convention

```
tests/
├── unit/
│   ├── test_depth_estimator.py
│   ├── test_drift_detector.py
│   ├── test_stereo_calibration.py
│   ├── test_alert_manager.py
│   ├── test_settings.py
│   └── test_person_detector.py
├── integration/
│   ├── test_camera_to_depth_pipeline.py
│   └── test_startup_sequence.py
├── performance/
│   └── test_frame_loop_timing.py
└── fixtures/
    ├── stereo_pair_near.npz        # person at ~0.8m (too close)
    ├── stereo_pair_far.npz         # person at ~2.0m (safe)
    ├── reference_cam0.png          # empty-room reference frame
    ├── reference_cam1.png
    └── reference_cam0_shifted.png  # reference_cam0 shifted 30px (for drift tests)
```

---

## Acceptance Criteria for Tests

A story is not done until:
1. All unit tests pass (`pytest tests/unit/`)
2. Relevant integration tests pass (`pytest tests/integration/ -m integration`)
3. `black` and `ruff` pass with zero warnings
4. Test coverage on the modified module is ≥ 80% (check with `pytest --cov`)
5. A new test was added that would have *caught* the bug this story fixes (if it's a bug fix story)

---

## Decision Log

Any change to the testing strategy (e.g., adding a test type, changing coverage targets, introducing a new mock boundary) must be documented in `docs/decisions/` as an ADR before taking effect.

---

## Running Tests

```bash
# All unit tests
pytest tests/unit/

# With coverage report
pytest tests/unit/ --cov=. --cov-report=term-missing

# Integration tests (requires fixture frames)
pytest tests/integration/ -m integration

# Skip slow tests
pytest tests/unit/ -m "not slow"

# Single file
pytest tests/unit/test_depth_estimator.py -v
```
