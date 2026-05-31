---
name: qa-deep-dive
description: Audit test quality and coverage by reading the actual code + git history, not just running coverage. Surfaces gamed metrics, missing tiers, and behavior bugs that pass a 100%-coverage suite.
---

## Usage

Run with `/qa-deep-dive` when the user asks for any of:
- A QA review, test-quality audit, coverage review, or "are our tests good"
- An assessment of whether the testing strategy is being followed
- A second opinion on whether a release is ready

This skill exists because the v0.1.0 QA review found a P1 functional defect
that was invisible to a 99% coverage number but obvious from reading
`main.py`. Metrics-only reviews miss bugs that live in untested
orchestration glue. **Always read the code.**

## What it does (the discipline)

Six steps, in order. Skipping any one defeats the point of the skill.

### 1. Read the testing strategy doc

- `docs/testing-strategy.md` (or equivalent). Note the tiers it names and the
  thresholds it promises.
- `docs/story-workflow.md` (or equivalent). Note what the per-story workflow
  claims is mandatory vs optional.
- `docs/decisions/` ADRs. Note any test-strategy decisions and their stated consequences.

Output of this step: a one-paragraph summary of what the strategy *says*
the test suite looks like.

### 2. Measure the **honest** coverage baseline

The trap is to trust whatever number the CI gate reports. Look for:

- `[tool.coverage.run] omit = [...]` — anything omitted is a place a metric
  can be gamed. Run coverage **without** the omit to see the real number.
- `--cov-fail-under=N` — what's N, and is the gate scoped to all product code
  or just the easy part?
- The CI workflow file: does the coverage step actually include all the
  source it should?

Commands (adjust paths for the project):
```bash
pytest tests/unit/ tests/integration/ --cov --cov-report=term-missing \
  --cov-config=/dev/null \
  --cov=audio --cov=camera --cov=config --cov=detection --cov=tray --cov=main --cov=state
```

Compare the honest number against the headline number. The delta is a finding.

### 3. Inventory the test suite by tier

```bash
pytest tests/ --collect-only -q | tail -1   # total
pytest tests/unit/ --collect-only -q | tail -1
pytest tests/integration/ --collect-only -q | tail -1
pytest tests/performance/ --collect-only -q | tail -1
```

Check:
- Are `tests/integration/` and `tests/performance/` empty or stubs?
- Are markers (`@pytest.mark.integration`, `performance`, `slow`) registered
  in `pyproject.toml`? If not, the strategy doc's marker-based filtering is
  broken.
- Are there CI stages for each tier, and are they blocking?

### 4. Read the source whose tests look thin

For every module under the lowest coverage:
- Open the source. Look for branch-y logic, threading, frame-skip caches,
  or state machines.
- Open its test. Is the dependency mocked in a way that bypasses the
  interesting branches? (E.g., `_make_detector_with_mock_hog` that uses
  `__new__` to skip `__init__` — the bug-shaped escape hatch from WS1.)
- Cross-check: does any test actually exercise the production wiring?
  The WS1 P1 defect was that `main._camera_loop` was constructed with
  one shared `PersonDetector` for both cameras; the unit tests used
  fresh instances per test and never saw the cache cross-contamination.

If you find the test suite uses unrealistic mocks and the wiring is
uncovered, **that** is the defect class. Write a paragraph describing
the specific shipping bug shape that this gap would let through, with
file:line references.

### 5. Cross-check ADRs against the code

For each accepted ADR, verify the code matches the stated decision. The
gaps between an ADR and the code are honest findings:
- "ADR-012 says X but `main.py:135` does Y" — drift.
- "ADR-016's fail-safe contract requires `assess_proximity` to never
  return `(False, 'no_person')` when detections exist — does the code do
  that?" — invariant check.

### 6. Inventory git history for per-story discipline

```bash
git log --oneline | head -40
git log --diff-filter=A --name-only --pretty=format:"%n## %s" -- \
  tests/integration/ tests/performance/ tests/fixtures/ | head -30
```

Patterns to flag:
- One commit spanning multiple stories ("Stories 6.1–10.3: …") — process
  drift, integration tests likely skipped under deadline pressure.
- `tests/integration/__init__.py` added but no tests landed alongside it
  — the tier was scaffolded and then abandoned.
- A coverage `omit` introduced in the same commit as the CI gate — the
  gate was probably gamed from day one.

## Output

A report sorted by severity, **S0 → S3**, with:
- File:line references for every claim
- A one-paragraph "process root cause" section (what did the team and the
  standards each contribute to the gaps?)
- A prioritized remediation plan: smallest blocker first, then the rest

For VP-level audiences, lead with a "Bottom line" paragraph (one short
paragraph) that gives the headline finding in plain English. The rest is
backup.

## When NOT to use

- The user asks for a code review of a single PR or diff — use `code-review`
  or `review` instead.
- The user wants to write new tests for a specific bug they're already
  aware of — use the existing workflow, not this audit skill.
- The user wants to validate a feature is working end-to-end — use
  `verify` or `run`.

## Prerequisites

- pytest + pytest-cov installed.
- A working `pytest --collect-only` run (the project's test discovery is sane).
- `coverage` CLI available (comes with pytest-cov).
- `git log` history is intact (no shallow clone).

## Why this is a skill and not just an agent prompt

The discipline of "read the actual source before quoting numbers" is
easy to forget under deadline pressure or scope creep. Having it as a
named, opinionated skill makes it harder to skip step 4. The slowest
step is also the step that finds the bugs.
