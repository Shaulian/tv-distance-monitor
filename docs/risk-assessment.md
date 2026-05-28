# Risk Assessment & Dependency Map

## How to Use This Document

Risks are rated: **Likelihood** (L/M/H) × **Impact** (L/M/H) = **Priority** (1–9).  
Review this document at the start of each epic. Update when a risk is resolved or a new one is discovered.

---

## Technical Risks

| # | Risk | Likelihood | Impact | Priority | Mitigation | Owner |
|---|------|-----------|--------|----------|------------|-------|
| T1 | USB cameras not detected on Windows (driver issues) | M | H | 6 | Test with both cameras on target Windows machine early (Epic 2); document required drivers in setup guide | Dev |
| T2 | HOG person detector insufficient accuracy at real-world angles/distances | M | H | 6 | Test on fixture frames from actual camera positions; have MediaPipe upgrade path (ADR-004) | Dev |
| T3 | pyttsx3 voice unavailable or silent on target Windows machine | M | H | 6 | Include "Test Alert" in Settings UI; test on Windows VM before release | Dev |
| T4 | phaseCorrelate drift detection unreliable on low-texture scene | L | M | 2 | Warn user at calibration time if reference frame has low variance; document in manual test checklist | Dev |
| T5 | PyInstaller .exe flagged by Windows Defender / SmartScreen | H | M | 6 | Document workaround for users (right-click → Run Anyway); code signing in v2 | Dev |
| T6 | Linear calibration fit inaccurate outside 0.5–3m range | L | M | 2 | Clamp and warn if estimated distance is outside calibration range; document in UI | Dev |
| T7 | pystray behaves differently on Windows vs. macOS (icon render, menu) | M | M | 4 | Manual test on Windows VM early (Story 8.2); keep tray logic minimal | Dev |
| T8 | Stereo matching breaks with very different camera resolutions | L | M | 2 | Resolution normalisation in FrameProcessor (Story 2.3); unit tested | Dev |
| T9 | Frame processing loop exceeds 80ms budget on low-spec Windows PC | M | H | 6 | Performance baseline test (Epic 1 → measure early); frame-skip every 3rd frame in HOG | Dev |
| T10 | Threading deadlock if alert thread holds lock during TTS call | L | H | 3 | Lock discipline rule: never call blocking I/O while holding `app_state_lock`; documented in ADR-010 | Dev |

---

## Dependency Map (Story Blockers)

Stories cannot start until their blockers are complete.

```
Story 1.1 (skeleton + deps)
  └── Story 1.2 (settings)
        ├── Story 2.1 (camera manager open/read)
        │     ├── Story 2.2 (degraded mode)
        │     ├── Story 2.3 (frame processor)
        │     │     └── Story 3.1 (HOG person detector)
        │     │           └── Story 4.1 (depth estimator)
        │     │                 └── Story 8.1 (app state + threading)
        │     │                       ├── Story 7.1 (alert manager)
        │     │                       ├── Story 8.2 (tray icon)
        │     │                       └── Story 8.3 (settings window)
        │     │                             └── Story 8.4 (main entry point)
        │     └── Story 5.1 (stereo calibrator)
        │           └── Story 5.2 (reference scene capture)
        │                 └── Story 6.1 (drift detector)
        │                       └── Story 8.4 (main entry point)
        └── Story 9.1 (PyInstaller) — after Story 8.4
              └── Story 9.2 (Windows autostart)
```

**Critical path:** 1.1 → 1.2 → 2.1 → 2.3 → 3.1 → 4.1 → 8.1 → 8.3/8.4 → 9.1

---

## External Dependencies

| Dependency | Version | Risk if Unavailable | Notes |
|-----------|---------|---------------------|-------|
| opencv-python | 4.x | HIGH — core of project | Pin exact version; test on Windows |
| pyttsx3 | 2.90 | HIGH — all audio alerts | Known macOS quirks; primary risk is Windows voice availability |
| pystray | 0.19+ | HIGH — tray is the whole UI shell | Test on Windows; macOS behaviour differs |
| numpy | 1.x / 2.x | MEDIUM — used in calibration math | Pin major version |
| pytest / black / ruff | latest | LOW — dev tooling only | No runtime impact |
| PyInstaller | 6.x | MEDIUM — only needed for packaging | Only used at release time |

---

## Process Risks

| # | Risk | Likelihood | Impact | Priority | Mitigation |
|---|------|-----------|--------|----------|------------|
| P1 | No access to Windows machine for manual testing | M | H | 6 | Set up Windows VM (VirtualBox / Parallels) early; don't leave Windows testing to the end |
| P2 | Calibration procedure confusing for non-technical users | M | M | 4 | Run usability test with a real caregiver before v1 release |
| P3 | Scope creep (multiple children, multiple TVs) | M | M | 4 | Enforce story acceptance criteria strictly; additions go into a backlog |
