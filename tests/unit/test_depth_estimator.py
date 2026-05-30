import pytest

from detection.depth_estimator import DepthEstimator

CALIB = {"slope": 0.1, "intercept": 0.5}

# Calibration tuned for assess_proximity bound tests:
#   distance = intercept + slope * disparity
#   slope=0.04, intercept=0.5 → disparity 50 → 2.5 m, disparity 0 → 0.5 m,
#   disparity 250 → 10.5 m (just past the 10.0 m sanity ceiling).
PROX_CALIB = {"slope": 0.04, "intercept": 0.5}
MIN_SAFE = 1.5  # m


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


# --- assess_proximity (ADR-016 fail-safe degradation contract) ---


def test_assess_proximity_no_detections_anywhere_returns_no_person_safe():
    too_close, reason = DepthEstimator(PROX_CALIB).assess_proximity([], [], MIN_SAFE)
    assert too_close is False
    assert reason == "no_person"


def test_assess_proximity_left_only_detection_returns_unmatched_fail_safe():
    # Right camera missed the person → cannot compute distance → fail loud, not silent.
    too_close, reason = DepthEstimator(PROX_CALIB).assess_proximity([_det(200, 100)], [], MIN_SAFE)
    assert too_close is True
    assert reason == "unmatched"


def test_assess_proximity_right_only_detection_returns_unmatched_fail_safe():
    too_close, reason = DepthEstimator(PROX_CALIB).assess_proximity([], [_det(150, 100)], MIN_SAFE)
    assert too_close is True
    assert reason == "unmatched"


def test_assess_proximity_vertical_mismatch_returns_unmatched_fail_safe():
    # Both cameras see a person but vertical centres differ >20 px (cy 50 vs 100)
    # → estimate_distance returns None → fail-safe True.
    too_close, reason = DepthEstimator(PROX_CALIB).assess_proximity(
        [_det(200, 50)], [_det(150, 100)], MIN_SAFE
    )
    assert too_close is True
    assert reason == "unmatched"


def test_assess_proximity_safe_distance_returns_false_ok():
    # disparity 50 → distance 0.5 + 0.04 * 50 = 2.5 m → 2.5 > 1.5 → safe.
    too_close, reason = DepthEstimator(PROX_CALIB).assess_proximity(
        [_det(200, 100)], [_det(150, 100)], MIN_SAFE
    )
    assert too_close is False
    assert reason == "ok"


def test_assess_proximity_close_distance_returns_true_ok():
    # disparity 10 → distance 0.5 + 0.04 * 10 = 0.9 m → 0.9 < 1.5 → too close.
    too_close, reason = DepthEstimator(PROX_CALIB).assess_proximity(
        [_det(160, 100)], [_det(150, 100)], MIN_SAFE
    )
    assert too_close is True
    assert reason == "ok"


def test_assess_proximity_exactly_min_safe_distance_is_not_too_close():
    # Choose disparity so distance == MIN_SAFE exactly: 0.5 + 0.04 * 25 = 1.5.
    # Strict `<` means "exactly at the safety boundary" is reported as safe,
    # matching the historical semantics in main._camera_loop.
    too_close, reason = DepthEstimator(PROX_CALIB).assess_proximity(
        [_det(175, 100)], [_det(150, 100)], MIN_SAFE
    )
    assert too_close is False
    assert reason == "ok"


def test_assess_proximity_negative_distance_returns_out_of_range_fail_safe():
    # Right cx > left cx → negative disparity → distance < 0 (physically impossible).
    # disparity -50 → distance 0.5 + 0.04 * -50 = -1.5 m.
    too_close, reason = DepthEstimator(PROX_CALIB).assess_proximity(
        [_det(100, 100)], [_det(150, 100)], MIN_SAFE
    )
    assert too_close is True
    assert reason == "out_of_range"


def test_assess_proximity_zero_distance_returns_out_of_range_fail_safe():
    # Tuned so distance lands exactly at 0.0: slope 0.04, intercept 0.5 →
    # disparity must satisfy 0.5 + 0.04 * d = 0 → d = -12.5 (rounded -13 for ints).
    # Easier: use a different intercept-zero scenario via a custom calibration.
    calib = {"slope": 0.04, "intercept": 0.0}
    too_close, reason = DepthEstimator(calib).assess_proximity(
        [_det(150, 100)], [_det(150, 100)], MIN_SAFE
    )
    assert too_close is True
    assert reason == "out_of_range"


def test_assess_proximity_at_max_plausible_distance_is_ok():
    # disparity 237.5 ≈ 238 → distance 0.5 + 0.04 * 238 = 10.02 m, just over.
    # Pick disparity 237 → distance = 0.5 + 0.04 * 237 = 9.98 m, within the 10 m ceiling.
    too_close, reason = DepthEstimator(PROX_CALIB).assess_proximity(
        [_det(387, 100)], [_det(150, 100)], MIN_SAFE
    )
    assert too_close is False
    assert reason == "ok"


def test_assess_proximity_beyond_max_plausible_distance_returns_out_of_range_fail_safe():
    # disparity 1000 → distance 0.5 + 0.04 * 1000 = 40.5 m → out of sanity range.
    too_close, reason = DepthEstimator(PROX_CALIB).assess_proximity(
        [_det(1150, 100)], [_det(150, 100)], MIN_SAFE
    )
    assert too_close is True
    assert reason == "out_of_range"


# Boundary tests added during WS5 mutmut triage — kill mutants that flip
# the sanity-ceiling constant (10.0 → 11.0) or its comparison (> → >=).


def test_assess_proximity_exactly_at_10_metres_is_ok_not_out_of_range():
    # Distance == 10.0 m exactly. Strict `> 10.0` keeps it inside the
    # plausible range; a mutation to `>= 10.0` would flip this to
    # out_of_range, and this assertion fails that mutation.
    # disparity 237.5 → 0.5 + 0.04 * 237.5 = 10.0
    # Round to disparity 237.5 isn't expressible as ints; use a different
    # calibration to land cleanly on 10.0:  slope=0.05, intercept=0.0,
    # disparity=200 → distance=10.0.
    calib = {"slope": 0.05, "intercept": 0.0}
    too_close, reason = DepthEstimator(calib).assess_proximity(
        [_det(350, 100)], [_det(150, 100)], MIN_SAFE
    )
    assert reason == "ok"
    assert too_close is False  # 10 > 1.5 safe


def test_assess_proximity_just_past_10_metres_is_out_of_range():
    # Distance 10.5 m → strictly past the sanity ceiling. A mutation that
    # raises the constant from 10.0 to 11.0 would mis-classify this as
    # "ok"; this assertion fails that mutation.
    # slope=0.05, intercept=0.0, disparity=210 → 10.5 m
    calib = {"slope": 0.05, "intercept": 0.0}
    too_close, reason = DepthEstimator(calib).assess_proximity(
        [_det(360, 100)], [_det(150, 100)], MIN_SAFE
    )
    assert reason == "out_of_range"
    assert too_close is True
