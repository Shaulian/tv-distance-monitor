import dataclasses


@dataclasses.dataclass
class AppState:
    num_cameras_online: int = 0
    alert_paused: bool = False
    person_too_close: bool = False
    position_drift_warning: bool = False
    calibration_valid: bool = False
    autostart_enabled: bool = True
    min_safe_distance_m: float = 1.5
    frame_capture_interval_ms: int = 100
    alert_cooldown_seconds: int = 3
    alert_message: str = "Please move back from the TV"
    drift_threshold_minor_cm: float = 5.0
    drift_threshold_significant_cm: float = 20.0
    awaiting_camera_permission: bool = False
