# TV Distance Monitor

A Windows system tray application that monitors how close children sit to a TV screen using two USB cameras. When anyone is too close, it plays a voice announcement. The minimum safe distance is configurable.

---

## How It Works

Two USB cameras are mounted as a stereo pair near the TV. After a one-time calibration (user stands at 4 reference points), the app continuously estimates the distance of any detected person using stereo disparity. If the distance falls below the configured threshold, a TTS alert plays in a loop until the person moves back.

---

## Quick Start

See `docs/environment-setup.md` for full setup instructions.

```bash
python3.11 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

On first launch: the tray icon appears in grey. Open Settings from the tray menu and run calibration.

---

## Documentation

| Document | Description |
|----------|-------------|
| `docs/environment-setup.md` | Dev environment setup (macOS + Windows) |
| `docs/epics-and-stories.md` | Epics, user stories, and acceptance criteria |
| `docs/testing-strategy.md` | Test types, coverage targets, mocking rules |
| `docs/story-workflow.md` | Per-story development process (TDD → review → sign-off) |
| `docs/risk-assessment.md` | Technical and process risks + story dependency map |
| `docs/security-checklist.md` | Pre-release security review |
| `docs/manual-test-checklist.md` | Windows manual test checklist |
| `docs/release-process.md` | Step-by-step release procedure |
| `docs/decisions/` | Architecture Decision Records (ADRs) |
| `CHANGELOG.md` | Version history |

---

## Project Structure

```
project/
├── main.py                    # Entry point
├── camera/
│   ├── camera_manager.py      # USB camera open/read/recovery
│   ├── frame_processor.py     # Resolution normalisation
│   ├── stereo_calibration.py  # Diamond 4-point calibration
│   └── drift_detector.py      # Startup camera movement check
├── detection/
│   ├── person_detector.py     # HOG person detection
│   └── depth_estimator.py     # Stereo depth from disparity
├── audio/
│   └── alert_manager.py       # pyttsx3 TTS alert loop
├── tray/
│   ├── tray_app.py            # pystray tray icon + menu
│   └── settings_window.py     # Tkinter settings + calibration UI
├── config/
│   └── settings.py            # Load/save settings.json
├── tests/
│   ├── unit/                  # pytest unit tests
│   ├── integration/           # End-to-end module tests
│   ├── performance/           # Timing benchmarks
│   └── fixtures/              # Test frames and reference images
├── docs/                      # All project documentation
├── .github/workflows/ci.yml   # CI/CD pipeline
└── requirements.txt
```

---

## Development

Run tests:
```bash
pytest tests/unit/ -v
pytest tests/unit/ --cov --cov-report=term-missing
```

Check formatting and lint:
```bash
black --check .
ruff check .
```

See `docs/story-workflow.md` for the full per-story development process.

---

## Packaging (Windows .exe)

A Windows `.exe` is built automatically by CI when a version tag is pushed:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The artifact is attached to the GitHub Release. See `docs/release-process.md` for the full release procedure.

---

## Requirements

- Python 3.11+
- Two USB cameras (indices 0 and 1)
- Windows 10/11 for deployment
- macOS or Windows for development
