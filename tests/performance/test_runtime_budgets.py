"""Performance regression guards (CI-runnable).

These tests do **not** validate the absolute hardware budgets in
`docs/testing-strategy.md` (frame loop ≤ 80 ms, full startup ≤ 5 s, < 150 MB
after 30 minutes) — those depend on real cameras and Windows hardware and
remain on `docs/manual-test-checklist.md`. CI runs on a headless Linux
runner with HOG and TTS mocked.

What CI **does** assert (per ADR-017):

  - `_camera_loop` orchestration overhead per iteration stays under a tight
    bound. Catches O(n²) regressions, accidental sleeps, lock contention,
    or expensive operations added to the hot path.
  - `_camera_loop` allocates only short-lived objects: monotonic memory
    growth per iteration is bounded.
  - `main.main()` startup, with all I/O mocked, completes in well under a
    second. Catches stray sleeps, network calls, or expensive imports
    added to the startup path.

Marked `@pytest.mark.performance` so the dedicated CI job runs it.
"""

from __future__ import annotations

import gc
import sys
import threading
import time
import tracemalloc
from unittest.mock import MagicMock

import numpy as np
import pytest

import main as main_module
from camera.frame_processor import FrameProcessor
from detection.depth_estimator import DepthEstimator
from detection.person_detector import PersonDetector
from main import _camera_loop
from state import AppState

pytestmark = pytest.mark.performance


_CALIBRATION = {"slope": 0.04, "intercept": 0.5, "valid": True}


# ─── hand-rolled fakes (no MagicMock — its call_args_list grows monotonically
#     and would itself look like a memory leak in tracemalloc snapshots) ────


class _NullHog:
    """A HOG stand-in that always reports "no person detected". Used to keep
    the perf test deterministic and avoid the cost (and CPU variance) of
    real HOG inference on a CI runner."""

    _EMPTY = np.empty((0, 4), dtype=np.int32)

    def detectMultiScale(self, *args, **kwargs):
        return (self._EMPTY, None)


class _BoundedCameraManager:
    """Returns the same stereo frame pair for `iterations` calls, then sets
    the loop's stop event and yields (None, None) so `_camera_loop` exits
    at the next while-check. Avoids MagicMock to keep the memory test
    accurate."""

    def __init__(self, frames: tuple, iterations: int, stop: threading.Event):
        self._frames = frames
        self._remaining = iterations
        self._stop = stop

    def read_frames(self):
        if self._remaining > 0:
            self._remaining -= 1
            return self._frames
        self._stop.set()
        return (None, None)

    def detect_and_handle_drop(self, frames, app_state, lock):
        # No-op: not relevant to perf measurement.
        pass


def _make_state() -> tuple[AppState, threading.Lock]:
    state = AppState()
    state.num_cameras_online = 2
    state.alert_paused = False
    state.min_safe_distance_m = 1.5
    state.frame_capture_interval_ms = 0  # eliminate sleep contribution
    return state, threading.Lock()


def _make_detector() -> PersonDetector:
    detector = PersonDetector()
    detector._hog = _NullHog()
    return detector


def _make_pipeline():
    state, lock = _make_state()
    return {
        "state": state,
        "lock": lock,
        "frame_processor": FrameProcessor(),
        "detector_left": _make_detector(),
        "detector_right": _make_detector(),
        "depth_estimator": DepthEstimator(_CALIBRATION),
        "frame_pair": (
            np.zeros((480, 640, 3), dtype=np.uint8),
            np.zeros((480, 640, 3), dtype=np.uint8),
        ),
    }


def _run_loop(pipeline: dict, iterations: int) -> None:
    stop = threading.Event()
    cam = _BoundedCameraManager(pipeline["frame_pair"], iterations, stop)
    _camera_loop(
        cam,
        pipeline["frame_processor"],
        pipeline["detector_left"],
        pipeline["detector_right"],
        pipeline["depth_estimator"],
        pipeline["state"],
        pipeline["lock"],
        stop,
    )


# ─── budgets (CI guards, not hardware budgets — see ADR-017) ──────────────

# Per-iteration orchestration cost in milliseconds. Real production includes
# HOG (~30–50 ms/iter on hardware) and is bounded at 80 ms total per the
# strategy doc; CI mocks HOG so this measures pipeline glue only. 5 ms / iter
# is roughly 50× the observed value on the dev machine — generous noise
# margin yet catches O(n²) or accidental-sleep regressions.
_PER_ITERATION_BUDGET_MS = 5.0

