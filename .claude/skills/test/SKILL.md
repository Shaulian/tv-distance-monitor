---
name: test
description: Run pytest on image processing functions and verify both USB cameras are detected and working
---

## Usage

Run with `/test` to validate your code and hardware setup.

## What it does

1. **Run pytest** on all test files in the project (looks for `test_*.py` or `*_test.py`)
2. **Verify USB cameras** — attempts to open both camera indices (0 and 1) using OpenCV to confirm they're accessible
3. **Report results** — shows test pass/fail status and camera detection results

## When to use

- After writing new image processing functions (before deploying)
- When troubleshooting camera access issues on Windows
- Before packaging as `.exe` to catch obvious bugs
- After connecting/disconnecting USB cameras to verify detection

## Prerequisites

- pytest installed: `pip install pytest`
- USB cameras connected and drivers installed (Windows)
- Test files created (initially none, but create as you add logic)

## Setup (one-time)

If you haven't set up tests yet, create a `tests/` directory:
```bash
mkdir -p tests
touch tests/test_camera.py  # Start with a basic camera detection test
touch tests/test_algorithms.py  # Add image processing tests here
```

Example basic test in `tests/test_camera.py`:
```python
import cv2

def test_cameras_available():
    """Verify both USB cameras are accessible."""
    for cam_idx in [0, 1]:
        cap = cv2.VideoCapture(cam_idx)
        assert cap.isOpened(), f"Camera {cam_idx} not found or not accessible"
        cap.release()
```
