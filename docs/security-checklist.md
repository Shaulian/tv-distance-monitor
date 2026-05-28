# Security Checklist

Review this checklist before every release. Each item describes a check and the risk it guards against.

---

## File System & Data

- [ ] Settings file (`settings.json`) contains no sensitive data — calibration numbers and distances are not secrets, but verify no credentials or PII are ever written
- [ ] Reference scene images (`reference_cam0.png`, `reference_cam1.png`) are stored in `%APPDATA%` (user-private directory), not a public or shared location
- [ ] The app does not write to any directory outside `%APPDATA%\TVDistanceMonitor\` and the temp dir (PyInstaller extraction on first run)
- [ ] `settings.json` file permissions are not world-readable (Windows: verify `%APPDATA%` ACL; default is user-only, which is correct)

---

## Camera Access

- [ ] Camera frames are never transmitted over a network — all processing is local
- [ ] Camera frames are not written to disk (no implicit frame logging or debug dumps in production builds)
- [ ] The app does not access any camera index beyond 0 and 1 (no inadvertent access to a built-in laptop camera on Windows)

---

## Audio

- [ ] The app only plays pre-defined TTS messages — user-controlled alert message content is set via Settings UI, not injectable from outside the app
- [ ] No microphone access is requested (output only)

---

## Network

- [ ] The app makes no outbound network connections in normal operation
- [ ] pyttsx3 is confirmed offline (no network calls) — verify by running with firewall rule blocking the process
- [ ] No telemetry, analytics, or update-check calls are present in the code

---

## Code & Dependencies

- [ ] `requirements.txt` uses pinned versions — no floating `>=` without an upper bound for packages that run at runtime
- [ ] Run `pip audit` before each release to check for known CVEs in dependencies:
  ```bash
  pip install pip-audit
  pip-audit -r requirements.txt
  ```
- [ ] No `eval()`, `exec()`, or `subprocess` calls with user-controlled input
- [ ] No `pickle` for settings storage (use JSON — pickle is unsafe for untrusted data)

---

## Windows-Specific

- [ ] The app does not request or require administrator (elevated) privileges — it runs as the current user
- [ ] Registry writes (autostart) are to `HKCU` (current user), not `HKLM` (machine-wide, requires admin)
- [ ] The `.exe` does not embed a manifest requesting UAC elevation

---

## Distribution

- [ ] The `.exe` is built from a clean, reviewed commit on `main` — not from a local dirty working tree
- [ ] Build hash / git tag is recorded alongside the distributed `.exe` so the source of any binary can be traced
- [ ] If code signing is added in future: sign with a certificate stored outside the repo (never commit private keys)
