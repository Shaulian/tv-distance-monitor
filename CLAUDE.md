# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Windows desktop tray application that captures video from 2 USB cameras, runs image processing algorithms, and outputs audio announcements. Developed on macOS, deployed to Windows.

## Python Setup

- Use Python 3.9+ (3.11+ recommended for Windows packaging)
- Standard venv + pip for dependency management (or Poetry if you prefer)
- Key dependencies:

### Camera & Image Processing
- **OpenCV (cv2)**: Primary choice for USB camera capture and image processing
  - Cross-platform; develop and test algorithms on macOS before Windows deployment
  - `cv2.VideoCapture(0)` and `cv2.VideoCapture(1)` for 2 USB cameras
  - Handles frame capture, transformations, and algorithm pipelines
  - Alternative: MediaPipe (if using Google ML models for detection)

### Windows Tray & Startup
- **pystray**: Create tray icon and system tray integration
  - Handles minimize-to-tray, context menus, window lifecycle
  - Windows startup on boot via registry or `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
  - Alternative: PyQt5/PySide2 with QSystemTrayIcon (heavier, but more feature-rich UI)

### Audio Output
- **pyttsx3** (preferred): Offline text-to-speech; no internet required; fast
  - Lightweight, works on Windows/Mac/Linux
  - `engine.say("message")` to speak announcements
- **google-cloud-text-to-speech**: Higher quality, cloud-based; requires API key and internet
- **pydub + ffmpeg**: If playing pre-recorded audio files instead of TTS
- **playsound**: Simple playback of WAV/MP3 files

### Supporting Libraries
- **numpy/scipy**: Math operations for image algorithms
- **pytest**: Unit testing for image processing functions
- **pyinstaller** or **cx_Freeze**: Package Python app as `.exe` for Windows distribution

## Cross-Platform Development (macOS → Windows)

- Test camera code on macOS with available webcams first; USB device paths differ (Linux/macOS use `/dev/videoX` or device names; Windows uses integer indices)
- Audio calls may behave differently on macOS vs Windows; test TTS voice availability and speaker routing on both platforms
- Tray icon behavior and startup registry operations only testable on actual Windows
- Plan for Windows testing environment (VM, real hardware, or CI with Windows runner)

## Windows-Specific Notes

- USB camera access: May require driver installation on Windows; test with both cameras connected
- Tray startup: Create `.bat` or `.vbs` wrapper for startup folder, or use pyinstaller with Windows registry integration
- Audio: pyttsx3 may have limited voice options on Windows; test available voices with `engine.getProperty('voices')`
- File paths: Use `pathlib.Path` for cross-platform compatibility (avoid hardcoded `\` separators)

## Testing Strategy

- Unit tests for image processing algorithms (pytest)
- Manual testing on Windows (physical machine or VM) before release
- Test both USB cameras detected and handled correctly
- Verify audio announcements play at expected volume via configured speaker
- **Quote authoritative numbers, never from memory.** Before any doc, slide, ADR, or PR description quotes a test count or coverage figure, run `pytest --collect-only` and `coverage report` and paste the live output. Numbers go stale fast.

## Packaging & Distribution

- Use pyinstaller with `--onefile` flag to create single `.exe`
- Include any model files or assets in the bundle
- Consider code signing for Windows SmartScreen bypass (future)

## Development Workflow

- Keep camera and audio logic modular for independent testing
- Use `cv2.waitKey()` sparingly in development; can block tray interactions
- Version bump and CHANGELOG before releasing new `.exe` to Windows

## Git Workflow

### Commit Granularity

- **One commit per user story maximum.** Never bundle multiple stories into a single commit.
- A story may span multiple commits (e.g., tests first, then implementation), but no single commit may touch more than one story's scope.
- Commit message subject line format: `Story X.Y — <imperative description>`. Body: one sentence per logical chunk of work.

### Branching and PRs

- Every story is implemented on a dedicated branch named `feat/X.Y-short-title`.
- Open a PR against `main` before merging — even when working alone. The PR is the code review gate and the CI trigger.
- Do not commit story work directly to `main`. `main` receives merges only.
- A story is not **Done** until: all ACs are ticked in `docs/epics-and-stories.md`, CI is green on the PR, and the branch is merged.

### Stacked PRs and Branch Sync

These rules exist because they bit us in real sessions: a commit landed on `main` because the working branch had silently switched; a stacked PR was merged into its parent and left stranded above `main`; a `pull --ff-only` succeeded against a base that wasn't what was expected.

- **Verify the current branch before staging.** Run `git branch --show-current` first; do not trust prior state across multi-step work.
- **Stacked PRs target the parent feature branch, not `main`.** When a story depends on an in-flight branch (WS1 → WS0, WS2 → main-after-WS1, etc.), open the PR against the parent. GitHub auto-retargets to `main` after the parent merges. The diff stays clean.
- **After every merge by the user (or any external git op), sync AND verify.** `git fetch origin && git checkout main && git pull --ff-only` is not enough — also `git log --oneline -3` and a `grep` for the new code or `ls` for the new file to confirm what's actually in the working tree. The merge can be on the wrong base.
- **Force-push only `--force-with-lease`, only on your own feature branches.** Never force-push `main`.
- **After a stacked-PR merge, check whether the parent reached `main`.** A PR merged into a feature branch ≠ merged into `main`. If the parent is still ahead, open a fresh PR `parent → main` (see the WS1 → WS0 → PR #3 catch-up).

### Self-Review Before Every PR

Run this checklist before pushing for review — do not open a PR if any step fails. The full annotated checklist with rationale lives in `docs/story-workflow.md` § Step 4; this block is the minimum command set, mirroring CI.

```bash
black --check .                                                                                     # formatting
ruff check .                                                                                        # linting
pytest tests/unit/ tests/integration/ -q                                                            # unit + integration (zero failures)
pytest tests/performance/ -m performance -q                                                         # perf budgets (ADR-017)
pytest tests/unit/ tests/integration/ --cov --cov-report=                                           # coverage data
coverage report --include="audio/*,camera/*,config/*,detection/*,state.py" --fail-under=90          # core-logic gate (ADR-014)
coverage report --fail-under=55                                                                     # full-codebase floor (ADR-014)
```
