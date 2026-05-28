# ADR-006: Calibration Method (Diamond, 4 Points)

**Date:** 2026-05-28  
**Status:** Accepted  
**Deciders:** Shaul Iantar

---

## Context

To convert pixel disparity to real-world distance we need a calibration curve. The calibration must be doable by a non-technical caregiver at home, with no special equipment.

## Options Considered

### Option A: User stands at 4 known positions (diamond pattern); fit linear curve
- **Pros:** Requires no equipment beyond a tape measure; caregiver-friendly; 4 points spread across the TV viewing area capture spatial variation; linear least-squares fit is well-understood and robust to one noisy capture
- **Cons:** Accuracy depends on user standing at precise points; diamond pattern only covers a 2D slice of the room

### Option B: OpenCV chessboard stereo calibration
- **Pros:** Accurate intrinsic + extrinsic calibration; standard approach
- **Cons:** Requires printing and moving a chessboard; complex procedure; not feasible for home caregivers; assumes stable camera mounting and full stereo rectification

### Option C: Single reference distance (user stands at 1 point)
- **Pros:** Even simpler
- **Cons:** Single-point calibration has no redundancy; cannot fit a curve; spatial variation across the TV area is unaccounted for

## Decision

**Chosen:** Option A — 4-point diamond pattern, linear least-squares fit.

4 points give enough data for a stable linear fit while remaining practical for a non-technical user. The diamond arrangement (centre + 3 corners at the same depth) covers the TV viewing zone.

## Consequences

- **Positive:** Calibration takes ~2 minutes; no equipment required; fit is inspectable (slope/intercept stored in settings)
- **Negative / Trade-offs:** Linear fit assumes depth is roughly linear with disparity in the target range — valid for parallel camera setups; may need a quadratic term if accuracy proves insufficient at extreme distances
- **Follow-up required:** At calibration time, log the R² of the fit; if R² < 0.95, warn the user that calibration quality is low and suggest recalibrating
