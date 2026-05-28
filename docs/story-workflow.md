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

Before asking for review or running CI, check each item yourself:

- [ ] All AC from the story are satisfied
- [ ] `pytest tests/unit/` passes with zero failures
- [ ] `black --check .` passes (or run `black .` to fix)
- [ ] `ruff check .` passes
- [ ] `pytest tests/unit/ --cov --cov-fail-under=80` passes for the modified module
- [ ] No hardcoded file paths (use `pathlib.Path`)
- [ ] No secrets, API keys, or personal data in code or test fixtures
- [ ] If a new significant decision was made: ADR written and added to `docs/decisions/README.md`
- [ ] If the story touches the threading model: verify no blocking calls are made while holding `app_state_lock`

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

## Step 6 — Integration Check

After merge, run the relevant integration test(s) if they exist:

```bash
pytest tests/integration/ -m integration -v
```

If this story is the first to touch a module boundary (e.g., camera manager + frame processor working together for the first time), write an integration test now even if it wasn't required by the story.

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
