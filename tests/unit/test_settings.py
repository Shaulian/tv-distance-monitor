import copy
import json
import sys
from pathlib import Path
from unittest.mock import patch


from config.settings import DEFAULTS, _settings_path, load_settings, save_settings


def _patch_path(p):
    return patch("config.settings._settings_path", return_value=p)


# --- defaults / missing file ---


def test_missing_file_returns_defaults(tmp_path):
    with _patch_path(tmp_path / "settings.json"):
        result = load_settings()
    assert result == copy.deepcopy(DEFAULTS)


def test_missing_file_no_exception(tmp_path):
    with _patch_path(tmp_path / "settings.json"):
        load_settings()  # must not raise


# --- partial file ---


def test_partial_file_fills_missing_keys_from_defaults(tmp_path):
    f = tmp_path / "settings.json"
    f.write_text(json.dumps({"min_safe_distance_m": 2.5}))
    with _patch_path(f):
        result = load_settings()
    assert result["min_safe_distance_m"] == 2.5
    assert result["alert_cooldown_seconds"] == DEFAULTS["alert_cooldown_seconds"]
    assert result["calibration"] == DEFAULTS["calibration"]


# --- unknown keys ---


def test_unknown_keys_are_preserved(tmp_path):
    f = tmp_path / "settings.json"
    f.write_text(json.dumps({"future_feature_flag": True}))
    with _patch_path(f):
        result = load_settings()
    assert result["future_feature_flag"] is True
    assert result["min_safe_distance_m"] == DEFAULTS["min_safe_distance_m"]


# --- invalid JSON ---


def test_invalid_json_returns_defaults(tmp_path):
    f = tmp_path / "settings.json"
    f.write_text("{ not valid json !!!")
    with _patch_path(f):
        result = load_settings()
    assert result == copy.deepcopy(DEFAULTS)


# --- round-trip ---


def test_round_trip_produces_identical_output(tmp_path):
    f = tmp_path / "settings.json"
    with _patch_path(f):
        first = load_settings()
        save_settings(first)
        second = load_settings()
    assert first == second


def test_round_trip_with_modified_values(tmp_path):
    f = tmp_path / "settings.json"
    with _patch_path(f):
        data = load_settings()
        data["min_safe_distance_m"] = 2.0
        data["calibration"]["valid"] = True
        save_settings(data)
        result = load_settings()
    assert result["min_safe_distance_m"] == 2.0
    assert result["calibration"]["valid"] is True


# --- save creates parent directory ---


def test_save_creates_parent_directories(tmp_path):
    f = tmp_path / "nested" / "dir" / "settings.json"
    with _patch_path(f):
        save_settings(copy.deepcopy(DEFAULTS))
    assert f.exists()


# --- settings path ---


def test_settings_path_returns_path_object():
    assert isinstance(_settings_path(), Path)


def test_settings_path_platform_specific():
    p = _settings_path()
    if sys.platform == "win32":
        assert "TVDistanceMonitor" in str(p)
    else:
        assert p == Path.home() / ".TVDistanceMonitor" / "settings.json"
