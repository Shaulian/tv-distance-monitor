"""Unit tests for the pure helper functions in tray/settings_subprocess.py."""

import pytest

from tray.settings_subprocess import build_save_data, cm_to_m, m_to_cm


class TestConversions:
    def test_cm_to_m_150(self):
        assert cm_to_m(150) == pytest.approx(1.5)

    def test_cm_to_m_50(self):
        assert cm_to_m(50) == pytest.approx(0.5)

    def test_cm_to_m_300(self):
        assert cm_to_m(300) == pytest.approx(3.0)

    def test_m_to_cm_1_5(self):
        assert m_to_cm(1.5) == pytest.approx(150.0)

    def test_m_to_cm_0_5(self):
        assert m_to_cm(0.5) == pytest.approx(50.0)

    def test_round_trip(self):
        assert cm_to_m(m_to_cm(1.23)) == pytest.approx(1.23)


class TestBuildSaveData:
    def test_distance_converted_to_metres(self):
        data = build_save_data(dist_cm=150, interval_ms=100, minor_cm=5.0, sig_cm=20.0)
        assert data["min_safe_distance_m"] == pytest.approx(1.5)

    def test_distance_rounded_to_4dp(self):
        data = build_save_data(dist_cm=133, interval_ms=100, minor_cm=5.0, sig_cm=20.0)
        assert data["min_safe_distance_m"] == pytest.approx(1.33)

    def test_interval_cast_to_int(self):
        data = build_save_data(dist_cm=150, interval_ms=100.9, minor_cm=5.0, sig_cm=20.0)
        assert isinstance(data["frame_capture_interval_ms"], int)
        assert data["frame_capture_interval_ms"] == 100

    def test_drift_thresholds_preserved(self):
        data = build_save_data(dist_cm=150, interval_ms=100, minor_cm=7.5, sig_cm=25.0)
        assert data["drift_threshold_minor_cm"] == pytest.approx(7.5)
        assert data["drift_threshold_significant_cm"] == pytest.approx(25.0)

    def test_all_required_keys_present(self):
        data = build_save_data(dist_cm=150, interval_ms=100, minor_cm=5.0, sig_cm=20.0)
        for key in (
            "min_safe_distance_m",
            "frame_capture_interval_ms",
            "drift_threshold_minor_cm",
            "drift_threshold_significant_cm",
        ):
            assert key in data
