# Architecture Decision Records

This directory documents every significant technical decision made in this project.

Use `docs/decisions/ADR-000-template.md` when writing a new ADR.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](ADR-001-language-and-tooling.md) | Language, Runtime & Core Tooling (Python 3.11, OpenCV, pyttsx3, pystray) | Accepted |
| [ADR-002](ADR-002-settings-storage.md) | Settings Storage Format & Location (JSON, APPDATA) | Accepted |
| [ADR-003](ADR-003-degraded-mode-behavior.md) | Behavior When One Camera Goes Offline (pause alerting, notify every 5 min) | Accepted |
| [ADR-004](ADR-004-person-detection-approach.md) | Person Detection Approach (OpenCV HOG vs. MediaPipe vs. YOLO) | Accepted |
| [ADR-005](ADR-005-depth-estimation-method.md) | Depth Estimation Method (centroid disparity + linear fit) | Accepted |
| [ADR-006](ADR-006-calibration-method.md) | Calibration Method (diamond 4-point, linear least-squares) | Accepted |
| [ADR-007](ADR-007-drift-detection-thresholds.md) | Camera Drift Detection — Method & Thresholds (phaseCorrelate, 5/20 cm) | Accepted |
| [ADR-008](ADR-008-tts-library.md) | Text-to-Speech Library (pyttsx3 vs. cloud TTS) | Accepted |
| [ADR-009](ADR-009-packaging.md) | Windows Packaging (PyInstaller vs. cx_Freeze) | Accepted |
| [ADR-010](ADR-010-threading-model.md) | Threading Model (pystray main thread + daemon threads + Lock) | Accepted |
| [ADR-011](ADR-011-one-camera-dev-mode.md) | Single-Camera Dev Mode (--one-camera CLI flag vs. auto-detect) | Accepted |
| [ADR-012](ADR-012-macos-settings-subprocess.md) | macOS Settings Window via Subprocess (Tkinter + pystray main thread conflict) | Accepted |
| [ADR-013](ADR-013-camera-preview-handoff.md) | Camera Preview in Settings via Process Handoff | Accepted |
| [ADR-014](ADR-014-layered-coverage-gates.md) | Layered Coverage Gates (Core High-Bar 90% + Full-Codebase Floor 45%, no omit, branch coverage) | Accepted |
| [ADR-015](ADR-015-per-camera-person-detector.md) | One PersonDetector Instance Per Camera (fixes shared frame-skip cache collapsing stereo disparity) | Accepted |
| [ADR-016](ADR-016-fail-safe-degradation.md) | Fail-Safe Degradation Policy ("degrade loud, not silent" — DepthEstimator.assess_proximity with sanity bounds) | Accepted |
| [ADR-017](ADR-017-ci-performance-budgets.md) | CI-Enforced Performance Budgets (regression guards for camera-loop iter, memory, startup; hardware budgets stay manual) | Accepted |
| [ADR-018](ADR-018-mutation-and-property-testing.md) | Mutation Testing + Property Testing as Test-Quality Tools (mutmut weekly, Hypothesis per PR) | Accepted |

## How to Add a New ADR

1. Copy `ADR-000-template.md` to `ADR-NNN-short-title.md` (next available number)
2. Fill in all sections — especially **Consequences** and **Follow-up required**
3. Add a row to the index table above
4. Set status to `Draft` until the decision is finalised, then change to `Accepted`
5. If a decision is later reversed, mark it `Superseded by ADR-NNN` (do not delete)
