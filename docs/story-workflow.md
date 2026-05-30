# Per-Story Development Workflow

Every story follows this sequence. Do not skip steps — each one exists to catch a class of problem the previous step misses.

---

## Step 1 — Read the Story

Before writing any code:
- Read the story title, user narrative, and **all acceptance criteria**
- Check the dependency map (`docs/risk-assessment.md`) — are all blockers complete?
- If any AC is ambiguous, resolve it now (update the story doc) rather than interpreting it mid-implementation

---

## Step 2 — Write the Tests First (TDD)

Write the unit tests in `tests/unit/test_<module>.py` before writing the implementation.

- Each AC that is unit-testable gets at least one test
- Tests should fail at this point (that's expected — there's no implementation yet)
- Name tests descriptively: `test_depth_estimator_returns_none_when_no_right_detections`

Why first? Writing tests before code forces you to think about the interface (inputs/outputs) before the internals. It also guarantees tests actually test something rather than being written to pass existing code.

---

## Step 3 — Implement

Write the module code to make the tests pass.

Rules:
- Match the interface defined in the plan (`docs/epics-and-stories.md`) exactly — other stories depend on it
- No comments explaining what the code does; only comments for non-obvious *why*
- No error handling for impossible scenarios; validate only at real boundaries (user input, hardware calls)
- If you make a significant design decision not covered by the plan, write an ADR before continuing (`docs/decisions/`)

---

## Step 4 — Self-Review Checklist

Before asking for review or running CI, check each item yourself. The
commands here mirror what CI runs (`.github/workflows/ci.yml`); if
something passes locally and fails in CI, the locally-run command list
below is wrong — fix it.

- [ ] All AC from the story are satisfied
- [ ] `black --check .` passes (or run `black .` to fix)
- [ ] `ruff check .` passes
- [ ] `pytest tests/unit/ tests/integration/` passes — zero failures
- [ ] `pytest tests/performance/ -m performance` passes — perf budgets per **ADR-017**
- [ ] `coverage report --include="audio/*,camera/*,config/*,detection/*,state.py" --fail-under=90` passes — core-logic gate per **ADR-014**
- [ ] `coverage report --fail-under=55` passes — full-codebase visibility floor per **ADR-014** (ratchets up; never down)
- [ ] No hardcoded file paths (use `pathlib.Path`)
- [ ] No secrets, API keys, or personal data in code or test fixtures
- [ ] If a new significant decision was made: ADR written and added to `docs/decisions/README.md`
- [ ] If the story touches the threading model: verify no blocking calls are made while holding `app_state_lock`
- [ ] If the story changes the fail-safe contract (ADR-016) or sanity bounds: the property tests in `tests/unit/test_depth_estimator_properties.py` are updated *first* so the contract change is reflected in invariants, not just examples

---

## Step 5 — Code Review

Push the branch and open a PR. Reviewer checks:

- Does the implementation match the story's AC?
- Is the threading/locking correct (if applicable)?
- Are there edge cases the tests don't cover?
- Does the code match the module interface defined in the plan?
- Is any new ADR needed for decisions made during implementation?

The PR is not merged until all review comments are resolved and CI is green.

---

## Step 6 — Integration Check (mandatory; not "if they exist")

The integration tier is **enforced** by CI (the dedicated `integration`
job; see `.github/workflows/ci.yml`). Before the PR is opened, you must:

- [ ] Run `pytest tests/integration/ -m integration -v` locally with the
      story's branch checked out, and confirm it is green.
- [ ] **If this story touches a module boundary that has no existing
      integration test**, write one in `tests/integration/` *as part of
      this story* — not as a follow-up. A "module boundary" means two
      production modules that have not been wired together by a test
      before (e.g. camera manager + frame processor, main startup +
      tray callbacks).
- [ ] If this is a bug-fix story, the integration test must be the one
      that would have caught the bug. Land it red (one commit) and green
      (the next) on the same branch so reviewers can see the proof.

This step was conditional in v0.1.0 ("if they exist"). A P1 functional
defect (the shared `PersonDetector`, fixed in WS1 / ADR-015) shipped
through the gap that conditional language opened. Step 6 is mandatory now.

For the bug-test-first pattern specifically: see WS1's PR for the
canonical example (`tests/integration/test_camera_to_depth_pipeline.py`
landed failing in commit `(1/2)`, fixed in `(2/2)`).

---

## Step 7 — Acceptance Sign-Off

Go back to the story in `docs/epics-and-stories.md` and tick off each AC.  
A story is **Done** only when every AC checkbox is ticked and CI is green on `main`.

---

## Decision Documentation Rule

If during implementation you:
- Choose between two libraries or approaches
- Work around a known bug or platform quirk
- Deviate from the plan for a non-trivial reason
- Discover a constraint that wasn't in the plan

→ Write an ADR. It takes 10 minutes and saves hours of future confusion.
