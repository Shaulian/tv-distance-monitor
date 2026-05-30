"""Hypothesis property tests for DepthEstimator.

The hand-written tests in test_depth_estimator.py pin specific inputs.
These property tests assert *invariants* over generated inputs — the
strongest pressure against silently-broken behaviour and the primary
defence against the survivor classes mutation testing flags. They are
particularly load-bearing for the ADR-016 fail-safe contract: if the
contract is ever violated for some unusual input the example-based tests
didn't think of, Hypothesis will find it.

Scope: estimate_distance + assess_proximity. Calibration math has its own
properties in test_stereo_calibration.py (added in a follow-up).
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st

from detection.depth_estimator import DepthEstimator

# Bounded so the random space is meaningful (640×480 frames) and avoids
# pathological floats that pyfit/polyfit doesn't produce in practice.
_cx_strategy = st.integers(min_value=0, max_value=640)
_cy_strategy = st.integers(min_value=0, max_value=480)
_slope_strategy = st.floats(min_value=0.001, max_value=0.5, allow_nan=False, allow_infinity=False)
_intercept_strategy = st.floats(min_value=0.1, max_value=3.0, allow_nan=False, allow_infinity=False)
_min_safe_strategy = st.floats(min_value=0.5, max_value=3.0, allow_nan=False, allow_infinity=False)
_detection_pair_strategy = st.tuples(_cx_strategy, _cy_strategy)


def _det(cx: int, cy: int) -> tuple:
    return (0, 0, 50, 100, int(cx), int(cy))


def _dets(pairs: list) -> list:
    return [_det(cx, cy) for cx, cy in pairs]


# ─── estimate_distance: formula invariant ─────────────────────────────────


@given(
    slope=_slope_strategy,
    intercept=_intercept_strategy,
    cxl=_cx_strategy,
    cxr=_cx_strategy,
)
def test_single_matched_pair_returns_linear_fit(slope, intercept, cxl, cxr):
    """For a single matched pair (same cy), distance must equal
    intercept + slope * (cxl - cxr) exactly."""
    estimator = DepthEstimator({"slope": slope, "intercept": intercept})
    distance = estimator.estimate_distance([_det(cxl, 240)], [_det(cxr, 240)])
    assert distance == pytest.approx(intercept + slope * (cxl - cxr), rel=1e-9)


@given(left=st.lists(_detection_pair_strategy, max_size=5))
def test_empty_right_always_returns_none(left):
    estimator = DepthEstimator({"slope": 0.04, "intercept": 0.5})
    assert estimator.estimate_distance(_dets(left), []) is None


@given(right=st.lists(_detection_pair_strategy, max_size=5))
def test_empty_left_always_returns_none(right):
    estimator = DepthEstimator({"slope": 0.04, "intercept": 0.5})
    assert estimator.estimate_distance([], _dets(right)) is None


# ─── assess_proximity: ADR-016 fail-safe contract ─────────────────────────


@given(min_safe=_min_safe_strategy)
def test_assess_proximity_both_empty_is_no_person(min_safe):
    """Property: with no detections anywhere, assess_proximity returns
    (False, 'no_person'). The only path to a non-alerting verdict."""
    estimator = DepthEstimator({"slope": 0.04, "intercept": 0.5})
    too_close, reason = estimator.assess_proximity([], [], min_safe)
    assert too_close is False
    assert reason == "no_person"


@given(
    left=st.lists(_detection_pair_strategy, min_size=1, max_size=5),
    right=st.lists(_detection_pair_strategy, min_size=1, max_size=5),
    min_safe=_min_safe_strategy,
)
def test_assess_proximity_with_any_detections_is_never_silently_safe(left, right, min_safe):
    """ADR-016 invariant: if at least one camera sees a person, the reason
    is NEVER 'no_person'. The system must either compute distance ('ok')
    or fail-safe ('unmatched' / 'out_of_range') — silence is forbidden."""
    estimator = DepthEstimator({"slope": 0.04, "intercept": 0.5})
    _too_close, reason = estimator.assess_proximity(_dets(left), _dets(right), min_safe)
    assert reason != "no_person"


@given(
    left=st.lists(_detection_pair_strategy, min_size=1, max_size=5),
    min_safe=_min_safe_strategy,
)
def test_assess_proximity_left_only_is_unmatched_fail_safe(left, min_safe):
    """Property: detections only on the left → (True, 'unmatched').
    No matter what the left detections look like, the verdict is loud."""
    estimator = DepthEstimator({"slope": 0.04, "intercept": 0.5})
    too_close, reason = estimator.assess_proximity(_dets(left), [], min_safe)
    assert too_close is True
    assert reason == "unmatched"


@given(
    right=st.lists(_detection_pair_strategy, min_size=1, max_size=5),
    min_safe=_min_safe_strategy,
)
def test_assess_proximity_right_only_is_unmatched_fail_safe(right, min_safe):
    estimator = DepthEstimator({"slope": 0.04, "intercept": 0.5})
    too_close, reason = estimator.assess_proximity([], _dets(right), min_safe)
    assert too_close is True
    assert reason == "unmatched"


@given(
    slope=_slope_strategy,
    intercept=_intercept_strategy,
    cxl=_cx_strategy,
    cxr=_cx_strategy,
    min_safe=_min_safe_strategy,
)
def test_assess_proximity_ok_verdict_is_consistent_with_estimate_distance(
    slope, intercept, cxl, cxr, min_safe
):
    """Property: when reason is 'ok', the boolean verdict matches a direct
    comparison of estimate_distance against min_safe. assess_proximity is
    not allowed to invent its own threshold for the 'ok' case."""
    calibration = {"slope": slope, "intercept": intercept}
    estimator = DepthEstimator(calibration)
    dets_l = [_det(cxl, 240)]
    dets_r = [_det(cxr, 240)]
    too_close, reason = estimator.assess_proximity(dets_l, dets_r, min_safe)

    if reason == "ok":
        distance = estimator.estimate_distance(dets_l, dets_r)
        assert distance is not None
        assert 0 < distance <= 10.0
        assert too_close == (distance < min_safe)


@given(
    slope=_slope_strategy,
    intercept=_intercept_strategy,
    cxl=_cx_strategy,
    cxr=_cx_strategy,
    min_safe=_min_safe_strategy,
)
def test_assess_proximity_fail_safe_reasons_always_say_too_close(
    slope, intercept, cxl, cxr, min_safe
):
    """ADR-016 invariant: any reason other than 'no_person' / 'ok'
    (i.e. the fail-safe reasons) must report too_close=True. There is no
    such thing as a quiet fail-safe."""
    estimator = DepthEstimator({"slope": slope, "intercept": intercept})
    dets_l = [_det(cxl, 240)]
    dets_r = [_det(cxr, 240)]
    too_close, reason = estimator.assess_proximity(dets_l, dets_r, min_safe)
    if reason in {"unmatched", "out_of_range"}:
        assert too_close is True
