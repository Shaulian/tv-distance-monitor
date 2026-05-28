# ADR-009: Windows Packaging (PyInstaller vs. cx_Freeze)

**Date:** 2026-05-28  
**Status:** Accepted  
**Deciders:** Shaul Iantar

---

## Context

The app must be distributed as a single `.exe` that runs on Windows without requiring Python to be installed. We need a Python-to-exe bundler.

## Options Considered

### Option A: PyInstaller (`--onefile`)
- **Pros:** Most widely used; large community; `--onefile` produces a single portable `.exe`; good OpenCV/numpy support; GitHub Actions `windows-latest` runner supports it well; actively maintained
- **Cons:** First-launch slower (extracts to temp on first run); Windows Defender / SmartScreen may flag unsigned executables

### Option B: cx_Freeze
- **Pros:** Produces a directory bundle (faster startup than onefile)
- **Cons:** Smaller community; less documentation for OpenCV; directory bundle is less portable than a single `.exe`; configuration is more complex

### Option C: Nuitka (compiles Python to C)
- **Pros:** Fastest runtime; smaller output
- **Cons:** Compilation time is very long (10–30 min); complex setup; overkill for a tray app

## Decision

**Chosen:** Option A — PyInstaller `--onefile`.

Widest ecosystem support, best OpenCV/pystray integration, and simplest CI integration. Single `.exe` is more user-friendly for distribution. Slow first-launch is acceptable for a background tray app.

## Consequences

- **Positive:** Single-file distribution; straightforward CI pipeline; well-documented workarounds for common issues (hook files for pystray, OpenCV data files)
- **Negative / Trade-offs:** Windows SmartScreen warning on first run for unsigned exe — acceptable for v1; consider code signing in a future release
- **Follow-up required:** Test PyInstaller build on a clean Windows VM with no Python installed; add `--add-data` flags for any asset files (tray icons); document build command in `docs/release-process.md`
