# Manual Test Checklist — Windows

Run this checklist on a real Windows 10/11 machine before every release. Check each item and record the date and result.

> **Note (ADR-017):** the CI performance job (`tests/performance/`) measures
> regression-guard budgets on a headless Linux runner with HOG and TTS mocked.
> The real-hardware budgets — 80 ms frame loop, 5 s cold start, 150 MB after
> 30 minutes — can only be validated here. A green CI is **necessary but not
> sufficient**; do not skip this checklist on the basis of "CI passed".

**Release version:** ___________  
**Test date:** ___________  
**Tester:** ___________  
**Windows version:** ___________  
**Hardware:** ___________

---

## 1. Installation & Startup

- [ ] Copy `TVDistanceMonitor.exe` to a clean Windows machine (no Python installed)
- [ ] Double-click `.exe` — Windows SmartScreen warning appears; click "More info → Run Anyway"
- [ ] App starts; tray icon appears in the system tray area (bottom-right taskbar)
- [ ] No error dialogs appear on startup
- [ ] Task Manager shows the process running under 150 MB memory **after 30 minutes of idle monitoring** (strategy budget; see ADR-017)
- [ ] First frame-loop iteration on real hardware (Task Manager / a quick log probe) completes inside the 80 ms strategy budget
- [ ] Cold start from a fresh Windows boot to "tray icon visible, monitoring active" inside the 5 s strategy budget

---

## 2. First Run (Uncalibrated)

- [ ] Tray icon is grey (uncalibrated state)
- [ ] Windows notification appears: "TV Distance Monitor needs calibration. Open Settings."
- [ ] Right-click tray → Status shows "Uncalibrated"
- [ ] Right-click tray → Settings opens a window

---

## 3. Camera Detection

- [ ] Connect both USB cameras before launching (or restart app with both connected)
- [ ] Settings window shows live preview from both cameras side-by-side
- [ ] Both preview feeds are moving (not frozen)
- [ ] Unplug camera 1 mid-preview → right camera preview stops; tray shows degraded state
- [ ] Replug camera 1 → preview resumes within 10 seconds; tray returns to previous state

---

## 4. Calibration Flow

- [ ] Click "Calibrate" in Settings
- [ ] Calibration dialog shows 4-point diamond diagram
- [ ] Stand at Point 1 (centre, ~2m); countdown reaches 0; "✓ Point 1 captured" appears
- [ ] Repeat for Points 2, 3, 4
- [ ] After Point 4: "Step out of frame" prompt appears; step out; reference scene is captured
- [ ] "Calibration complete" message appears
- [ ] Tray icon turns green
- [ ] Settings shows "Calibrated" banner (green)

---

## 5. Distance Alerting

- [ ] After calibration: stand in front of TV at 2m — no alert plays
- [ ] Move to within 1m (below default 1.5m threshold) — alert voice plays within 3 seconds
- [ ] Alert repeats every ~3 seconds while you stay close
- [ ] Move back to 2m — alert stops within one detection cycle (~0.5s)
- [ ] Tray icon shows "Too Close" state when person is within threshold

---

## 6. Settings Adjustments

- [ ] Open Settings; move distance slider to 2.0m; save
- [ ] Stand at 1.5m — alert now triggers (previously safe distance)
- [ ] Change Frame Capture Interval to 200ms; alert response time is noticeably slower
- [ ] "Test Alert" button plays TTS exactly once without starting continuous alerting
- [ ] All changes persist after closing and reopening Settings

---

## 7. Camera Offline Mid-Run

- [ ] With monitoring active: unplug one camera
- [ ] Alerting stops immediately (no distance alerts while camera is offline)
- [ ] Within 5 minutes: audio notification "Camera offline — check the connection" plays
- [ ] Notification repeats every 5 minutes while offline
- [ ] Replug camera — alerting resumes automatically; offline notification stops

---

## 8. Drift Detection

- [ ] Calibrate normally; note tray shows green
- [ ] Quit app; physically nudge one camera slightly (~2cm)
- [ ] Restart app — tray shows green; one-time voice announcement: "Camera position changed — recalibration recommended"
- [ ] Announcement does not repeat during that session
- [ ] Quit app; move camera significantly (~15cm)
- [ ] Restart app — tray shows "Needs Recalibration"; no distance alerting; 5-minute audio notification plays
- [ ] Open Settings → Recalibrate → after recalibration, alerting resumes normally

---

## 9. Autostart (Story 9.2)

- [ ] Check that app is registered for autostart (Settings → "Autostart: Enabled")
- [ ] Restart Windows — app appears in tray without manual launch
- [ ] Right-click tray → "Disable Autostart" → restart Windows → app does NOT autostart

---

## 10. Audio

- [ ] All TTS announcements are audible at normal speaker volume
- [ ] Voice is intelligible (not garbled)
- [ ] No audio output to wrong device (headphones vs. speakers)
- [ ] TTS works in the configured Windows system language

---

## Sign-Off

All items above checked: **YES / NO**  
Known issues carried forward: ___________  
Ready to release: **YES / NO**
