import threading
import time
from unittest.mock import MagicMock, patch

from audio.alert_manager import AlertManager, _CAMERA_OFFLINE_INTERVAL_S
from state import AppState


def _run(state, lock=None, *, stop=None, duration=0.15):
    """Start AlertManager.run() in a daemon thread; stop after `duration` seconds."""
    if lock is None:
        lock = threading.Lock()
    if stop is None:
        stop = threading.Event()
    t = threading.Thread(target=AlertManager().run, args=(lock, state, stop), daemon=True)
    t.start()
    time.sleep(duration)
    stop.set()
    t.join(timeout=2.0)
    return t


# --- person_too_close ---


def test_say_called_when_person_too_close():
    with patch("audio.alert_manager.pyttsx3") as mock_tts:
        engine = MagicMock()
        mock_tts.init.return_value = engine
        spoke = threading.Event()
        engine.runAndWait.side_effect = lambda: spoke.set()

        state = AppState()
        state.person_too_close = True
        lock = threading.Lock()
        stop = threading.Event()

        t = threading.Thread(target=AlertManager().run, args=(lock, state, stop), daemon=True)
        t.start()
        spoke.wait(timeout=2.0)
        stop.set()
        t.join(timeout=1.0)

    assert engine.say.called


def test_say_uses_alert_message():
    with patch("audio.alert_manager.pyttsx3") as mock_tts:
        engine = MagicMock()
        mock_tts.init.return_value = engine
        spoke = threading.Event()
        engine.runAndWait.side_effect = lambda: spoke.set()

        state = AppState()
        state.person_too_close = True
        state.alert_message = "Custom alert message"
        lock = threading.Lock()
        stop = threading.Event()

        t = threading.Thread(target=AlertManager().run, args=(lock, state, stop), daemon=True)
        t.start()
        spoke.wait(timeout=2.0)
        stop.set()
        t.join(timeout=1.0)

    engine.say.assert_called_with("Custom alert message")


def test_say_not_called_when_nothing_active():
    with patch("audio.alert_manager.pyttsx3") as mock_tts:
        engine = MagicMock()
        mock_tts.init.return_value = engine

        with patch("audio.alert_manager.time.sleep"):
            state = AppState()  # all defaults → no alert, no pause, no drift
            _run(state, duration=0.05)

    engine.say.assert_not_called()


# --- alert_paused ---


def test_distance_alert_not_spoken_when_paused():
    with patch("audio.alert_manager.pyttsx3") as mock_tts:
        engine = MagicMock()
        mock_tts.init.return_value = engine

        with (
            patch("audio.alert_manager.time.monotonic", return_value=0.0),
            patch("audio.alert_manager.time.sleep"),
        ):
            state = AppState()
            state.person_too_close = True
            state.alert_paused = True  # overrides too_close
            stop = threading.Event()
            stop.set()
            AlertManager().run(threading.Lock(), state, stop)

    # 0 seconds elapsed → camera offline cooldown not reached; no distance alert
    engine.say.assert_not_called()


def test_camera_offline_spoken_when_paused_and_cooldown_elapsed():
    with patch("audio.alert_manager.pyttsx3") as mock_tts:
        engine = MagicMock()
        mock_tts.init.return_value = engine
        spoke = threading.Event()
        engine.runAndWait.side_effect = lambda: spoke.set()

        with patch(
            "audio.alert_manager.time.monotonic", return_value=float(_CAMERA_OFFLINE_INTERVAL_S)
        ):
            state = AppState()
            state.alert_paused = True
            lock = threading.Lock()
            stop = threading.Event()

            t = threading.Thread(target=AlertManager().run, args=(lock, state, stop), daemon=True)
            t.start()
            spoke.wait(timeout=2.0)
            stop.set()
            t.join(timeout=1.0)

    assert engine.say.called
    call_text: str = engine.say.call_args[0][0].lower()
    assert "offline" in call_text or "camera" in call_text


# --- position_drift_warning ---


def test_drift_warning_spoken_exactly_once_then_flag_cleared():
    with patch("audio.alert_manager.pyttsx3") as mock_tts:
        engine = MagicMock()
        mock_tts.init.return_value = engine
        spoke = threading.Event()
        engine.runAndWait.side_effect = lambda: spoke.set()

        state = AppState()
        state.position_drift_warning = True
        lock = threading.Lock()
        stop = threading.Event()

        t = threading.Thread(target=AlertManager().run, args=(lock, state, stop), daemon=True)
        t.start()
        spoke.wait(timeout=2.0)

        # After first speak, flag should be cleared
        with lock:
            flag = state.position_drift_warning

        # Give loop one more iteration to check it doesn't speak again
        stop.set()
        t.join(timeout=1.0)

    assert flag is False  # flag cleared after first announcement
    assert engine.say.call_count == 1


def test_drift_warning_message_contains_relevant_text():
    with patch("audio.alert_manager.pyttsx3") as mock_tts:
        engine = MagicMock()
        mock_tts.init.return_value = engine
        spoke = threading.Event()
        engine.runAndWait.side_effect = lambda: spoke.set()

        state = AppState()
        state.position_drift_warning = True
        lock = threading.Lock()
        stop = threading.Event()

        t = threading.Thread(target=AlertManager().run, args=(lock, state, stop), daemon=True)
        t.start()
        spoke.wait(timeout=2.0)
        stop.set()
        t.join(timeout=1.0)

    text: str = engine.say.call_args[0][0].lower()
    assert any(kw in text for kw in ("camera", "recalib", "position", "warning"))
