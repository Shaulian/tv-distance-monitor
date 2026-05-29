import copy
import json
import os
import sys
from pathlib import Path

DEFAULTS: dict = {
    "min_safe_distance_m": 1.5,
    "frame_capture_interval_ms": 100,
    "alert_cooldown_seconds": 3,
    "camera_retry_interval_seconds": 5,
    "drift_threshold_minor_cm": 5.0,
    "drift_threshold_significant_cm": 20.0,
    "alert_message": "Please move back from the TV",
    "left_camera_index": 0,
    "right_camera_index": 1,
    "calibration": {
        "valid": False,
        "slope": None,
        "intercept": None,
        "reference_cam0_path": None,
        "reference_cam1_path": None,
    },
}


def _settings_path() -> Path:
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / "TVDistanceMonitor" / "settings.json"
    return Path.home() / ".TVDistanceMonitor" / "settings.json"


def load_settings() -> dict:
    path = _settings_path()
    if not path.exists():
        return copy.deepcopy(DEFAULTS)
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(DEFAULTS)
    merged = copy.deepcopy(DEFAULTS)
    merged.update(data)
    return merged


def save_settings(data: dict) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
