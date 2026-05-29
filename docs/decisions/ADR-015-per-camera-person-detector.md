# ADR-015: One PersonDetector Instance Per Camera

**Date:** 2026-05-30
**Status:** Accepted
**Deciders:** QA Lead, VP R&D

---

## Context

`PersonDetector` (per ADR-004) processes every 3rd frame and returns a cached
result on the skipped frames (`person_detector.py:11-26`). The cache is held on
the instance: `self._last_result` and `self._frame_count`.

`main._camera_loop` and `StereoCalibrator.calibrate_diamond` both called
`detector.detect(left)` followed by `detector.detect(right)` on the **same**
`PersonDetector` instance. Because the frame-skip cache advances per-call (not
per-source), at most one of the two calls in any iteration actually ran HOG;
the other returned the previous call's cached detection. Concretely:

| Iteration | `detect(left)` (call N)         | `detect(right)` (call N+1)     |
|---|---|---|
| 1 | processes → returns LEFT detection | skipped → returns cached LEFT  |
| 2 | skipped → returns cached LEFT      | processes → returns RIGHT       |
| 3 | skipped → returns cached RIGHT     | skipped → returns cached RIGHT  |

Three iterations out of four produced identical left/right detections →
`disparity = cx_l - cx_r ≈ 0` → `distance = intercept` (a constant) regardless
of how close the person actually was. For a child-safety device the dangerous
failure direction is silent: the loop reports a fixed distance and either
fires constantly or never fires.

The unit suite did not catch this because (a) tests construct one fresh
`PersonDetector` per test (no cross-camera contamination) and (b) HOG is
mocked, so the frame-skip cache was never exercised against the production
wiring. The defect was found during the v0.1.0 QA review and is reproduced
by `tests/integration/test_camera_to_depth_pipeline.py`.

## Options Considered

### Option A: Make `PersonDetector` frame-skip keyed by frame identity
- **Pros:** Single instance keeps the API the same; cache becomes per-source.
- **Cons:** Requires the caller to supply a key (frame identity isn't intrinsic to a numpy array). Implicit coupling between detector and caller. Easy to misuse — a caller passing the same key for both cameras reintroduces the bug invisibly.

### Option B: Remove frame-skip from `PersonDetector`
- **Pros:** Simplest — bug structurally impossible.
- **Cons:** Removes the ~66% CPU saving documented in ADR-004; would need a different mechanism to control HOG cost. Larger surface change; risks regressing ADR-004's accepted performance trade-off.

### Option C: One `PersonDetector` instance per camera
- **Pros:** Bug structurally impossible — each cache is local to one stream. Preserves the frame-skip CPU saving from ADR-004 unchanged. Minimal code change: signature update + one extra constructor call per loop. Matches how `CameraManager` already models the cameras (separate left/right indices).
- **Cons:** Two HOG instances in memory instead of one (a few MB, negligible). Slightly more constructor cost at startup (one-off).

## Decision

**Chosen: Option C — one `PersonDetector` per camera.**

- `main._camera_loop` takes `detector_left: PersonDetector` and `detector_right: PersonDetector` (was a single `detector`).
- `main.main()` constructs two detectors and passes both to the loop thread.
- `StereoCalibrator.calibrate_diamond` instantiates `detector_left` and `detector_right` internally and uses each for its own camera.

## Consequences

- **Positive:**
  - The shared-cache class of bug is structurally impossible: each detector's cache is local to one camera stream.
  - Stereo disparity is now computed from independent detections; runtime distance and calibration curve are both correct.
  - ADR-004's frame-skip CPU saving is preserved (each detector still processes every 3rd frame on its own stream).
  - `tests/integration/test_camera_to_depth_pipeline.py` provides both a behavioural guard (correct distance from disparity 50) and a structural guard (`_camera_loop` signature requires two detector arguments). A future regression that collapses these back to one detector fails the test loudly.

- **Negative / Trade-offs:**
  - Two HOG descriptors instantiated at startup instead of one (negligible memory, one-off init cost).
  - The frame-skip behaviour is now de-synchronised between cameras (left and right may process different frame-counts of the same iteration). In practice both cameras see the same person at the same instant, so the depth estimate uses one fresh + one cached detection on most iterations — acceptable, since both detections still come from the *correct* camera. If sub-frame stereo alignment ever matters, revisit.

- **Follow-up required:**
  - WS2: extend the integration tier with a false-negative suite (occlusion, single-camera person visibility, outlier disparity) — those scenarios still produce silent `None`-distance failures (see `depth_estimator.py:22`).
  - WS3: bring `main.py` startup sequence into integration coverage to raise the WS0 full-codebase floor.
