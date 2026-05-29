# ADR-014: Layered Coverage Gates (Core High-Bar + Full-Codebase Floor)

**Date:** 2026-05-29
**Status:** Accepted
**Deciders:** QA Lead, VP R&D

---

## Context

The v0.1.0 quality gate (`--cov-fail-under=80`) was applied to the whole codebase but `[tool.coverage.run] omit` excluded `tray/*` and `main.py` from measurement. As a result:

- Headline coverage read ~99%, while honest line coverage on shipped product code was ≈47% and honest branch coverage ≈48%.
- A P1 functional defect (shared `PersonDetector` between cameras → disparity collapses to 0) shipped because the orchestration in `main.py` (where the bug lives) was at 0% coverage and excluded from the gate.
- Line coverage masked uncovered conditional branches in the algorithm modules.

The testing strategy's own rule (`docs/testing-strategy.md` § Decision Log) requires any change to test policy to be recorded as an ADR before taking effect.

## Options Considered

### Option A: Single global gate at a low honest number (e.g. 45%)
- **Pros:** Simple; honest; ratchets up over time.
- **Cons:** A single number averages strong (95% core) and weak (0% UI) layers — algorithm-module regressions can be masked by UI improvements. The number that matters most (logic) becomes invisible.

### Option B: Single global gate at a high number (e.g. 80%) with no omit
- **Pros:** Looks strict.
- **Cons:** Currently impossible — full-codebase coverage is ≈48%. Would block all PRs immediately. Reinstating an `omit` to make it pass reproduces today's masking. Rejected.

### Option C: Layered gates — high bar on core logic, ratcheting floor on full codebase
- **Pros:** Each layer enforced separately. Core regressions caught immediately; UI/orchestration coverage cannot silently rot. True coverage stays visible in every CI run. Aligns the gate with where risk actually lives.
- **Cons:** Slightly more CI plumbing (two `coverage report` invocations against shared data).

## Decision

**Chosen: Option C — layered gates.**

- **Core-logic gate (blocking, primary quality bar):** branch coverage ≥ **90%** across `audio/`, `camera/`, `config/`, `detection/`, `state.py`. Today's measurement is 95%; the 90% floor absorbs noise. Ratchet upward as it climbs.
- **Full-codebase floor (blocking, ratcheting):** branch coverage ≥ **45%** across all product code (`main.py` and `tray/*` included, no `omit`). Today's measurement is 48%. This number can only be raised over time; it can never be lowered without an ADR.
- The `omit` of `tray/*` / `main.py` is removed from `[tool.coverage.run]`. Coverage uses `branch = true`. The only `omit` retained is `tests/*`, `venv/*`, `tvdm.spec`, and `__pycache__`.
- Markers `integration`, `performance`, `slow` are registered in `[tool.pytest.ini_options]`. CI gains dedicated `integration` and `performance` job stages.

## Consequences

- **Positive:**
  - Headline coverage now reflects shipped product code, not a curated subset.
  - Algorithm regressions cannot be hidden by UI improvements (and vice versa).
  - The integration tier specified in `docs/testing-strategy.md` becomes CI-enforced (tolerates "no tests yet" via exit code 5 until WS1 lands the first integration test).
  - Branch coverage replaces line coverage — uncovered `else`/`elif` paths now count as misses.

- **Negative / Trade-offs:**
  - PRs that touch core packages must keep branch coverage ≥ 90% on those packages; this is stricter than the prior 80% gate but is the deliberate raised bar.
  - The full-codebase floor (45%) is intentionally low at the start and looks unimpressive — it is the *honest* number and the right starting point for a ratchet.

- **Follow-up required:**
  - **WS1:** Land `tests/integration/test_camera_to_depth_pipeline.py`, exposing and fixing the shared-detector bug; raise the full-codebase floor as `main.py` enters coverage.
  - **WS3:** Bring `main.py` startup sequence into integration coverage; raise the floor again.
  - **WS4:** Implement performance tier; remove `continue-on-error` from the performance CI job.
  - **WS6:** Update `docs/story-workflow.md` Step 4 self-review checklist to reference the new gates; update `docs/testing-strategy.md` with the layered model. Until then, the workflow doc still cites the legacy `--cov-fail-under=80` command and should be read together with this ADR.
