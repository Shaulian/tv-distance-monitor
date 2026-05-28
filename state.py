import dataclasses


@dataclasses.dataclass
class AppState:
    num_cameras_online: int = 0
    alert_paused: bool = False
    person_too_close: bool = False
    position_drift_warning: bool = False
    min_safe_distance_m: float = 1.5
    frame_capture_interval_ms: int = 100
    alert_message: str = "Please move back from the TV"
