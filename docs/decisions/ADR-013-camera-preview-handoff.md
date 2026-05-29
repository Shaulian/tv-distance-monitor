# ADR-013 — Camera Preview in Settings via Process Handoff

**Date:** 2026-05-29  
**Status:** Accepted

---

## Context

The settings subprocess (introduced in ADR-012) runs as a separate OS process with
its own main thread so Tkinter can initialise correctly on macOS. However, on macOS
the built-in FaceTime camera (and most USB webcams) allow only one reader process
at a time. When the main app holds the camera open, the subprocess cannot acquire it
for a live preview.

---

## Options Considered

### Option A — Share frames via a pipe or shared memory
The main app encodes frames and sends them to the subprocess over a `multiprocessing.Queue`
or pipe. Rejected: adds latency, complexity, and a cross-process serialisation layer for
something that only needs to work during the settings window lifetime.

### Option B — Use a separate camera stream (duplicate handle)
Try to open the same camera index in both processes simultaneously and hope the driver
allows it. Rejected: behaviour is hardware-dependent and unreliable; fails silently on
most macOS webcams.

### Option C — Handoff: main app releases cameras before launching subprocess (chosen)
Before calling `subprocess.Popen`, the main app calls `camera_manager.release()` and
sets `num_cameras_online = 0`. The subprocess then opens its own `cv2.VideoCapture`
handles. When the subprocess exits (user saves or cancels), the main app's existing
reconnect loop automatically re-acquires the cameras within one retry interval.

---

## Decision

- `TrayApp` accepts an optional `on_before_settings` callback (default `None`).
- On macOS, `_open_settings()` calls `on_before_settings()` **before** `subprocess.Popen`.
- In `main.py`, `on_before_settings` calls `camera_manager.release()` and zeroes
  `num_cameras_online`, putting the tray into degraded mode while settings is open.
- The subprocess opens its own `VideoCapture` for each camera index read from settings.
  In `--one-camera` mode (passed via CLI flag), only the left camera is opened.
- The `R` preview canvas shows a dark placeholder when no right camera is available.
- When the subprocess exits, `run_reconnect_loop` in the main process retries within
  the configured interval (default 5 s) and restores normal operation.

---

## Consequences

- The tray shows "Status: Degraded" while the settings window is open on macOS.
  This is correct and expected — camera monitoring is paused during configuration.
- On Windows, `on_before_settings` is never called; the camera loop runs uninterrupted
  while the settings window is open (they share the same process, different threads).
- If the user force-quits the settings subprocess, cameras are not released by the
  subprocess; the reconnect loop in the main process will still recover automatically.
