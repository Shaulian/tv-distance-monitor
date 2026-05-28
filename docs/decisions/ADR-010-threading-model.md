# ADR-010: Threading Model

**Date:** 2026-05-28  
**Status:** Accepted  
**Deciders:** Shaul Iantar

---

## Context

The app has three concurrent concerns: the tray icon event loop, continuous camera/detection processing, and the audio alert loop. These must coexist without blocking each other.

## Options Considered

### Option A: pystray on main thread; camera and alert on daemon threads
- **Pros:** pystray's documentation explicitly states it must run on the main thread on some platforms (macOS, Windows); daemon threads exit automatically when main thread exits (clean shutdown); straightforward `threading.Thread` usage; shared `AppState` with a `threading.Lock` is simple and transparent
- **Cons:** Python GIL means true parallelism is limited (acceptable: camera read and TTS are I/O-bound, not CPU-bound); manual lock discipline required

### Option B: asyncio event loop
- **Pros:** Modern Python async pattern
- **Cons:** OpenCV's `VideoCapture.read()` is blocking and not async-compatible without a thread executor; pyttsx3 is blocking; mixing asyncio with blocking camera I/O creates complexity without benefit

### Option C: multiprocessing
- **Pros:** True parallelism; no GIL
- **Cons:** Shared state (`AppState`) requires IPC (pipes, queues, shared memory) — far more complex than a simple lock; serialisation overhead; overkill for I/O-bound workloads

## Decision

**Chosen:** Option A — pystray on main thread, daemon threads for camera/detection and alert loops, `threading.Lock` for shared `AppState`.

## Consequences

- **Positive:** Simple mental model; clean shutdown (daemon threads auto-terminate); lock is easy to reason about with only two writer threads
- **Negative / Trade-offs:** Lock must be held for the minimum time possible (read state → release → process → re-acquire to write); long-held locks would stall the alert loop
- **Follow-up required:** Document lock discipline in `AppState` — all reads and writes must use `with app_state_lock:` and must not call blocking functions while holding the lock
