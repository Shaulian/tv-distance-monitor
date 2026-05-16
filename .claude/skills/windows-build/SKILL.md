---
name: windows-build
description: Package the Python app as a Windows .exe using pyinstaller for distribution
disable-model-invocation: true
---

## Usage

Run with `/windows-build` to create a standalone `.exe` file for Windows deployment.

## What it does

1. **Installs/updates pyinstaller** if needed
2. **Builds a single executable** (`.exe`) from your Python source
3. **Bundles all dependencies** (OpenCV, pyttsx3, pystray, etc.) into the `.exe`
4. **Outputs to `dist/` folder** with a standalone application ready for Windows distribution

## Prerequisites

- All code committed or saved (build works from current files)
- All dependencies listed in `requirements.txt` (or installed in venv)
- Main entry point defined (e.g., `main.py` at project root)

## Build Command

```bash
pyinstaller --onefile --windowed --name "CameraApp" main.py
```

Flags explained:
- `--onefile` — Creates a single `.exe` instead of a folder with many files (slower startup, but easier distribution)
- `--windowed` — Hides the console window on startup (tray app doesn't need console visible)
- `--name "CameraApp"` — Sets the `.exe` filename and window title

Output: `dist/CameraApp.exe`

## Optional: Add startup behavior

To make the `.exe` launch on Windows startup:
1. Place `CameraApp.exe` in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
2. Or use a `.bat` wrapper in the startup folder that launches the `.exe`

## If build fails

- Check that all imports in `main.py` are available (`pip list`)
- Some libraries (cv2, pyttsx3) may need explicit `--hidden-import` flags:
  ```bash
  pyinstaller --onefile --windowed --hidden-import=cv2 --hidden-import=pyttsx3 --name "CameraApp" main.py
  ```
- Build must run on Windows (or in a Windows VM/Docker) for `.exe` to work correctly

## Distribution

The `.exe` in `dist/` can be:
- Shared directly with users
- Placed in Windows Installer (NSIS, MSI) for professional setup
- Signed with a certificate (future) to bypass SmartScreen warnings
