# ADR-007: Camera Drift Detection — Method & Thresholds

**Date:** 2026-05-28  
**Status:** Accepted  
**Deciders:** Shaul Iantar

---

## Context

Stereo depth is sensitive to camera position. If a camera is nudged between sessions the calibration is no longer valid. We need a startup check that measures how much a camera has moved and decides whether to continue, warn, or pause alerting.

## Options Considered

### Option A: Phase correlation on full frame (cv2.phaseCorrelate)
- **Pros:** Sub-pixel accuracy; robust to lighting changes (operates in frequency domain); no physical marker required; works on any scene content; built into OpenCV
- **Cons:** Only detects translational shift (not rotation); requires a reasonably textured scene (empty white wall would fail)

### Option B: Feature matching (ORB/SIFT keypoints between reference and current frame)
- **Pros:** Handles rotation and scale; more robust on low-texture scenes
- **Cons:** More complex to implement; slower; requires tuning feature count and match threshold; overkill for detecting a nudge of a mounted camera

### Option C: Require a physical marker (QR code / ArUco) on the wall
- **Pros:** Very precise; explicit reference point
- **Cons:** Requires user to place and keep a marker visible; unfriendly for home installation; marker could be obscured

## Decision

**Chosen:** Option A — `cv2.phaseCorrelate` on full grayscale frames.

Translational shift covers the primary failure mode (camera bumped sideways or up/down on its mount). Rotation is less likely for a mounted camera and is out of scope for v1.

**Thresholds (defaults, configurable in settings):**
- `< 5 cm` error → negligible, no action
- `5–20 cm` error → minor, warn once at startup, continue monitoring
- `> 20 cm` error → significant, pause alerting, require recalibration

Thresholds are expressed as estimated distance error (cm), not raw pixels, so they remain meaningful across different camera resolutions and focal lengths.

## Consequences

- **Positive:** No physical marker needed; works on any real-world scene; configurable thresholds let users tune for their specific setup
- **Negative / Trade-offs:** A completely empty, textureless room could produce unreliable phase correlation results; an empty white wall is an edge case (reference scene should ideally contain some room content)
- **Follow-up required:** At calibration time (reference scene capture), warn the user if the captured frame has very low texture variance (std dev < threshold) — prompt them to ensure some room content is visible
