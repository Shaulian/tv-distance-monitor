"""
Tests for the platform-aware settings window dispatch in TrayApp.

On macOS, Tkinter and pystray both require the main thread (AppKit NSApplication),
creating an irreconcilable conflict when the settings window is opened from a
pystray menu callback. The fix: open the settings window as a subprocess on macOS
so it gets its own main thread.
"""

import threading
from unittest.mock import MagicMock, patch

from state import AppState
from tray.tray_app import TrayApp


def _make_tray():
    state = AppState()
    lock = threading.Lock()
    return TrayApp(state, lock, on_settings=MagicMock(), on_quit=MagicMock())


class TestSettingsDispatch:
    def test_macos_opens_subprocess_not_thread(self):
        """On macOS the settings window must be launched as a subprocess."""
        tray = _make_tray()
        with (
            patch("tray.tray_app.sys") as mock_sys,
            patch("tray.tray_app.subprocess.Popen") as mock_popen,
        ):
            mock_sys.platform = "darwin"
            mock_sys.executable = "/usr/bin/python3"
            tray._open_settings(MagicMock(), MagicMock())
        mock_popen.assert_called_once()

    def test_macos_subprocess_command_targets_settings_subprocess(self):
        """The subprocess command must point at settings_subprocess.py."""
        tray = _make_tray()
        with (
            patch("tray.tray_app.sys") as mock_sys,
            patch("tray.tray_app.subprocess.Popen") as mock_popen,
        ):
            mock_sys.platform = "darwin"
            mock_sys.executable = "/usr/bin/python3"
            tray._open_settings(MagicMock(), MagicMock())
        cmd = mock_popen.call_args[0][0]
        assert any("settings_subprocess" in str(arg) for arg in cmd)

    def test_macos_does_not_spawn_a_thread(self):
        """On macOS no threading.Thread should be created for the settings window."""
        tray = _make_tray()
        with (
            patch("tray.tray_app.sys") as mock_sys,
            patch("tray.tray_app.subprocess.Popen"),
            patch("tray.tray_app.threading.Thread") as mock_thread,
        ):
            mock_sys.platform = "darwin"
            mock_sys.executable = "/usr/bin/python3"
            tray._open_settings(MagicMock(), MagicMock())
        mock_thread.assert_not_called()

    def test_windows_opens_thread_not_subprocess(self):
        """On Windows the settings window is opened via threading.Thread (existing behaviour)."""
        tray = _make_tray()
        with (
            patch("tray.tray_app.sys") as mock_sys,
            patch("tray.tray_app.subprocess.Popen") as mock_popen,
            patch("tray.tray_app.threading.Thread") as mock_thread,
        ):
            mock_sys.platform = "win32"
            mock_thread.return_value.start = MagicMock()
            tray._open_settings(MagicMock(), MagicMock())
        mock_popen.assert_not_called()
        mock_thread.assert_called_once()
