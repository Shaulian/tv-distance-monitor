# ADR-005: Depth Estimation Method

**Date:** 2026-05-28  
**Status:** Accepted  
**Deciders:** Shaul Iantar

---

## Context

We have two USB cameras in a stereo configuration and need to estimate the distance of a detected person from the TV. The cameras are consumer-grade USB webcams, not a calibrated industrial stereo rig.

## Options Considered

### Option A: Disparity-based depth with user calibration (linear fit)
- **Pros:** Works with uncalibrated consumer cameras; user calibration at 4 known points accounts for the specific rig geometry; linear fit is robust and interpretable; no per-frame dense stereo matching (expensive) — just centroid disparity
- **Cons:** Accuracy limited by HOG centroid precision; assumes person is roughly centred in frame; linear fit only valid within the calibration range (~0.5–3m)

### Option B: Dense stereo matching (cv2.StereoBM / StereoSGBM) + depth map
- **Pros:** Per-pixel depth; could detect anyone in the scene
- **Cons:** Requires proper stereo rectification (needs chessboard calibration, not user-standing-at-points); computationally expensive at real-time rates on CPU; consumer webcams with different lenses make rectification unreliable

### Option C: Time-of-Flight / structured-light sensor (Intel RealSense, etc.)
- **Pros:** Highly accurate depth out of the box
- **Cons:** Requires specific hardware; not standard USB webcam; out of scope for this project

### Option D: Bounding box size heuristic (single camera)
- **Pros:** Works with one camera
- **Cons:** Unreliable — bounding box size varies with clothing, posture, and camera angle; not safe for this use case

## Decision

**Chosen:** Option A — centroid disparity with user-calibrated linear fit.

This is the only option that works with two arbitrary consumer USB webcams without a calibration rig. The diamond calibration at 4 known distances gives enough data points for a reliable linear fit in the target range.

## Consequences

- **Positive:** No special hardware; works with any two USB webcams; user calibration is a one-time 2-minute procedure
- **Negative / Trade-offs:** Distance accuracy degrades if person is not facing the cameras (unusual poses); linear fit extrapolated outside the 0.5–3m calibration range is unreliable (warn in UI if distance estimate is outside range)
- **Follow-up required:** ADR-006 (calibration method); distance estimates outside calibration range should be flagged, not silently reported
