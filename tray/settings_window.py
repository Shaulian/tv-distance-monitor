import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import cv2
from PIL import Image, ImageTk

from camera.stereo_calibration import StereoCalibrator

_PREVIEW_W, _PREVIEW_H = 320, 240
_PREVIEW_INTERVAL_MS = 100


class SettingsWindow:
    def __init__(
        self,
        app_state,
        app_state_lock: threading.Lock,
        camera_manager,
        calibrator: StereoCalibrator,
        on_save=None,
    ):
        self._state = app_state
        self._lock = app_state_lock
        self._camera = camera_manager
        self._calibrator = calibrator
        self._on_save = on_save
        self._root: tk.Tk | None = None
        self._preview_running = False
        self._photos: list = []

    def show(self) -> None:
        self._root = tk.Tk()
        self._root.title("TV Distance Monitor — Settings")
        self._root.resizable(False, False)
        self._build()
        self._preview_running = True
        self._root.after(_PREVIEW_INTERVAL_MS, self._tick_preview)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._root.mainloop()

    def _build(self) -> None:
        root = self._root
        root.configure(padx=12, pady=12)

        with self._lock:
            valid = self._state.calibration_valid
            dist = self._state.min_safe_distance_m
            interval = self._state.frame_capture_interval_ms
            minor = self._state.drift_threshold_minor_cm
            sig = self._state.drift_threshold_significant_cm

        # Calibration status banner
        bg = "#16a34a" if valid else "#dc2626"
        text = "Calibrated" if valid else "NOT CALIBRATED"
        self._banner = tk.Label(
            root, text=text, bg=bg, fg="white", font=("Arial", 11, "bold"), pady=6
        )
        self._banner.pack(fill="x", pady=(0, 8))

        # Dual camera preview
        preview_row = tk.Frame(root)
        preview_row.pack()
        self._canvas_l = tk.Canvas(preview_row, width=_PREVIEW_W, height=_PREVIEW_H, bg="#111")
        self._canvas_l.pack(side="left", padx=4)
        self._canvas_r = tk.Canvas(preview_row, width=_PREVIEW_W, height=_PREVIEW_H, bg="#111")
        self._canvas_r.pack(side="left", padx=4)

        # Controls grid
        grid = tk.Frame(root)
        grid.pack(fill="x", pady=10)
        grid.columnconfigure(1, weight=1)

        self._dist_var = tk.DoubleVar(value=dist)
        self._interval_var = tk.IntVar(value=interval)
        self._minor_var = tk.DoubleVar(value=minor)
        self._sig_var = tk.DoubleVar(value=sig)

        tk.Label(grid, text="Min safe distance (m):", anchor="w").grid(
            row=0, column=0, sticky="w", padx=4, pady=3
        )
        ttk.Scale(
            grid,
            from_=0.5,
            to=3.0,
            variable=self._dist_var,
            orient="horizontal",
            length=220,
            command=lambda _: self._on_dist(),
        ).grid(row=0, column=1, sticky="ew", padx=4)
        self._dist_label = tk.Label(grid, width=5, anchor="w")
        self._dist_label.grid(row=0, column=2)

        tk.Label(grid, text="Frame capture interval (ms):", anchor="w").grid(
            row=1, column=0, sticky="w", padx=4, pady=3
        )
        ttk.Scale(
            grid,
            from_=50,
            to=500,
            variable=self._interval_var,
            orient="horizontal",
            length=220,
            command=lambda _: self._on_interval(),
        ).grid(row=1, column=1, sticky="ew", padx=4)
        self._interval_label = tk.Label(grid, width=5, anchor="w")
        self._interval_label.grid(row=1, column=2)

        tk.Label(grid, text="Drift minor threshold (cm):", anchor="w").grid(
            row=2, column=0, sticky="w", padx=4, pady=3
        )
        ttk.Spinbox(grid, from_=1, to=50, textvariable=self._minor_var, width=8).grid(
            row=2, column=1, sticky="w", padx=4
        )

        tk.Label(grid, text="Drift significant threshold (cm):", anchor="w").grid(
            row=3, column=0, sticky="w", padx=4, pady=3
        )
        ttk.Spinbox(grid, from_=5, to=100, textvariable=self._sig_var, width=8).grid(
            row=3, column=1, sticky="w", padx=4
        )

        self._on_dist()
        self._on_interval()

        # Buttons
        btn_row = tk.Frame(root)
        btn_row.pack(pady=(4, 0))
        calib_text = "Recalibrate" if valid else "Calibrate"
        self._calib_btn = tk.Button(btn_row, text=calib_text, command=self._calibrate, width=12)
        self._calib_btn.pack(side="left", padx=4)
        tk.Button(btn_row, text="Test Alert", command=self._test_alert, width=10).pack(
            side="left", padx=4
        )
        tk.Button(btn_row, text="Save", command=self._save, width=8).pack(side="left", padx=4)

        self._status_lbl = tk.Label(root, text="", fg="#555")
        self._status_lbl.pack(pady=(6, 0))

    def _on_dist(self) -> None:
        val = round(self._dist_var.get(), 2)
        self._dist_label.config(text=f"{val:.2f}")
        with self._lock:
            self._state.min_safe_distance_m = val

    def _on_interval(self) -> None:
        val = int(self._interval_var.get())
        self._interval_label.config(text=str(val))
        with self._lock:
            self._state.frame_capture_interval_ms = val

    def _tick_preview(self) -> None:
        if not self._preview_running or self._root is None:
            return
        left, right = self._camera.read_frames()
        self._photos.clear()
        for canvas, frame in ((self._canvas_l, left), (self._canvas_r, right)):
            if frame is not None:
                frame_resized = cv2.resize(frame, (_PREVIEW_W, _PREVIEW_H))
                frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                photo = ImageTk.PhotoImage(Image.fromarray(frame_rgb))
                canvas.create_image(0, 0, anchor="nw", image=photo)
                self._photos.append(photo)
        self._root.after(_PREVIEW_INTERVAL_MS, self._tick_preview)

    def _calibrate(self) -> None:
        self._calib_btn.config(state="disabled")
        self._status_lbl.config(text="Calibrating…")

        def progress(i: int, total: int) -> None:
            if self._root:
                self._root.after(
                    0,
                    lambda: self._status_lbl.config(text=f"Calibrating… point {i + 1}/{total}"),
                )

        def run() -> None:
            try:
                result = self._calibrator.calibrate_diamond(self._camera, progress)
                ref_dir = Path.home() / ".TVDistanceMonitor" / "references"
                ref_result = self._calibrator.save_reference_scene(self._camera, ref_dir)
                calib = {**result, **ref_result, "valid": True}
                with self._lock:
                    self._state.calibration_valid = True
                if self._on_save:
                    self._on_save({"calibration": calib})

                def on_success() -> None:
                    self._banner.config(text="Calibrated", bg="#16a34a")
                    self._calib_btn.config(text="Recalibrate", state="normal")
                    self._status_lbl.config(text="Calibration complete.")

                if self._root:
                    self._root.after(0, on_success)
            except Exception as _exc:
                err_msg = str(_exc)

                def on_error() -> None:
                    messagebox.showerror("Calibration Error", err_msg)
                    self._calib_btn.config(state="normal")
                    self._status_lbl.config(text="")

                if self._root:
                    self._root.after(0, on_error)

        threading.Thread(target=run, daemon=True).start()

    def _test_alert(self) -> None:
        def speak() -> None:
            import pyttsx3

            engine = pyttsx3.init()
            engine.say(getattr(self._state, "alert_message", "Test alert"))
            engine.runAndWait()

        threading.Thread(target=speak, daemon=True).start()

    def _save(self) -> None:
        data = {
            "min_safe_distance_m": round(self._dist_var.get(), 2),
            "frame_capture_interval_ms": int(self._interval_var.get()),
            "drift_threshold_minor_cm": self._minor_var.get(),
            "drift_threshold_significant_cm": self._sig_var.get(),
        }
        if self._on_save:
            self._on_save(data)
        self._status_lbl.config(text="Settings saved.")

    def _on_close(self) -> None:
        self._preview_running = False
        if self._root:
            self._root.destroy()
            self._root = None
