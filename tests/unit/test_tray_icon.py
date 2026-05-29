import pytest

from tray.tray_app import _make_icon


class TestMakeIcon:
    @pytest.mark.parametrize("color", ["green", "red", "orange", "grey"])
    def test_icon_mode_is_rgba(self, color):
        img = _make_icon(color)
        assert img.mode == "RGBA", f"Expected RGBA, got {img.mode} for color '{color}'"

    @pytest.mark.parametrize("color", ["green", "red", "orange", "grey"])
    def test_icon_size_is_correct(self, color):
        img = _make_icon(color)
        assert img.size == (64, 64)

    def test_green_icon_is_not_red(self):
        green = _make_icon("green")
        red = _make_icon("red")
        assert green.getpixel((0, 0)) != red.getpixel((0, 0))

    def test_icon_is_fully_opaque(self):
        """Alpha channel must be 255 (fully opaque) for all icon states."""
        for color in ("green", "red", "orange", "grey"):
            img = _make_icon(color)
            _, _, _, alpha = img.getpixel((0, 0))
            assert alpha == 255, f"Expected alpha=255 for '{color}', got {alpha}"
