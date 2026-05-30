# Testing Strategy — TV Distance Monitor

> Living document. Strategy changes are recorded as ADRs (see § Decision Log).
> v0.1.0 → v0.2.0 hardening: ADR-014 (layered coverage), ADR-016 (fail-safe
> contract), ADR-017 (CI perf budgets), ADR-018 (mutation + property), ADR-019
> (Definition of Done).

## Philosophy

- Tests exist to verify *behavior*, not implementation. If the behavior is correct, the test passes regardless of how the code is written internally.
- Tests are documentation: a failing test should tell you exactly what broke and why.
- Every bug found in production means a missing test. Add it before fixing the bug.
- Never mock the core logic. Mock only at system boundaries (camera hardware, audio hardware, file I/O).
- **Coverage is necessary but not sufficient.** Mutation testing (ADR-018) and property tests (Hypothesis) are how we verify the tests would actually catch a behavior change, not just that they ran the line.
- **Fail loud, not silent (ADR-016).** For this safety-critical product, ambiguity must trigger an alert, never suppress one. Every code path through `DepthEstimator.assess_proximity` returns a defined verdict.

---

## Test Types

### 1. Unit Tests (primary)

**Tool:** pytest (+ Hypothesis for property tests)
**Location:** `tests/unit/`
**Run on:** every commit (CI `test` job)
**Coverage targets (ADR-014):**
- **Core-logic gate (blocking):** branch coverage ≥ **90%** across `audio/`, `camera/`, `config/`, `detection/`, `state.py`.
- **Full-codebase floor (blocking, ratcheting):** branch coverage ≥ **55%** across all product code, including `main.py` and `tray/*`. Ratchets upward over time; never lowered without an ADR.

What belongs here:
- Image processing functions (`FrameProcessor`, `DepthEstimator`)
- Calibration math (`StereoCalibrator` — disparity-to-distance curve fitting)
- Drift detection logic (`DriftDetector` — pixel shift → cm → severity bucket)
- Alert state logic (`AlertManager` — cooldown, pause flag, drift-warning-once)
- Settings load/save (`config/settings.py` — round-trip, defaults, missing keys)
- Person matching heuristic (`DepthEstimator.estimate_distance` — matching persons across frames)
- **Property tests (Hypothesis)** for the depth contract — `tests/unit/test_depth_estimator_properties.py`; see ADR-018.

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

**Tool:** pytest
**Location:** `tests/integration/`
**Run on:** every PR (CI `integration` job — blocking)
**Marker:** `@pytest.mark.integration`

What belongs here:
- Camera manager + frame processor + person detector — end-to-end depth estimate on a stereo frame pair (`test_camera_to_depth_pipeline.py`).
- `main.main()` startup orchestration with mocked hardware (`test_main_startup_sequence.py`).
- Alert manager responding to AppState transitions.

These tests use real module interactions but still mock hardware boundaries. **Adding an integration test at every new module boundary is mandatory per `docs/story-workflow.md` Step 6** — not optional.

---

### 3. Performance Tests (ADR-017)

**Tool:** pytest + `time.perf_counter()` / `tracemalloc`
**Location:** `tests/performance/`
**Run on:** every PR (CI `performance` job — blocking; release blocker via `build-windows-exe.needs`)
**Marker:** `@pytest.mark.performance`

CI budgets (regression guards — not hardware budgets; see ADR-017):
- `_camera_loop` per-iteration orchestration ≤ **5 ms** (HOG mocked).
- `_camera_loop` memory growth ≤ **1000 bytes/iter** (tracemalloc).
- `main.main()` startup ≤ **1 s** (all I/O mocked).

Real-hardware budgets (manual checklist; ADR-017 explains why CI cannot enforce them):
- Frame processing loop ≤ 80 ms at default settings (real HOG, 100 ms interval).
- Full startup sequence ≤ 5 s on a cold start (real cameras, real drift check).
- Memory usage of camera loop < 150 MB after 30 minutes of continuous operation.

---

### 4. Mutation + Property Testing (ADR-018)

