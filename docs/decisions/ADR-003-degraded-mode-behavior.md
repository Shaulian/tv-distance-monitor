# ADR-003: Behavior When One Camera Goes Offline

**Date:** 2026-05-28  
**Status:** Accepted  
**Deciders:** Shaul Iantar

---

## Context

The app uses stereo disparity (pixel difference between two cameras) to measure distance. If one camera disconnects mid-run, we must decide whether to continue alerting using the remaining camera or pause alerting entirely.

## Options Considered

### Option A: Pause distance alerting immediately; notify caregiver every 5 minutes
- **Pros:** Safe — a monocular fallback would silently produce inaccurate distances; caregivers would trust wrong data; pausing makes the failure visible
- **Cons:** Monitoring stops until camera is restored; a child could sit too close with no alert during the outage

### Option B: Continue with monocular distance estimation (single camera, bounding-box-size heuristic)
- **Pros:** No monitoring gap
- **Cons:** Bounding-box-based distance is highly unreliable (varies with clothing, posture, camera angle); risk of false "safe" readings; the whole-point of stereo is accuracy

### Option C: Continue alerting at the last known distance until camera reconnects
- **Pros:** No gap in monitoring
- **Cons:** Last distance may be stale by minutes; could alert when child has moved away, or worse, not alert when they've moved closer

## Decision

**Chosen:** Option A — pause distance alerting; play an audio notification every 5 minutes until the camera reconnects.

The safety failure mode of Option B/C (child sits too close with no alert) is worse than the monitoring gap of Option A. A 5-minute audio notification ensures a caregiver notices and intervenes.

## Consequences

- **Positive:** No silent failure; degraded state is audible and obvious
- **Negative / Trade-offs:** Monitoring gap during outage; caregivers must physically reconnect the camera to restore full monitoring
- **Follow-up required:** The 5-minute interval is configurable (`degraded_mode_alert_interval_seconds` in settings); reconnection detection must be automatic (no manual restart required)
