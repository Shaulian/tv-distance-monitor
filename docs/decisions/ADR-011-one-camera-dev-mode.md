# ADR-011 — Single-Camera Dev Mode via CLI Flag

**Date:** 2026-05-29  
**Status:** Accepted

---

## Context

The app requires two USB cameras for stereo depth estimation. During macOS development, only the built-in webcam (index 0) is typically available. Without a workaround, every launch fails to reach the calibrated state, making it impossible to exercise the tray icon, settings window, and TTS alert path on macOS.

---

## Options Considered

### Option A — Auto-detect camera count, silently degrade
Run the normal open_cameras() path; if only one camera is found, operate in single-camera mode automatically. No CLI flag needed.

Rejected: auto-detection masks real hardware problems (e.g., a USB camera disconnected accidentally). It is better to make the developer explicitly opt in to one-camera mode so two-camera failures remain visible.

### Option B — `--one-camera` CLI flag (chosen)
Add a `--one-camera` argument to `main.py`. When set, `CameraManager` opens only index 0 and always returns `(frame, None)` from `read_frames()`. Distance estimation and calibration are skipped; the tray, settings window, and TTS continue to work.

Chosen because: explicit opt-in, zero impact on the normal code path, easy to document, easy to test.

### Option C — Environment variable (`TVDM_ONE_CAMERA=1`)
Similar to option B but via an env var. Rejected in favour of a CLI flag because a flag appears in `--help`, is self-documenting, and does not pollute the shell environment.

---

## Decision

Implement `--one-camera` as an `argparse` flag in `main.py`. Pass `one_camera_mode=True` to `CameraManager.__init__()`. The flag does not affect any other module.

---

## Consequences

- One-camera mode cannot calibrate (stereo depth requires two cameras); tray always shows "Uncalibrated" when `--one-camera` is used.
- `run_dev.sh` prints the flag in its "Setup complete" message so developers know it exists.
- No change to the Windows production path (`one_camera_mode` defaults to `False`).
