---
name: check-cameras
description: Verify both USB cameras are accessible and can capture frames
---

## Usage

Run with `/check-cameras` to diagnose USB camera detection and connectivity issues.

## What it does

1. **Lists available cameras** using OpenCV (attempts indices 0 and 1)
2. **Verifies each camera opens** without errors
3. **Captures a test frame** from each camera to confirm functionality
4. **Reports camera properties** (resolution, FPS, etc.)
5. **Suggests fixes** if cameras are not detected

## When to use

- Troubleshooting camera access issues on Windows
- After connecting USB cameras to verify they're recognized
- After updating drivers or changing USB ports
- When developing camera initialization code
- Before packaging as `.exe` to ensure hardware is accessible

## Prerequisites

- Both USB cameras physically connected to Windows machine
- Latest USB drivers installed (may require manual driver installation on Windows)
- OpenCV installed: `pip install opencv-python`

## Manual test script

If you want to test cameras directly in Python:

```python
import cv2

def test_camera(cam_idx):
    cap = cv2.VideoCapture(cam_idx)
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print(f"Camera {cam_idx}: OK - {frame.shape[0]}x{frame.shape[1]} pixels")
        else:
            print(f"Camera {cam_idx}: Cannot read frame")
        cap.release()
    else:
        print(f"Camera {cam_idx}: Not accessible")

for i in [0, 1]:
    test_camera(i)
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Camera 0: Not accessible" | Check USB connection, try different USB port, update drivers |
| "Cannot read frame" | Camera may be in use by another app (close Zoom, Teams, etc.) |
| Only 1 camera detected | USB hub may not provide enough power; try different hub or direct ports |
| Works on macOS but not Windows | Windows drivers may be missing; install manufacturer drivers |

## Notes

- Camera indices on Windows are typically 0 and 1 for the first two USB cameras
- Some USB cameras may appear as different indices if one is already in use
- Build this into your main app's startup routine to alert user if cameras missing
