"""Settings window for macOS — runs as a standalone subprocess.

On macOS, pystray holds the AppKit main thread (NSApplication), and Tkinter also
requires the main thread.  Opening SettingsWindow from a pystray callback (even
via threading.Thread) crashes with NSInvalidArgumentException.

This script is launched as a separate process so it gets its own main thread.
Camera preview and calibration are omitted because the camera objects cannot
cross process boundaries; all other settings are fully functional.
"""

from __future__ import annotations

import pathlib
import sys
import threading
import tkinter as tk
from tkinter import ttk

# Allow running as `python tray/settings_subprocess.py` from the project root.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config.settings import load_settings, save_settings


def _speak(message: str) -> None:
    import pyttsx3

    engine = pyttsx3.init()
    engine.say(message)
    engine.runAndWait()


def main() -> None:
    settings = load_settings()

    root = tk.Tk()
    root.title("TV Distance Monitor — Settings")
    root.resizable(False, False)

    tk.Label(
        root,
        text="macOS dev mode — camera preview and calibration unavailable",
        fg="#888",
        font=("Helvetica", 11, "italic"),
    ).pack(padx=16, pady=(12, 4))

    frame = tk.Frame(root, padx=16, pady=8)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(1, weight=1)

    dist_var = tk.DoubleVar(value=settings.get("min_safe_distance_m", 1.5))
    interval_var = tk.IntVar(value=settings.get("frame_capture_interval_ms", 100))
    minor_var = tk.DoubleVar(value=settings.get("drift_threshold_minor_cm", 5.0))
    sig_var = tk.DoubleVar(value=settings.get("drift_threshold_significant_cm", 20.0))

    def _row(label: str, row: int, widget_factory):
        tk.Label(frame, text=label, anchor="w").grid(row=row, column=0, sticky="w", pady=4, padx=4)
        widget_factory(row)

    def _slider(var, lo, hi, row):
        ttk.Scale(frame, from_=lo, to=hi, variable=var, orient="horizontal", length=220).grid(
            row=row, column=1, sticky="ew", padx=4
        )

    def _spinbox(var, lo, hi, row):
        ttk.Spinbox(frame, from_=lo, to=hi, textvariable=var, width=8).grid(
            row=row, column=1, sticky="w", padx=4
        )

    _row("Min safe distance (m):", 0, lambda r: _slider(dist_var, 0.5, 3.0, r))
    _row("Frame capture interval (ms):", 1, lambda r: _slider(interval_var, 50, 500, r))
    _row("Drift minor threshold (cm):", 2, lambda r: _spinbox(minor_var, 1.0, 50.0, r))
    _row("Drift significant threshold (cm):", 3, lambda r: _spinbox(sig_var, 5.0, 100.0, r))

    btn_frame = tk.Frame(root, padx=16, pady=12)
    btn_frame.pack(fill="x")

    def on_test_alert():
        msg = settings.get("alert_message", "Please move back from the TV")
        threading.Thread(target=_speak, args=(msg,), daemon=True).start()

    def on_save():
        settings["min_safe_distance_m"] = round(dist_var.get(), 2)
        settings["frame_capture_interval_ms"] = int(interval_var.get())
        settings["drift_threshold_minor_cm"] = minor_var.get()
        settings["drift_threshold_significant_cm"] = sig_var.get()
        save_settings(settings)
        root.destroy()

    tk.Button(btn_frame, text="Test Alert", command=on_test_alert).pack(side="left")
    tk.Button(btn_frame, text="Cancel", command=root.destroy).pack(side="right", padx=4)
    tk.Button(btn_frame, text="Save", command=on_save).pack(side="right")

    root.mainloop()


if __name__ == "__main__":
    main()
