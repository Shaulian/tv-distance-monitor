# Environment Setup Guide

## Prerequisites

- Python 3.11 (exactly — not 3.9, not 3.12; PyInstaller and pystray have version-specific behaviour)
- Git
- A code editor (VS Code recommended)
- For Windows testing: a Windows 10/11 machine or VM with USB camera access

---

## macOS Development Setup

```bash
# 1. Clone the repo
git clone <repo-url>
cd tv-distance-monitor

# 2. Create and activate virtualenv (Python 3.11 specifically)
python3.11 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify key packages loaded
python -c "import cv2, numpy, pyttsx3, pystray; print('All imports OK')"

# 5. Run linter and formatter check
black --check .
ruff check .

# 6. Run unit tests
pytest tests/unit/ -v
```

**macOS note:** pyttsx3 uses `nsss` (macOS speech) on macOS. Voice behaviour will differ from Windows. Only test alert logic (timing, flags) on macOS — test actual audio on Windows.

---

## Windows Setup (Testing / Deployment)

```bat
REM 1. Install Python 3.11 from python.org (check "Add to PATH")
REM 2. Clone or copy the repo
REM 3. Create virtualenv
python -m venv venv
venv\Scripts\activate

REM 4. Install dependencies
pip install -r requirements.txt

REM 5. Verify
python -c "import cv2, numpy, pyttsx3, pystray; print('All imports OK')"

REM 6. Connect both USB cameras, then run
python main.py
```

**Windows camera note:** If cameras are not detected at index 0/1, try `cv2.VideoCapture(0, cv2.CAP_DSHOW)` — DirectShow backend is more reliable on Windows.

---

## Verifying Camera Access

```bash
# Run the check-cameras skill from the project root
# (or manually):
python -c "
import cv2
for i in range(2):
    cap = cv2.VideoCapture(i)
    ok, frame = cap.read()
    print(f'Camera {i}: {\"OK\" if ok else \"FAILED\"} — shape {frame.shape if ok else None}')
    cap.release()
"
```

Both cameras should report OK before starting development on any camera-dependent story.

---

## IDE Configuration (VS Code)

Recommended extensions:
- Python (Microsoft)
- Pylance
- Ruff (replaces pylint/flake8 in the editor)

`.vscode/settings.json` (not committed — personal preference):
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

---

## Python Version Pinning

The `.python-version` file (if using pyenv) or CI config pins Python 3.11.  
If you install a different version, recreate the venv:

```bash
deactivate
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `import cv2` fails | `pip install opencv-python`; on Linux also `apt install libgl1` |
| `import pystray` fails on macOS | `pip install pystray`; may also need `pip install pillow` |
| Camera index 0 opens but returns black frames | Try unplugging and replugging; try `CAP_DSHOW` on Windows |
| pyttsx3 `runAndWait()` hangs on macOS | Known issue; call from a non-main thread (already handled in AlertManager) |
| PyInstaller `.exe` crashes silently on Windows | Run from terminal to see traceback: `TVDistanceMonitor.exe` in `cmd.exe` |
