# ADR-012 — macOS Settings Window via Subprocess

**Date:** 2026-05-29  
**Status:** Accepted

---

## Context

On macOS, both pystray and Tkinter require the AppKit main thread (NSRunLoop /
NSApplication). pystray takes ownership of the main thread when `Icon.run()` is
called. Any attempt to create a `tk.Tk()` instance from a background thread
(even an explicitly spawned `threading.Thread`) crashes with:

```
NSInvalidArgumentException: -[NSApplication macOSVersion]:
  unrecognized selector sent to instance
```

The original code opened `SettingsWindow` from a daemon thread, which worked on
Windows (no single-thread requirement for Tkinter there) but crashed on macOS.

---

## Options Considered

### Option A — Migrate settings UI to a thread-safe toolkit (e.g., PyQt5)
PyQt5 / PySide6 can be initialised from non-main threads on macOS. But this
would require rewriting the entire settings window, adding a heavy dependency,
and diverging from the Windows code path.

### Option B — Use pystray's `app.update_menu()` as a settings surface
Represent all settings as pystray submenu items. Avoids any GUI toolkit
conflict. Rejected: the resulting UX would be unusable for sliders, spinboxes,
and camera preview.

### Option C — Launch a subprocess for the settings window (chosen)
`subprocess.Popen([sys.executable, "tray/settings_subprocess.py"])` gives the
settings window its own OS process with its own main thread. Tkinter initialises
cleanly. The subprocess reads from and writes to the settings file directly,
eliminating the need to pass shared Python objects across the process boundary.

Chosen because it:
- Requires minimal changes to the existing Windows code path
- Keeps the subprocess self-contained and independently testable
- Matches how macOS native apps handle "inspector" windows in a multi-process
  model

---

## Decision

- `TrayApp._open_settings()` checks `sys.platform`. On `"darwin"` it calls
  `subprocess.Popen([sys.executable, str(settings_subprocess_path)])`.
  On all other platforms the existing `threading.Thread` path is used unchanged.
- `tray/settings_subprocess.py` is a standalone Tkinter app that reads the
  settings file on open and writes it on Save. Camera preview and calibration
  are omitted (camera objects cannot cross process boundaries); all other
  controls (distance slider, frame interval, drift thresholds, Test Alert) are
  present.

---

## Consequences

- Settings changes made in the subprocess do not update `AppState` in the
  parent process in real time. They take effect on the next app restart. This
  is acceptable for macOS dev mode.
- The subprocess inherits `sys.executable`, so it works with any virtualenv
  without extra configuration.
- Windows production behaviour is completely unchanged.
