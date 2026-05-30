# ADR-019: Definition of Done — Per-Story PR + Integration-Test Mandate + Enforced Gates

**Date:** 2026-05-30
**Status:** Accepted
**Deciders:** QA Lead, VP R&D

---

## Context

The v0.1.0 QA review identified that the project's testing **strategy** was
sound while its **execution** drifted from that strategy. The breakdown
happened in two places:

1. **Process discipline.** Stories 1.2–5.2 were each one commit on a
   dedicated branch with TDD discipline. Then a single commit
   (`0c60087`) bundled five entire epics — drift, audio, tray,
   packaging, docs — with no per-story PR or per-story review. Step 6
   of `docs/story-workflow.md` ("Integration Check… if they exist")
   was treated as conditional and dropped under deadline pressure.
2. **Enforcement.** The 80% coverage gate was satisfied by omitting
   `tray/*` and `main.py` from coverage measurement — the gate was
   passing while the orchestration layer sat at 0%. CI ran only
   `tests/unit/`; integration and performance tiers existed in the
   strategy doc but had no enforcement.

WS0–WS5 closed both gaps technically (layered gates, integration
tier built, perf tier built, mutation testing introduced, fail-safe
contract added). This ADR is the consolidating policy: it states the
Definition of Done in one place, and it pins the workflow changes that
make the new ceiling load-bearing.

## Options Considered

### Option A: Leave the new gates and tier additions implicit; trust authors to follow them
- **Pros:** Lightest touch.
- **Cons:** Implicit standards drift. The v0.1.0 evidence shows this approach already failed once on this project.

### Option B: Add lint-style commit-message bots, branch protection, and require code-owners review
- **Pros:** Mechanical enforcement.
- **Cons:** Repo-administration changes that may need GitHub plan / org-level configuration; out of scope of a code-only PR. Worth doing as a follow-up; not the right primary intervention.

### Option C: Codify the Definition of Done in the workflow + strategy docs, add a PR template that surfaces the checklist at PR creation, and update CLAUDE.md so any agent or new contributor sees the same gates
- **Pros:** Same source of truth for humans, agents, and CI. The strategy's own decision-log rule mandates this for any test-strategy change. PR template is mechanical enough to not be forgotten.
- **Cons:** Still relies on reviewers checking the boxes. Without a server-side gate someone can technically merge a red PR.

## Decision

**Chosen: Option C, with Option B noted as a follow-up.**

This ADR consolidates the v0.2.0 Definition of Done. A story is **Done**
only when **all** of the following are true:

### Process
1. The work is on a **dedicated branch** named `feat/X.Y-short-title` (or `feat/qa-WSx-short-title` for QA workstreams). No commits to `main`.
2. The PR is opened against `main` (or the parent feature branch in a stacked PR) — even when working solo. The PR is the review gate and the CI trigger.
3. **At most one story per commit.** A story may span multiple commits (e.g. a red→green pair); a single commit may not touch more than one story's scope.

### Tests
4. `pytest tests/unit/ tests/integration/` passes with zero failures.
5. `pytest tests/performance/ -m performance` passes — CI perf budgets per **ADR-017**.
6. If the story touches a new module boundary, an integration test for that boundary exists under `tests/integration/` (workflow Step 6 — mandatory, not "if they exist").
7. If the story is a bug-fix, a regression test is added that *would have* caught the bug — landed red first when practical (see WS1 PR for the canonical example).
8. If the story changes the fail-safe contract or sanity bounds (**ADR-016**), the Hypothesis property tests in `tests/unit/test_depth_estimator_properties.py` are updated *first*, before the implementation change.

### Quality gates
9. `black --check .` and `ruff check .` pass with zero warnings.
10. **Core-logic gate (ADR-014):** branch coverage ≥ **90 %** across `audio/`, `camera/`, `config/`, `detection/`, `state.py`.
11. **Full-codebase floor (ADR-014):** branch coverage ≥ **55 %**, ratcheting up; never lowered without an ADR.
12. The dedicated `integration` CI job is green. The `performance` CI job is green (blocking; release tag requires it).

### Documentation
13. Significant design decisions are captured as ADRs under `docs/decisions/` and indexed in `docs/decisions/README.md`.
14. The acceptance criteria for the story are ticked off in `docs/epics-and-stories.md` before merge.

### Out-of-band
15. Mutation testing on `detection/` runs weekly via `.github/workflows/mutation.yml` (per **ADR-018**). Any new surviving mutant is triaged within two working weeks: classified as missing-test (add it), equivalent (document), or deferred-with-note.

## Consequences

- **Positive:**
  - One source of truth: this ADR is referenced from `docs/story-workflow.md`, `docs/testing-strategy.md`, `CLAUDE.md`, and the PR template. No room for "I read a different version".
  - The conditional "if they exist" in workflow Step 6 — the policy gap that let the WS1 P1 ship — is closed.
  - The PR template surfaces the Definition of Done at PR-creation time, before the reviewer is on the hook to catch omissions.
  - New contributors and agents see the same gates.

- **Negative / Trade-offs:**
  - Without GitHub branch-protection rules, a determined committer can still merge a red PR. Option B (server-side enforcement) is the natural follow-up; out of scope for a code-only ADR.
  - The PR template adds checkbox friction. For trivial PRs (typo fixes, doc tweaks) authors may leave items unchecked — reviewers should be lenient on those.
  - The Definition of Done is now long enough that no one will remember it all. That's why it lives in three places (workflow / strategy / PR template) that are each read at the moment they are needed.

- **Follow-up required:**
  - **Branch protection on `main`:** require linear history, require PRs, require the `test`, `integration`, and `performance` jobs to be green before merge. Repo-admin task; not in this PR's scope but should land soon.
  - **First-week audit:** the first three PRs after this lands should be checked against the template, with corrections fed back into the template if anything is unclear.
  - **Quarterly ADR review:** ADR-014's coverage thresholds and ADR-017's perf budgets should be ratcheted up as the codebase improves. This ADR does not pin specific dates — the next ADR-019-style update should set a schedule.
