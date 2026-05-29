"""Settings window for macOS — runs as a standalone subprocess.

On macOS, pystray holds the AppKit main thread (NSApplication), and Tkinter also
requires the main thread.  Opening SettingsWindow from a pystray callback (even
via threading.Thread) crashes with NSInvalidArgumentException.

This script is launched as a separate process so it gets its own main thread.
Camera preview and calibration are omitted (Story 11.7 adds preview via handoff);
all other settings are fully functional.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import threading
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from config.settings import load_settings, save_settings

# ── factory defaults shown as hints in the UI ─────────────────────────────────
_DEFAULTS = {
    "dist_cm": 150,
    "interval_ms": 100,
    "minor_cm": 5.0,
    "sig_cm": 20.0,
}


# ── pure helpers (unit-tested) ─────────────────────────────────────────────────


def cm_to_m(cm: float) -> float:
    return cm / 100.0


def m_to_cm(m: float) -> float:
    return m * 100.0


def build_save_data(
    dist_cm: float,
    interval_ms: float,
    minor_cm: float,
    sig_cm: float,
) -> dict:
    return {
        "min_safe_distance_m": round(cm_to_m(dist_cm), 4),
        "frame_capture_interval_ms": int(interval_ms),
        "drift_threshold_minor_cm": minor_cm,
        "drift_threshold_significant_cm": sig_cm,
    }


def swap_camera(old_left: int, old_right: int, changed: str, new_val: int) -> tuple[int, int]:
    """Return (new_left, new_right), swapping the other side when there would be a collision."""
    if changed == "left":
        if new_val == old_right:
            return new_val, old_left
        return new_val, old_right
    else:
        if new_val == old_left:
            return old_right, new_val
        return old_left, new_val


# ── slider row builder ─────────────────────────────────────────────────────────


def _make_slider_row(
    parent: tk.Widget,
    grid_row: int,
    label: str,
    var: tk.Variable,
    lo: float,
    hi: float,
    default: float,
    unit: str,
    fmt: str = "{:.0f}",
) -> None:
    """Build a labelled slider row with value display, hint line, and reset button."""

    # Row label
    tk.Label(parent, text=label, anchor="w").grid(
        row=grid_row * 3, column=0, sticky="w", padx=(0, 8), pady=(8, 0)
    )

    # Slider
    scale = ttk.Scale(parent, from_=lo, to=hi, variable=var, orient="horizontal", length=260)
    scale.grid(row=grid_row * 3, column=1, sticky="ew", padx=(0, 4))

    # Live value label
    val_lbl = tk.Label(parent, width=9, anchor="w")
    val_lbl.grid(row=grid_row * 3, column=2)

    def _refresh(*_):
        val_lbl.config(text=fmt.format(var.get()) + f" {unit}")

    var.trace_add("write", _refresh)
    _refresh()

    # Reset button
    def _reset():
        var.set(default)

    tk.Button(parent, text="↺", command=_reset, width=2, relief="flat").grid(
        row=grid_row * 3, column=3, padx=(2, 0)
    )

    # Hint line: min — default — max
    hint = f"min: {fmt.format(lo)} {unit}   default: {fmt.format(default)} {unit}   max: {fmt.format(hi)} {unit}"
    tk.Label(parent, text=hint, fg="#888", font=("Helvetica", 10)).grid(
        row=grid_row * 3 + 1, column=1, columnspan=3, sticky="w", padx=(0, 4)
    )

    # Spacer row
    tk.Label(parent, text="").grid(row=grid_row * 3 + 2, column=0)


# ── TTS helper ────────────────────────────────────────────────────────────────


def _speak(message: str) -> None:
    import pyttsx3

    engine = pyttsx3.init()
    engine.say(message)
    engine.runAndWait()


# ── main window ───────────────────────────────────────────────────────────────


_PREVIEW_W, _PREVIEW_H = 320, 240
_PREVIEW_FPS = 10


def main() -> None:
    import cv2
    from PIL import Image, ImageTk

    parser = argparse.ArgumentParser()
    parser.add_argument("--one-camera", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    left_idx = settings.get("left_camera_index", 0)
    right_idx = settings.get("right_camera_index", 1)

    # Open cameras for preview (main app released them before launching us)
    cap_left = cv2.VideoCapture(left_idx)
    cap_right = None if args.one_camera else cv2.VideoCapture(right_idx)

    root = tk.Tk()
    root.title("TV Distance Monitor — Settings")
    root.resizable(False, False)

    tk.Label(
        root,
        text="macOS dev mode — calibration not available",
        fg="#888",
        font=("Helvetica", 11, "italic"),
    ).pack(padx=16, pady=(12, 4))

    # ── camera previews ────────────────────────────────────────────────────────
    preview_frame = tk.Frame(root, padx=16)
    preview_frame.pack()

    _photos: list = []

    def _make_preview(parent, label: str):
        col = tk.Frame(parent)
        col.pack(side="left", padx=4)
        tk.Label(col, text=label, font=("Helvetica", 11, "bold")).pack()
        canvas = tk.Canvas(col, width=_PREVIEW_W, height=_PREVIEW_H, bg="#111")
        canvas.pack()
        return canvas

    canvas_l = _make_preview(preview_frame, "L")
    canvas_r = _make_preview(preview_frame, "R")

    def _tick_preview():
        _photos.clear()
        for cap, canvas in ((cap_left, canvas_l), (cap_right, canvas_r)):
            if cap is None or not cap.isOpened():
                continue
            ok, frame = cap.read()
            if not ok:
                continue
            frame_rgb = cv2.cvtColor(cv2.resize(frame, (_PREVIEW_W, _PREVIEW_H)), cv2.COLOR_BGR2RGB)
            photo = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
            canvas.create_image(0, 0, anchor="nw", image=photo)
            _photos.append(photo)
        root.after(1000 // _PREVIEW_FPS, _tick_preview)

    root.after(100, _tick_preview)

    def _on_close():
        if cap_left:
            cap_left.release()
        if cap_right:
            cap_right.release()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)

    # ── camera L/R assignment ──────────────────────────────────────────────────
    cam_frame = tk.LabelFrame(
        root, text="Camera assignment (from viewer's perspective)", padx=12, pady=8
    )
    cam_frame.pack(fill="x", padx=16, pady=(4, 0))

    left_idx_var = tk.IntVar(value=settings.get("left_camera_index", 0))
    right_idx_var = tk.IntVar(value=settings.get("right_camera_index", 1))
    _CAM_OPTIONS = [0, 1]

    def _on_left_changed(*_):
        new_left = left_idx_var.get()
        new_left, new_right = swap_camera(left_idx_var.get(), right_idx_var.get(), "left", new_left)
        left_idx_var.set(new_left)
        right_idx_var.set(new_right)

    def _on_right_changed(*_):
        new_right = right_idx_var.get()
        new_left, new_right = swap_camera(
            left_idx_var.get(), right_idx_var.get(), "right", new_right
        )
        left_idx_var.set(new_left)
        right_idx_var.set(new_right)

    tk.Label(cam_frame, text="Left camera index:").grid(row=0, column=0, sticky="w", padx=(0, 8))
    tk.OptionMenu(
        cam_frame, left_idx_var, *_CAM_OPTIONS, command=lambda _: _on_left_changed()
    ).grid(row=0, column=1, sticky="w")
    tk.Label(cam_frame, text="Right camera index:").grid(row=0, column=2, sticky="w", padx=(16, 8))
    tk.OptionMenu(
        cam_frame, right_idx_var, *_CAM_OPTIONS, command=lambda _: _on_right_changed()
    ).grid(row=0, column=3, sticky="w")

    frame = tk.Frame(root, padx=16, pady=4)
    frame.pack(fill="both", expand=True)
    frame.columnconfigure(1, weight=1)

    dist_var = tk.DoubleVar(value=m_to_cm(settings.get("min_safe_distance_m", 1.5)))
    interval_var = tk.DoubleVar(value=settings.get("frame_capture_interval_ms", 100))
    minor_var = tk.DoubleVar(value=settings.get("drift_threshold_minor_cm", 5.0))
    sig_var = tk.DoubleVar(value=settings.get("drift_threshold_significant_cm", 20.0))

    _make_slider_row(frame, 0, "Min safe distance:", dist_var, 50, 300, _DEFAULTS["dist_cm"], "cm")
    _make_slider_row(
        frame, 1, "Frame interval:", interval_var, 50, 500, _DEFAULTS["interval_ms"], "ms"
    )
    _make_slider_row(
        frame, 2, "Drift minor threshold:", minor_var, 1, 50, _DEFAULTS["minor_cm"], "cm", "{:.1f}"
    )
    _make_slider_row(
        frame,
        3,
        "Drift significant threshold:",
        sig_var,
        5,
        100,
        _DEFAULTS["sig_cm"],
        "cm",
        "{:.1f}",
    )

    # ── buttons ───────────────────────────────────────────────────────────────
    btn_frame = tk.Frame(root, padx=16, pady=12)
    btn_frame.pack(fill="x")

    alert_btn = tk.Button(btn_frame, text="Test Alert", width=12)
    alert_btn.pack(side="left")

    def on_test_alert():
        alert_btn.config(state="disabled", text="▶ Testing...")
        msg = settings.get("alert_message", "Please move back from the TV")

        def _run():
            _speak(msg)
            root.after(0, lambda: alert_btn.config(state="normal", text="Test Alert"))

        threading.Thread(target=_run, daemon=True).start()

    alert_btn.config(command=on_test_alert)

    tk.Button(btn_frame, text="Cancel", command=_on_close, width=8).pack(side="right", padx=(4, 0))

    def on_save():
        data = build_save_data(
            dist_cm=dist_var.get(),
            interval_ms=interval_var.get(),
            minor_cm=minor_var.get(),
            sig_cm=sig_var.get(),
        )
        data["left_camera_index"] = left_idx_var.get()
        data["right_camera_index"] = right_idx_var.get()
        settings.update(data)
        save_settings(settings)
        _on_close()

    tk.Button(btn_frame, text="Save and close", command=on_save, width=14).pack(side="right")

    root.mainloop()


if __name__ == "__main__":
    main()
