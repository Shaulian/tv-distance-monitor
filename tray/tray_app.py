import sys
import threading
import time

import pystray
from PIL import Image

_ICON_SIZE = 64
_POLL_INTERVAL_S = 0.5

_COLORS: dict[str, tuple[int, int, int]] = {
    "green": (34, 197, 94),  # OK / monitoring active
    "red": (239, 68, 68),  # Too close
    "orange": (249, 115, 22),  # Degraded / camera offline
    "grey": (156, 163, 175),  # Uncalibrated
}


def _make_icon(color: str) -> Image.Image:
    return Image.new("RGB", (_ICON_SIZE, _ICON_SIZE), _COLORS[color])


class TrayApp:
    def __init__(self, app_state, app_state_lock: threading.Lock, on_settings, on_quit):
        self._state = app_state
        self._lock = app_state_lock
        self._on_settings = on_settings
        self._on_quit = on_quit
        self._icon: pystray.Icon | None = None

    def run(self) -> None:
        def get_status(item: pystray.MenuItem) -> str:
            with self._lock:
                valid = self._state.calibration_valid
                cameras = self._state.num_cameras_online
                too_close = self._state.person_too_close
                paused = self._state.alert_paused
            if not valid:
                return "Status: Uncalibrated"
            if paused or cameras < 2:
                return "Status: Degraded"
            if too_close:
                return "Status: Too Close"
            return "Status: OK"

        def toggle_autostart(icon: pystray.Icon, item: pystray.MenuItem) -> None:
            from tray.autostart import is_autostart_enabled, set_autostart

            enabled = not is_autostart_enabled()
            set_autostart(enabled)
            with self._lock:
                self._state.autostart_enabled = enabled

        menu = pystray.Menu(
            pystray.MenuItem(get_status, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings", self._open_settings),
            pystray.MenuItem("Toggle Autostart", toggle_autostart),
            pystray.MenuItem("Quit", self._quit),
        )

        self._icon = pystray.Icon(
            "TVDistanceMonitor",
            _make_icon("grey"),
            "TV Distance Monitor",
            menu,
        )

        poll = threading.Thread(target=self._poll_state, daemon=True)
        poll.start()
        self._icon.run()

    def _poll_state(self) -> None:
        last_color: str | None = None
        while True:
            with self._lock:
                valid = self._state.calibration_valid
                cameras = self._state.num_cameras_online
                too_close = self._state.person_too_close
                paused = self._state.alert_paused

            if not valid:
                color = "grey"
            elif paused or cameras < 2:
                color = "orange"
            elif too_close:
                color = "red"
            else:
                color = "green"

            if color != last_color and self._icon is not None:
                self._icon.icon = _make_icon(color)
                last_color = color

            time.sleep(_POLL_INTERVAL_S)

    def _open_settings(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        threading.Thread(target=self._on_settings, daemon=True).start()

    def _quit(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        icon.stop()
        self._on_quit()

    def stop(self) -> None:
        if self._icon is not None:
            self._icon.stop()

    @staticmethod
    def register_autostart_on_first_run(exe_path=None) -> None:
        if sys.platform != "win32":
            return
        from tray.autostart import is_autostart_enabled, set_autostart

        if not is_autostart_enabled():
            set_autostart(True, exe_path)
