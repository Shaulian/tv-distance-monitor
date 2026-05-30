# ADR-017: CI-Enforced Performance Budgets (Regression Guards, Not Hardware Limits)

**Date:** 2026-05-30
**Status:** Accepted
**Deciders:** QA Lead, VP R&D

---

## Context

`docs/testing-strategy.md` (§ Performance Tests) names three budgets:

| Budget | Value | Scope |
|---|---|---|
| Frame processing loop | ≤ 80 ms | per iteration on real hardware |
| Full startup sequence | ≤ 5 s | cold start, real cameras, drift check |
| Memory usage | < 150 MB | after 30 minutes of continuous operation |

Through v0.1.0 these were neither asserted nor enforced anywhere — no
`tests/performance/` files, no CI step that fails on a breach. The QA
review flagged this as part of the broader "the strategy describes tiers
the suite doesn't implement" gap.

A direct CI translation is not feasible:

- **The frame loop budget** is dominated by HOG inference (~30–50 ms on
  real-world frames). A headless Linux runner has no real frames; HOG
  must be mocked, and the mocked time is microseconds.
- **The startup budget** includes USB camera enumeration and a drift check
  that reads PNG files — both side-effected by environment. CI mocks the
  whole I/O surface, again landing in microseconds.
- **The 150 MB memory ceiling after 30 minutes** would require a 30-minute
  CI test (untenable) and depends on the working set of pyttsx3, pystray
  and the Python interpreter on Windows specifically — not Linux.

## Options Considered

### Option A: Skip CI performance enforcement; rely on manual checklist
- **Pros:** Honest — CI cannot measure what the strategy describes.
- **Cons:** A regression that doubles the frame loop time on hardware would only be caught at manual-checklist time, by which point it has shipped. Misses the easy wins (algorithmic complexity, accidental sleeps, memory leaks).

### Option B: Run real performance tests on Windows CI with real cameras
- **Pros:** Closest to the strategy's intent.
- **Cons:** Windows runners are slower and expensive; no real cameras attached; the build-windows-exe job already runs only on version tags. Wrong tier for per-PR regression catching.

### Option C: CI-enforced *regression guards* that test what is testable; absolute hardware budgets stay on the manual checklist
- **Pros:** Catches the failure modes CI can actually see — algorithmic complexity (O(n²) added to the hot path), stray sleeps, lock contention, memory leaks, expensive imports added to startup. Cheap (< 1 s total), deterministic, no real hardware required.
- **Cons:** A CI pass does not guarantee the hardware budget will be met. Reviewers must read this ADR to understand what each tier covers.

## Decision

**Chosen: Option C — CI regression guards in `tests/performance/`; the
hardware budgets remain on `docs/manual-test-checklist.md`.**

Three tests under `tests/performance/test_runtime_budgets.py`,
all marked `@pytest.mark.performance`:

| Test | CI budget | What a breach signals |
|---|---|---|
| `test_camera_loop_iteration_overhead_within_budget` | **5 ms / iter** (orchestration only; HOG mocked) | O(n²) or accidental sleep added to the hot path. Real-hardware iteration is ~50–80 ms; a CI breach guarantees a hardware breach. |
| `test_camera_loop_does_not_leak_memory` | **1000 bytes / iter** retained (tracemalloc delta) | An object reference held over loop iterations. At 100 ms intervals, 1 KB / iter = ~36 MB / hour — would breach the 150 MB strategy budget within a working day. |
| `test_main_startup_completes_within_budget` | **1 s** for `main.main()` end-to-end with all I/O mocked | Stray `time.sleep`, network call, or expensive import added to startup. Real cold start (5 s) covers the things this test cannot. |

All three use hand-rolled fakes (not `MagicMock`) inside the timed/measured
regions: `MagicMock.call_args_list` grows monotonically and would itself
register as a memory leak under tracemalloc.

CI integration:

- The `performance` job runs on every push and PR.
- `continue-on-error: true` is removed — the job is now blocking.
- `build-windows-exe` (release job, tag-triggered) `needs: [test, integration, performance]` — a perf budget breach blocks a release.

## Consequences

- **Positive:**
  - The performance tier described in `docs/testing-strategy.md` is now CI-enforced for the first time.
  - The class of regressions CI can catch — algorithmic, allocation, accidental-sleep — fails fast, on the PR that introduces them, before reaching a release.
  - Release tags can no longer be cut while perf budgets are red.

- **Negative / Trade-offs:**
  - Reviewers must read this ADR to understand the gap between the CI budget (5 ms / iter) and the strategy budget (80 ms / iter). The CI number is **lower** than the strategy number, which looks confusing without context: CI measures orchestration only, hardware includes HOG.
  - Test budgets are set with ~50× headroom above measured baselines to absorb CI noise. A tighter budget would catch smaller regressions but flake more often. The chosen numbers are a deliberate trade-off.
  - The 30-minute memory soak is not run in CI. A slow leak below the per-iteration threshold could still accumulate over hours and would only surface on the manual checklist.

- **Follow-up required:**
  - When budgets become flaky on CI, raise them by 2× (not lower) and add a comment citing the run that triggered the change.
  - WS5 (mutation testing) will exercise additional code paths; verify perf budgets do not regress under that stress.
  - The manual checklist (`docs/manual-test-checklist.md`) should explicitly cross-reference this ADR so the manual tester knows the CI budgets are not a substitute.
