import threading

from state import AppState


def test_appstate_default_values():
    state = AppState()
    assert state.num_cameras_online == 0
    assert state.alert_paused is False
    assert state.person_too_close is False
    assert state.position_drift_warning is False
    assert state.calibration_valid is False
    assert state.autostart_enabled is True
    assert state.min_safe_distance_m == 1.5
    assert state.frame_capture_interval_ms == 100
    assert state.alert_cooldown_seconds == 3
    assert state.alert_message == "Please move back from the TV"
    assert state.drift_threshold_minor_cm == 5.0
    assert state.drift_threshold_significant_cm == 20.0


def test_appstate_accepts_keyword_overrides():
    state = AppState(num_cameras_online=2, alert_paused=True, min_safe_distance_m=2.0)
    assert state.num_cameras_online == 2
    assert state.alert_paused is True
    assert state.min_safe_distance_m == 2.0


def test_concurrent_reads_and_writes_are_consistent():
    state = AppState()
    lock = threading.Lock()

    def writer() -> None:
        for i in range(1000):
            with lock:
                state.person_too_close = bool(i % 2)
                state.num_cameras_online = i % 3

    def reader() -> None:
        for _ in range(1000):
            with lock:
                _ = state.person_too_close
                _ = state.num_cameras_online

    threads = [
        threading.Thread(target=writer),
        threading.Thread(target=writer),
        threading.Thread(target=reader),
        threading.Thread(target=reader),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    for t in threads:
        assert not t.is_alive(), "Thread did not complete within timeout"


def test_lock_protected_increment_is_race_free():
    state = AppState()
    lock = threading.Lock()

    def increment_1000() -> None:
        for _ in range(1000):
            with lock:
                state.num_cameras_online += 1

    threads = [threading.Thread(target=increment_1000) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert state.num_cameras_online == 4000
