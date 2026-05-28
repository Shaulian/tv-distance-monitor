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

## How to Add a New ADR

1. Copy `ADR-000-template.md` to `ADR-NNN-short-title.md` (next available number)
2. Fill in all sections — especially **Consequences** and **Follow-up required**
3. Add a row to the index table above
4. Set status to `Draft` until the decision is finalised, then change to `Accepted`
5. If a decision is later reversed, mark it `Superseded by ADR-NNN` (do not delete)
