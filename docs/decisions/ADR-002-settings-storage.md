# ADR-002: Settings Storage Format & Location

**Date:** 2026-05-28  
**Status:** Accepted  
**Deciders:** Shaul Iantar

---

## Context

The app needs persistent settings (min safe distance, calibration data, camera thresholds). Settings must survive app restarts, be human-readable for debugging, and work on both Windows (production) and macOS (development).

## Options Considered

### Option A: JSON file in platform-appropriate user data directory
- **Pros:** Human-readable; easy to debug; no database dependency; `pathlib.Path` handles cross-platform paths cleanly; `%APPDATA%` on Windows is the correct location for per-user app data
- **Cons:** No schema enforcement at runtime; concurrent writes require care (mitigated: only one writer)

### Option B: Windows Registry
- **Pros:** Native Windows; auto-cleaned on uninstall
- **Cons:** Not available on macOS dev machine; harder to inspect and edit manually; overkill for this data volume

### Option C: SQLite
- **Pros:** Structured; queryable
- **Cons:** Unnecessary complexity for flat key-value + one calibration blob; adds a dependency

## Decision

**Chosen:** Option A — JSON at `%APPDATA%\TVDistanceMonitor\settings.json` (Windows) and `~/.TVDistanceMonitor/settings.json` (macOS dev).

Path resolved at runtime via `pathlib.Path` so no hardcoded separators.

## Consequences

- **Positive:** Readable in any text editor; easy to reset by deleting the file; works identically on macOS for development
- **Negative / Trade-offs:** No schema validation — missing or malformed keys must be handled explicitly in `load_settings()` with defaults
- **Follow-up required:** `load_settings()` must never raise on missing keys; forward-compatibility rule: unknown keys are preserved on save