**Tools:** `mutmut==2.5.1` (mutation), Hypothesis (property tests in unit tier)
**Mutation scope:** `detection/` only (smallest, highest-stakes pure-logic package)
**Run on:**
- Property tests: every PR (alongside the unit suite — they live in `tests/unit/`).
- Mutation testing: **weekly** schedule + on-demand `workflow_dispatch` (`.github/workflows/mutation.yml`). Not blocking; track + triage.

Current baseline: **84% mutation score (59/70 killed)** on `detection/`. New survivors triaged within two weeks (classified as missing-test, equivalent, or deferred-with-note).

---

### 5. Manual Tests (Windows-Specific)

**Location:** `docs/manual-test-checklist.md`
**Run on:** before every release, on real Windows hardware or VM

See `docs/manual-test-checklist.md` for the full checklist. Key areas:
- USB camera detection on Windows
- pystray tray icon render and menu interactions
- pyttsx3 voice availability and audio output
- Autostart on login (registry / Startup folder)
- Camera unplug/replug mid-run
- Drift scenarios: nudge one camera, restart, verify warning
- The real-hardware perf budgets from § 3 (CI cannot measure them; see ADR-017)

---

## Test File Naming Convention

```
tests/
├── unit/
│   ├── test_depth_estimator.py
│   ├── test_depth_estimator_properties.py   # Hypothesis — ADR-018
│   ├── test_drift_detector.py
│   ├── test_stereo_calibration.py
│   ├── test_alert_manager.py
│   ├── test_settings.py
│   ├── test_person_detector.py
│   ├── test_camera_manager{,_degraded,_one_camera}.py
│   ├── test_camera_permission_guard.py
│   ├── test_app_state_threading.py
│   ├── test_frame_processor.py
│   ├── test_tray_icon.py
│   └── test_tray_settings_dispatch.py
├── integration/
│   ├── test_camera_to_depth_pipeline.py     # depth pipeline + fail-safe — ADR-015/016
│   └── test_main_startup_sequence.py        # main() orchestration — WS3
├── performance/
│   └── test_runtime_budgets.py              # ADR-017
└── fixtures/
    └── (real-image fixtures: add when needed; currently synthetic)
```

---

## Acceptance Criteria for Tests (Definition of Done — ADR-019)

A story is not done until:
1. `pytest tests/unit/ tests/integration/` passes with zero failures.
2. `pytest tests/performance/ -m performance` passes — CI perf budgets per ADR-017.
3. `black --check .` and `ruff check .` pass with zero warnings.
4. **Core-logic gate** (ADR-014): `coverage report --include="audio/*,camera/*,config/*,detection/*,state.py" --fail-under=90` passes.
5. **Full-codebase floor** (ADR-014): `coverage report --fail-under=55` passes.
6. If the story touches a new module boundary, an integration test for that boundary exists (workflow Step 6).
7. If the story is a bug-fix, a new test was added that *would have caught* the bug — landed on the branch before the fix.
8. If the story changes the depth/fail-safe contract or sanity bounds, the corresponding property tests (`test_depth_estimator_properties.py`) are updated *first*.
9. If significant decisions were made, ADRs written and added to `docs/decisions/README.md`.
10. Story branch follows the naming convention `feat/X.Y-short-title` (or `feat/qa-WSx-short-title` for QA workstreams).
11. PR opened against `main` (or the parent feature branch in a stacked PR); CI green before merge.

---

## Decision Log

Any change to the testing strategy (e.g., adding a test type, changing coverage targets, introducing a new mock boundary) must be documented in `docs/decisions/` as an ADR before taking effect.

---

## Running Tests

```bash
# Unit + integration (what CI runs in the `test` and `integration` jobs)
pytest tests/unit/ tests/integration/

# Performance budgets (ADR-017)
pytest tests/performance/ -m performance

# Coverage gates (ADR-014) — run after the above unit + integration pass
pytest tests/unit/ tests/integration/ --cov --cov-report=term-missing
coverage report --include="audio/*,camera/*,config/*,detection/*,state.py" --fail-under=90
coverage report --fail-under=55

# Mutation testing on detection/ (ADR-018) — slow; not per-PR
mutmut run
mutmut results

# Single file
pytest tests/unit/test_depth_estimator.py -v
```
