import threading
import time

import pyttsx3

_CAMERA_OFFLINE_INTERVAL_S = 300  # 5 minutes between repeated camera-offline announcements


class AlertManager:
    def run(
        self,
        app_state_lock: threading.Lock,
        app_state,
        _stop_event: threading.Event | None = None,
    ) -> None:
        engine = pyttsx3.init()
        last_camera_alert_t = 0.0

        while _stop_event is None or not _stop_event.is_set():
            with app_state_lock:
                too_close = app_state.person_too_close
                paused = app_state.alert_paused
                drift_warning = app_state.position_drift_warning
                cooldown = getattr(app_state, "alert_cooldown_seconds", 3)
                message = getattr(app_state, "alert_message", "Please move back from the TV")

            if drift_warning:
                engine.say("Warning: camera position has changed. Recalibration recommended.")
                engine.runAndWait()
                with app_state_lock:
                    app_state.position_drift_warning = False

            elif paused:
                now = time.monotonic()
                if now - last_camera_alert_t >= _CAMERA_OFFLINE_INTERVAL_S:
                    engine.say("Camera offline — check the connection")
                    engine.runAndWait()
                    last_camera_alert_t = now
                time.sleep(1.0)

            elif too_close:
                engine.say(message)
                engine.runAndWait()
                time.sleep(cooldown)

            else:
                time.sleep(0.5)
