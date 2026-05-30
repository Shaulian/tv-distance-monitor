import numpy as np
from unittest.mock import MagicMock

from detection.person_detector import PersonDetector

BLANK = np.zeros((480, 640, 3), dtype=np.uint8)
FAKE_BOX = np.array([[100, 50, 64, 128]])  # x, y, w, h


def _make_detector_with_mock_hog(boxes=FAKE_BOX):
    detector = PersonDetector.__new__(PersonDetector)
    detector._hog = MagicMock()
    detector._hog.detectMultiScale.return_value = (boxes, None)
    detector._frame_count = 0
    detector._last_result = []
    return detector


# --- return format ---


def test_detect_returns_list():
    detector = _make_detector_with_mock_hog()
    result = detector.detect(BLANK)
    assert isinstance(result, list)


def test_detect_returns_empty_list_not_none_when_no_person():
    detector = _make_detector_with_mock_hog(boxes=np.empty((0, 4), dtype=int))
    result = detector.detect(BLANK)
    assert result == []


def test_detect_result_tuples_have_six_elements():
    detector = _make_detector_with_mock_hog()
    result = detector.detect(BLANK)
    assert len(result) == 1
    assert len(result[0]) == 6


def test_detect_centroid_is_centre_of_bounding_box():
    # box: x=100, y=50, w=64, h=128 → cx=132, cy=114
    detector = _make_detector_with_mock_hog(FAKE_BOX)
    x, y, w, h, cx, cy = detector.detect(BLANK)[0]
    assert x == 100
    assert y == 50
    assert w == 64
    assert h == 128
    assert cx == 100 + 64 // 2
    assert cy == 50 + 128 // 2


# --- blank frame ---


def test_blank_frame_returns_empty_list():
    # HOG produces no detections on an all-zero frame
    result = PersonDetector().detect(BLANK)
    assert result == []


# --- frame skipping (every 3rd frame processed) ---


def test_first_call_processes_frame():
    detector = _make_detector_with_mock_hog()
    detector.detect(BLANK)
    detector._hog.detectMultiScale.assert_called_once()


def test_first_call_processes_frame_with_real_constructor():
    # WS5 mutmut catch: _make_detector_with_mock_hog above bypasses __init__
    # via __new__, so it cannot detect a mutation in __init__ that flips
    # _frame_count to a non-zero start (which would silently skip the first
    # frame). This test uses the regular constructor and patches _hog
    # afterwards so the contract "first call always processes" is enforced
    # against the real __init__.
    detector = PersonDetector()
    detector._hog = MagicMock()
    detector._hog.detectMultiScale.return_value = (FAKE_BOX, None)
    result = detector.detect(BLANK)
    detector._hog.detectMultiScale.assert_called_once()
    assert len(result) == 1  # the patched box was actually returned, not the empty cache


def test_second_and_third_calls_are_skipped():
    detector = _make_detector_with_mock_hog()
    detector.detect(BLANK)  # call 1: processed
    detector.detect(BLANK)  # call 2: skipped
    detector.detect(BLANK)  # call 3: skipped
    assert detector._hog.detectMultiScale.call_count == 1


def test_fourth_call_processes_again():
    detector = _make_detector_with_mock_hog()
    for _ in range(4):
        detector.detect(BLANK)
    assert detector._hog.detectMultiScale.call_count == 2


def test_skipped_frames_return_cached_result():
    detector = _make_detector_with_mock_hog()
    result_1 = detector.detect(BLANK)  # processed
    result_2 = detector.detect(BLANK)  # skipped → returns cache
    result_3 = detector.detect(BLANK)  # skipped → returns cache
    assert result_2 == result_1
    assert result_3 == result_1


def test_skipped_frame_before_first_detection_returns_empty():
    # If somehow detect() is called before any frame is processed (shouldn't
    # happen since frame 0 is always processed), cache starts as [].
    detector = PersonDetector.__new__(PersonDetector)
    detector._hog = MagicMock()
    detector._hog.detectMultiScale.return_value = (FAKE_BOX, None)
    detector._frame_count = 1  # artificially skip first-frame processing
    detector._last_result = []
    result = detector.detect(BLANK)
    assert result == []
