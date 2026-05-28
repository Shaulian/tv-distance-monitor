import pytest

from detection.depth_estimator import DepthEstimator

CALIB = {"slope": 0.1, "intercept": 0.5}


def _det(cx, cy):
    """Minimal detection tuple (x, y, w, h, cx, cy)."""
    return (0, 0, 50, 100, cx, cy)


# --- distance formula ---


def test_known_disparity_returns_correct_distance():
    # distance = 0.5 + 0.1 * 50 = 5.5
    dist = DepthEstimator(CALIB).estimate_distance([_det(100, 50)], [_det(50, 50)])
    assert dist == pytest.approx(5.5, rel=0.05)


def test_zero_disparity_returns_intercept():
    dist = DepthEstimator(CALIB).estimate_distance([_det(80, 50)], [_det(80, 50)])
    assert dist == pytest.approx(0.5, rel=0.05)


# --- no match cases ---


def test_no_right_detections_returns_none():
    assert DepthEstimator(CALIB).estimate_distance([_det(100, 50)], []) is None


def test_no_left_detections_returns_none():
    assert DepthEstimator(CALIB).estimate_distance([], [_det(50, 50)]) is None


def test_both_empty_returns_none():
    assert DepthEstimator(CALIB).estimate_distance([], []) is None


# --- vertical threshold ---


def test_vertical_mismatch_beyond_threshold_returns_none():
    # |50 - 71| = 21 > 20 → no match
    assert DepthEstimator(CALIB).estimate_distance([_det(100, 50)], [_det(50, 71)]) is None


def test_vertical_match_exactly_at_threshold():
    # |50 - 70| = 20 ≤ 20 → matches
    dist = DepthEstimator(CALIB).estimate_distance([_det(100, 50)], [_det(50, 70)])
    assert dist is not None


def test_vertical_match_within_threshold():
    dist = DepthEstimator(CALIB).estimate_distance([_det(100, 50)], [_det(50, 55)])
    assert dist is not None


# --- multiple persons ---


def test_multiple_persons_returns_smallest_distance():
    # person A: disparity=50 → dist=5.5
    # person B: disparity=20 → dist=2.5 (closest to TV)
    det_l = [_det(100, 50), _det(200, 150)]
    det_r = [_det(50, 50), _det(180, 150)]
    dist = DepthEstimator(CALIB).estimate_distance(det_l, det_r)
    assert dist == pytest.approx(2.5, rel=0.05)


def test_one_pair_matched_one_unmatched_returns_matched_distance():
    # person A cy=50 matches right cy=52 (within 20); person B cy=50 vs right cy=80 (|30|>20, no match)
    det_l = [_det(100, 50), _det(200, 50)]
    det_r = [_det(50, 52), _det(180, 80)]
    dist = DepthEstimator(CALIB).estimate_distance(det_l, det_r)
    # Only person A matches: disparity=50 → 5.5; person B vs right[0]: |50-52|=2≤20 → also matches
    # person A vs right[0]: |50-52|=2 → dist=5.5
    # person A vs right[1]: |50-80|=30 → no match
    # person B vs right[0]: |50-52|=2 → disparity=200-50=150 → dist=0.5+0.1*150=15.5
    # person B vs right[1]: |50-80|=30 → no match
    # min(5.5, 15.5) = 5.5
    assert dist == pytest.approx(5.5, rel=0.05)
