<!--
TV Distance Monitor — PR template

The checklist below mirrors the self-review in docs/story-workflow.md § Step 4
and the Definition of Done in docs/testing-strategy.md § Acceptance Criteria
(ADR-019). Check every box before requesting review.
-->

## Summary

<!-- 1–3 bullets. What changed and why. Link the story / ADR. -->

## Test plan

<!-- The Step 4 self-review, run locally before pushing. -->

- [ ] `black --check .` clean
- [ ] `ruff check .` clean
- [ ] `pytest tests/unit/ tests/integration/` passes
- [ ] `pytest tests/performance/ -m performance` passes (ADR-017)
- [ ] Core-logic branch coverage ≥ 90 % (ADR-014)
- [ ] Full-codebase branch coverage ≥ 55 % (ADR-014, ratchet floor)
- [ ] CI green on this PR

## Workflow checks (workflow Step 6 / Definition of Done — ADR-019)

- [ ] If this PR touches a **new module boundary**, an integration test exists for it under `tests/integration/`.
- [ ] If this is a **bug-fix**, a regression test is in the branch — landed red first if practical (see WS1 for the canonical red→green example).
- [ ] If this PR changes the **fail-safe contract** (ADR-016) or sanity bounds, the Hypothesis property tests in `tests/unit/test_depth_estimator_properties.py` are updated *first*.
- [ ] **Significant design decisions** captured as ADRs under `docs/decisions/` and indexed in `docs/decisions/README.md`.
- [ ] Branch follows naming convention `feat/X.Y-short-title` (or `feat/qa-WSx-short-title` for QA workstreams).

## Hardware-only follow-ups

<!-- If this PR moves anything that can only be validated on real Windows hardware
     (camera capture, pyttsx3, autostart, the 80 ms / 5 s / 150 MB real budgets),
     list the items here so the next manual-checklist run covers them. -->

- [ ] N/A, or:

🤖 Generated with [Claude Code](https://claude.com/claude-code)
