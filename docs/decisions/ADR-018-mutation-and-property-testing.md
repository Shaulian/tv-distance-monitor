# ADR-018: Mutation Testing + Property Testing as Test-Quality Tools

**Date:** 2026-05-30
**Status:** Accepted
**Deciders:** QA Lead, VP R&D

---

## Context

WS0–WS4 raised coverage from ~47 % to ~57 % and built integration +
performance tiers. Coverage answers "did a test run this line?" — it does
not answer "would a test catch a meaningful change in this line's
behaviour?" The QA review explicitly cited this gap: the original
v0.1.0 unit suite had 99 % line coverage *and* shipped a P1 functional
defect (shared-detector in WS1). Coverage was satisfied; semantic
correctness was not.

Two techniques target this gap directly:

- **Mutation testing** systematically rewrites the source (`<` → `<=`,
  `+` → `-`, constants nudged, etc.) and re-runs the test suite. A
  mutation that no test catches is a "surviving mutant" — concrete
  evidence of a missing test.
- **Property-based testing** (Hypothesis) generates many random inputs
  and asserts invariants instead of specific outputs. It pressures the
  code from angles a hand-written example doesn't think of.

We need a policy for how both are introduced, run, and acted on.

## Options Considered

### Option A: Per-PR mutation testing as a blocking gate
- **Pros:** Survivors are caught at the PR that creates them; no drift over time.
- **Cons:** Mutmut on `detection/` (70 mutants) takes ~90 s today; once expanded to `camera/` it would be many minutes per PR. Most mutations are repeated test-suite runs — they would dominate CI time. The PR-level signal is also noisy: an *equivalent* mutation (a mutation whose behaviour is observationally identical) cannot be fixed by adding a test, only by being marked accepted, which adds policy churn to every PR.

### Option B: No CI for mutation testing; run manually before releases
- **Pros:** Honest about cost; nothing to maintain.
- **Cons:** Easily forgotten. Survivor count would drift up over time and never be reviewed. Wastes the tool.

### Option C: Per-PR mutation testing as advisory (non-blocking) with weekly summary
- **Pros:** PR author sees signal in real time.
- **Cons:** Doubles every PR's CI time for a signal most authors will ignore; "advisory" comments tend to be tuned out.

### Option D: Out-of-band CI (weekly schedule + `workflow_dispatch`); per-PR runs done locally if the author touches a mutated module
- **Pros:** Weekly cadence forces a regular triage moment without slowing every PR. `workflow_dispatch` lets a reviewer demand a run on a specific PR if it touches risky logic. Local `mutmut run` is one command for authors who want to check before pushing. The kill-rate trend is tracked over time.
- **Cons:** A surviving mutant introduced today might not be flagged until next Monday's run. For non-blocking signal this is acceptable.

### Property tests — single option
- **Hypothesis** added to `requirements.txt`, property tests live alongside example-based tests under `tests/unit/`. Run on every PR (same job, same cost as the rest of the unit suite). Default profile is fine; no shrinking config required at this scope.

## Decision

**Chosen: Option D + Hypothesis property tests on every PR.**

Concretely:

- **Mutation testing scope:** `detection/` — the smallest, highest-stakes pure-logic package (stereo depth + the ADR-016 fail-safe contract + the HOG cache that caused the WS1 P1). `camera/` and `audio/` are explicitly out of scope for v1 of this policy; revisit when their pure-logic surface grows.
- **Mutation tool:** `mutmut==2.5.1`. mutmut 3.x's `mutants/` workspace pattern conflicts with our package layout (it doesn't copy non-mutated source modules into the workspace, so the test suite fails to import sibling packages). mutmut 2.x runs in place and works.
- **Configuration:** `[tool.mutmut]` in `pyproject.toml` pins paths, tests dir, and the runner command. The runner targets only the tests that exercise `detection/` (depth_estimator + person_detector + the property tests) to keep each mutant run fast.
- **CI:** `.github/workflows/mutation.yml` runs on `schedule: 0 6 * * 1` (Mondays 06:00 UTC) and on `workflow_dispatch`. The workflow uploads an HTML survivor report as an artifact (retention 30 days). It does **not** fail the job on survivors — the policy is track + triage, not block.
- **Triage cadence:** new survivors are reviewed within one working week. Each survivor is classified as (a) missing test → add it, (b) equivalent mutation → document in this ADR's annex (future, not now), or (c) deferred with a tracking note. No survivor stays unclassified for more than two weeks.

**Property tests** added under `tests/unit/test_depth_estimator_properties.py` covering:
- `estimate_distance` formula correctness (single matched pair → exact linear fit).
- `estimate_distance` empty-list returns None on either side.
- `assess_proximity` "no_person" only when both inputs empty.
- `assess_proximity` never silent when at least one camera sees a person — the ADR-016 invariant.
- `assess_proximity` left-only and right-only always (True, "unmatched").
- `assess_proximity` "ok" verdict is consistent with `estimate_distance` + min_safe comparison.
- `assess_proximity` fail-safe reasons (`"unmatched"`/`"out_of_range"`) always report `too_close=True`.

These properties kill many mutants on their own (the WS5 baseline of 56/70 already includes them) and are the primary defence against silent contract violations.

## Baseline established by this PR

| Metric | Value |
|---|---|
| Mutants generated on `detection/` | 70 |
| Killed | 59 |
| Survivors | 11 |
| **Mutation score** | **84 %** |
| New unit + property tests added | 12 (9 Hypothesis + 3 triage) |

The 11 surviving mutants break down as:
- 1 type-annotation change (`float | None` → `float & None`) — runtime no-op, equivalent.
- 1 strict-vs-loose comparison for tie-breaking among equal-distance matches — both produce the same `best` value, equivalent.
- 1 `_last_result` initial value (`[]` → `None`) that is overwritten before any observable use, equivalent.
- 1 internal counter mutation (`+= 1` → `= 1` on the process branch) that cycles to the same modulo pattern, observationally equivalent.
- 5 HOG hyperparameters (winStride, padding, scale) — different inference behaviour, but the test suite mocks HOG; would only be caught by real-image regression tests (manual on hardware).
- 2 integer-division/float-division mutations followed by `int()` — produce identical results for non-negative inputs.

Treated as the baseline; this PR's CI report is the reference for future regression.

## Consequences

- **Positive:**
  - Test-quality is measurable, with a number to defend and grow.
  - The ADR-016 fail-safe contract is property-tested against the full input space, not just hand-picked examples.
  - The weekly cadence forces a recurring triage moment; survivors cannot quietly accumulate for months.
  - Adds two well-understood industry techniques to the project's standard toolkit — strengthens the QA review's "raised bar" theme.

- **Negative / Trade-offs:**
  - Survivor triage is a recurring cost (small but non-zero). The "two-week classification" rule keeps it honest.
  - Mutmut pinned to 2.x means we won't pick up future 3.x improvements automatically. Worth revisiting if the upstream rewrite stabilises and gains workspace-aware behaviour for multi-package projects.
  - The 5 HOG-hyperparameter survivors will keep showing up forever unless someone writes an image-based regression test. That work is on the manual checklist, not here.

- **Follow-up required:**
  - When `camera/` grows new pure-logic (e.g. drift heuristics beyond `phaseCorrelate`), extend the mutmut scope.
  - First Monday after merge: confirm the scheduled workflow ran and the HTML artifact uploaded.
  - When introducing future ADRs that change the fail-safe contract or sanity bounds, ensure the property tests are updated *first* so the contract change is reflected in invariants, not just examples.