# Bytes the loop may retain per iteration before we call it a leak.
# 1 KB / iter at the default 100 ms interval = ~36 MB/hour of growth, which
# would breach the 150 MB strategy budget within a working day.
_MEMORY_BUDGET_BYTES_PER_ITER = 1000

# Mocked startup. Real cold start (camera enumeration + drift check) is
# budgeted at 5 s by the strategy doc; CI mocks all I/O so this should
# complete in well under a second. 1 s is a comfortable regression cap.
_STARTUP_BUDGET_S = 1.0


# ─── tests ────────────────────────────────────────────────────────────────


def test_camera_loop_iteration_overhead_within_budget():
    """Drives `_camera_loop` for 2000 iterations on a headless pipeline and
    asserts the average orchestration time per iteration stays under the
    CI budget. Regression target: someone introducing an O(n²) loop, a
    stray `time.sleep`, or excessive lock contention in `_camera_loop`."""

    iterations = 2000
    pipeline = _make_pipeline()

    # Warm-up — first iterations pay one-off costs (module init, numpy
    # buffer setup) that would skew the timing measurement.
    _run_loop(pipeline, 100)

    start = time.perf_counter()
    _run_loop(pipeline, iterations)
    elapsed_ms = (time.perf_counter() - start) * 1000

    per_iter_ms = elapsed_ms / iterations
    assert per_iter_ms < _PER_ITERATION_BUDGET_MS, (
        f"_camera_loop overhead {per_iter_ms:.3f} ms/iter > "
        f"{_PER_ITERATION_BUDGET_MS} ms CI budget. The hardware budget "
        "(80 ms incl. HOG, per strategy doc) is far tighter; a CI-budget "
        "breach here means real hardware will miss frames."
    )


def test_camera_loop_does_not_leak_memory():
    """Snapshots Python heap before and after 2000 `_camera_loop` iterations
    and asserts the per-iteration growth stays under the byte budget.
    Catches algorithmic leaks (lists/dicts that grow over time, retained
    object references) which would silently breach the 150 MB ceiling at
    runtime."""

    iterations = 2000
    pipeline = _make_pipeline()

    # Warm-up so one-off allocations (numpy buffers, lazy imports) are
    # outside the measurement window.
    _run_loop(pipeline, 100)
    gc.collect()

    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()

    _run_loop(pipeline, iterations)

    gc.collect()
    snap_after = tracemalloc.take_snapshot()
    total_diff = sum(s.size_diff for s in snap_after.compare_to(snap_before, "lineno"))
    tracemalloc.stop()

    bytes_per_iter = total_diff / iterations
    # Negative deltas are fine (GC ran, net release); only positive growth
    # is the failure direction.
    assert bytes_per_iter < _MEMORY_BUDGET_BYTES_PER_ITER, (
        f"_camera_loop retains {bytes_per_iter:.1f} bytes/iter > "
        f"{_MEMORY_BUDGET_BYTES_PER_ITER} byte CI budget. At a 100 ms "
        f"interval this is ~{bytes_per_iter * 36000 / (1024**2):.1f} MB/hour "
        "of monotonic growth and would breach the 150 MB strategy budget."
    )


def test_main_startup_completes_within_budget(monkeypatch):
    """Times `main.main()` through to TrayApp.run() with all hardware
    boundaries mocked. The hardware budget is 5 s on a real cold start;
    CI is microseconds — 1 s is a comfortable regression cap that catches
    stray sleeps, network calls, or expensive imports added to startup."""

    fake_cap = MagicMock()
    fake_cap.isOpened.return_value = True
    fake_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
    monkeypatch.setattr("cv2.VideoCapture", MagicMock(return_value=fake_cap))
    monkeypatch.setattr("pyttsx3.init", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(main_module, "_camera_loop", lambda *a, **kw: None)
    monkeypatch.setattr(main_module, "load_settings", lambda: {})
    monkeypatch.setattr(main_module, "save_settings", MagicMock())
    monkeypatch.setattr(sys, "argv", ["main.py"])

    class _FakeTrayApp:
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            pass

        @staticmethod
        def register_autostart_on_first_run(exe_path=None):
            pass

    monkeypatch.setattr(main_module, "TrayApp", _FakeTrayApp)

    start = time.perf_counter()
    main_module.main()
    elapsed_s = time.perf_counter() - start

    assert elapsed_s < _STARTUP_BUDGET_S, (
        f"main.main() took {elapsed_s:.3f}s > {_STARTUP_BUDGET_S}s CI budget. "
        "Real cold-start budget (5 s) includes camera enumeration + drift "
        "check; CI is fully mocked so this guards against accidental "
        "sleeps or expensive work added to startup."
    )
