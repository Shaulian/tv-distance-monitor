# ADR-016: Fail-Safe Degradation Policy ("Degrade Loud, Not Silent")

**Date:** 2026-05-30
**Status:** Accepted
**Deciders:** QA Lead, VP R&D

---

## Context

The TV Distance Monitor is a child-safety device. The dangerous failure
direction is **silence**: a child is too close to the TV, but no alert fires.
The opposite failure (an alert when the child is actually safe) is *annoying*,
but the user can dismiss it; silence is unrecoverable in real time.

Several inputs reach `DepthEstimator.estimate_distance` where stereo distance
cannot be computed:

| Scenario | Today's behaviour | Outcome |
|---|---|---|
| Both cameras see a person, vertical centres > 20 px apart (motion, crouching, angle) | `estimate_distance` returns `None` | `person_too_close = False` → silent |
| Left camera detects a person, right camera misses (occlusion, glare, momentary tracking loss) | `estimate_distance` returns `None` | silent |
| Right-only detection | same | silent |
| Linear fit extrapolates to negative distance (disparity wrong-signed, e.g. matched against a reflection) | `distance < 0`, then `distance < min_safe` → `True` | accidentally loud |
| Linear fit extrapolates to absurd distance (e.g. 50 m) | `distance > min_safe` → `False` | silent |

The first three are real-world conditions that occur every session. The
WS2 integration test (committed first as the failing red proof) demonstrates
the left-only-detection case. The QA review classifies all silent paths
as a single class-of-defect.

## Options Considered

### Option A: Leave `estimate_distance` as-is; require callers to handle `None`
- **Pros:** Smallest change. No API addition.
- **Cons:** Every caller (main loop, calibration, future settings preview) has to know and re-implement the fail-safe policy. Easy to forget. Today's `main._camera_loop` already gets it wrong silently.

### Option B: Add per-state fields (`distance_uncertain`, `distance_out_of_range`) and a separate "uncertain" TTS alert
- **Pros:** Most expressive — the user hears *why* the system is alerting (occlusion vs too-close).
- **Cons:** Larger surface change: AppState, AlertManager, settings UI all touched. New TTS phrasing requires localisation thought. Adds three states (too-close, uncertain, out-of-range) where today there is one.

### Option C: Centralise the policy in `DepthEstimator.assess_proximity` returning `(person_too_close, reason)`; default to `True` whenever distance cannot be trusted
- **Pros:** One place owns the safety contract — the depth estimator, which already knows the geometry. Callers stay simple (`person_too_close = assess_proximity(...)[0]`). Reason is exposed for future telemetry/UI without forcing a state-model change today. Sanity bounds become first-class.
- **Cons:** More verbose than Option A. Today the `reason` is unused in production; will look unused in coverage reports until a follow-up surfaces it.

## Decision

**Chosen: Option C — `DepthEstimator.assess_proximity` with a fail-safe default.**

Implementation:

- New method `DepthEstimator.assess_proximity(detections_left, detections_right, min_safe_distance_m) -> tuple[bool, str]`.
- Return reasons: `"no_person"`, `"ok"`, `"unmatched"`, `"out_of_range"`.
- Fail-safe defaults: `unmatched` and `out_of_range` both return `person_too_close = True`.
- Sanity bounds: `0 < distance ≤ 10.0 m`. A distance ≤ 0 (negative or exactly zero — physically impossible for a person watching a TV) or > 10 m (calibration was for ≤ ~2 m; extrapolation past 10 m is not credible) is treated as `out_of_range`.
- `main._camera_loop` is wired through `assess_proximity` instead of comparing the raw `estimate_distance` return.
- `estimate_distance` is unchanged — backward compatible with existing tests and any external callers.

## Consequences

- **Positive:**
  - The silent-failure class of defect is structurally impossible from `main._camera_loop`'s perspective: every code path through `assess_proximity` returns a defined `person_too_close` boolean.
  - The dangerous direction is now the loud one. False-positive rate may increase in degraded conditions (one camera occluded mid-session); this is a deliberate trade-off in favour of child safety.
  - `tests/integration/test_camera_to_depth_pipeline.py::test_left_only_detection_triggers_fail_safe_person_too_close` is the regression guard — a future change reintroducing silent failure (e.g. someone reverting the wiring to `estimate_distance` directly) fails the integration job.
  - The `reason` return value is available for WS3 (tray status) and downstream telemetry without further API change.

- **Negative / Trade-offs:**
  - Brief degraded conditions (one camera obstructed for a second, then resumes) will trigger an audible alert that the user must wait out. AlertManager's 3-second cooldown limits the cost; AlertManager is not changed by this ADR.
  - The 10 m sanity ceiling is a heuristic chosen from the calibration range. If a future installation requires longer-range monitoring (atypical for the use case), the constant must move.
  - The `reason` string is currently unused in production code; consumed only by tests. Discarding it in `main._camera_loop` is intentional (no AppState change in this story).

- **Follow-up required:**
  - **WS3** (`main.main()` startup integration): when bringing main into integration coverage, consider exposing `reason` on `AppState` for the tray status icon.
  - **WS4** (performance tier): assess_proximity adds a constant-time check; no perf budget impact expected, but confirm with the frame-loop timing test.
  - Future ADR if the `out_of_range` ceiling needs revisiting for longer-range deployments.
