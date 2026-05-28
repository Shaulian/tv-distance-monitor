import numpy as np
import pytest

from camera.frame_processor import FrameProcessor


def _frame(h, w):
    return np.zeros((h, w, 3), dtype=np.uint8)


# --- same resolution ---


def test_same_resolution_returns_identical_objects():
    frame = _frame(480, 640)
    left_out, right_out = FrameProcessor().process(frame, frame)
    assert left_out is frame
    assert right_out is frame


def test_same_resolution_does_not_alter_shape():
    frame = _frame(480, 640)
    left_out, right_out = FrameProcessor().process(frame, frame)
    assert left_out.shape == (480, 640, 3)


# --- different resolution ---


def test_both_frames_resized_to_smaller_dimensions():
    left_out, right_out = FrameProcessor().process(_frame(480, 640), _frame(720, 1280))
    assert left_out.shape == (480, 640, 3)
    assert right_out.shape == (480, 640, 3)


def test_output_shapes_always_match():
    left_out, right_out = FrameProcessor().process(_frame(480, 640), _frame(600, 800))
    assert left_out.shape == right_out.shape


def test_uses_min_height_and_min_width_independently():
    # left: 400h×640w, right: 480h×320w → target: 400h×320w
    left_out, right_out = FrameProcessor().process(_frame(400, 640), _frame(480, 320))
    assert left_out.shape[:2] == (400, 320)
    assert right_out.shape[:2] == (400, 320)


def test_frame_already_at_target_size_not_copied():
    # left is already at the target (min) size; only right should be resized
    left = _frame(480, 640)
    left_out, _ = FrameProcessor().process(left, _frame(720, 1280))
    assert left_out is left


def test_larger_frame_is_downsampled_not_upsampled():
    left_out, right_out = FrameProcessor().process(_frame(480, 640), _frame(240, 320))
    assert left_out.shape[:2] == (240, 320)
    assert right_out.shape[:2] == (240, 320)
