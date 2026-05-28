# ADR-001: Language, Runtime & Core Tooling

**Date:** 2026-05-28  
**Status:** Accepted  
**Deciders:** Shaul Iantar

---

## Context

We need a language and toolchain for a Windows desktop tray app that: captures USB camera frames, runs image processing, plays TTS audio, and shows a system tray icon. Development happens on macOS; deployment targets Windows.

## Options Considered

### Option A: Python 3.11 + OpenCV + pyttsx3 + pystray
- **Pros:** OpenCV is the industry standard for frame capture and image processing; cross-platform; large community; pyttsx3 works offline; pystray is lightweight for tray apps; pytest ecosystem for testing
- **Cons:** Python packaging for Windows (.exe) requires PyInstaller; startup time slightly slower than compiled languages; GIL limits true parallelism (mitigated by I/O-bound camera threads)

### Option B: C++ / Qt
- **Pros:** Native performance; no packaging overhead; full Windows integration
- **Cons:** Much higher development cost; cross-platform dev/deploy cycle harder; team expertise not available

### Option C: Electron + Node.js
- **Pros:** Easy UI; cross-platform
- **Cons:** No native camera/image-processing ecosystem; 200+ MB runtime overhead for a tray app; overkill

## Decision

**Chosen:** Option A — Python 3.11 with OpenCV, pyttsx3, pystray.

Python 3.11 specifically for improved performance over 3.9/3.10 and better PyInstaller compatibility on Windows.

## Consequences

- **Positive:** Fast development cycle; algorithms testable on macOS before Windows deploy; rich image processing ecosystem
- **Negative / Trade-offs:** PyInstaller packaging must be tested on real Windows; GIL means camera and alert threads share the interpreter (acceptable: both are I/O-bound)
- **Follow-up required:** ADR-009 (packaging), environment setup guide must document Python 3.11 version pinning
