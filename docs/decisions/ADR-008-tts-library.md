# ADR-008: Text-to-Speech Library

**Date:** 2026-05-28  
**Status:** Accepted  
**Deciders:** Shaul Iantar

---

## Context

The app plays voice announcements (distance alerts, camera-offline warnings, drift warnings). The TTS solution must work on Windows in a home environment without internet.

## Options Considered

### Option A: pyttsx3 (offline, system TTS)
- **Pros:** Fully offline; lightweight; wraps Windows SAPI5 (native Windows voices); no API key; no internet dependency; simple API (`engine.say()`)
- **Cons:** Voice quality depends on Windows-installed voices (may sound robotic); voice availability varies by Windows language/region; known issues with some Python versions on macOS

### Option B: Google Cloud Text-to-Speech
- **Pros:** High-quality, natural-sounding voices
- **Cons:** Requires internet; requires API key and billing; latency (network round-trip) before each alert; unacceptable for a real-time safety alert

### Option C: Pre-recorded audio files (pydub / playsound)
- **Pros:** Perfect audio quality; offline; no TTS latency
- **Cons:** Fixed set of messages — cannot vary alert text dynamically; must ship audio files with the app; adding new messages requires re-recording

## Decision

**Chosen:** Option A — pyttsx3.

Offline operation is a hard requirement (home network not guaranteed; alerts must work during an outage). Alert messages are short and functional — voice quality is not a priority. The custom distance value in "Please move back — you are X metres from the TV" requires dynamic TTS.

## Consequences

- **Positive:** Zero latency; works with no internet; no ongoing cost; alert message is customisable by user
- **Negative / Trade-offs:** Must test available voices on the target Windows machine before release; pyttsx3's `runAndWait()` blocks the calling thread — AlertManager must call it on its own thread (already the case in our threading model)
- **Follow-up required:** Manual test checklist must include verifying TTS voice and volume on Windows; Settings window should expose a "Test Alert" button
