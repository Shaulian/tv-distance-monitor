# ADR-004: Person Detection Approach

**Date:** 2026-05-28  
**Status:** Accepted  
**Deciders:** Shaul Iantar

---

## Context

We need to detect people in camera frames and get their bounding boxes / centroids. The detector runs continuously at ~10 FPS on a Windows machine with no GPU guarantee.

## Options Considered

### Option A: OpenCV HOG + default people detector
- **Pros:** Built into OpenCV (no extra dependency or model file to bundle); works offline; no GPU required; reasonable accuracy for full-body frontal/profile detection at close range (0.5–3m)
- **Cons:** Struggles with partial occlusion; slower than GPU-accelerated models; higher false-negative rate in unusual poses

### Option B: MediaPipe Pose / BlazePose (Google)
- **Pros:** High accuracy; returns skeleton keypoints (could use torso midpoint for better centroid); runs on CPU
- **Cons:** Additional dependency (~50 MB model); slightly higher setup complexity; overkill if we only need a centroid

### Option C: YOLOv8 (Ultralytics)
- **Pros:** State-of-the-art accuracy; fast on modern hardware
- **Cons:** Large model file (6–25 MB); requires `ultralytics` package; likely overkill; slower on CPU-only Windows machines

## Decision

**Chosen:** Option A — OpenCV HOG detector.

At 0.5–3m range with a stationary camera pointing at a TV-watching area, HOG is accurate enough. Zero additional dependencies or model files means simpler packaging and no download on first run. Can be swapped for MediaPipe in a future iteration if false-negative rate is too high in practice.

## Consequences

- **Positive:** No model file to bundle; works on any CPU; no internet required at any point
- **Negative / Trade-offs:** May miss detections in unusual postures (lying down, side-on); not tested yet on the specific camera angles — may need tuning of HOG `winStride` and `padding` parameters
- **Follow-up required:** ADR-004a if HOG proves inadequate during integration testing and we switch to MediaPipe
