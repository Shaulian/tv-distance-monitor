# Release Process

Follow these steps in order for every release. Do not skip steps.

---

## 1. Verify All Stories Are Done

- All stories targeted for this release have every AC ticked in `docs/epics-and-stories.md`
- `main` branch CI is green

---

## 2. Run the Security Checklist

Complete `docs/security-checklist.md`. All items must pass before proceeding.

---

## 3. Run the Manual Test Checklist

Complete `docs/manual-test-checklist.md` on real Windows hardware.  
Record the date, tester name, and Windows version in the checklist.  
All items must pass. Known issues must be documented and accepted explicitly.

---

## 4. Update the CHANGELOG

In `CHANGELOG.md`:
- Add a new section under `## [Unreleased]` with today's date and the version number
- List all changes under the correct headers: `Added`, `Changed`, `Fixed`, `Removed`
- Move the `[Unreleased]` heading above the new version section

Example:
```markdown
## [1.1.0] — 2026-06-15
### Added
- Frame Capture Interval slider in Settings (Story 2.3)
### Fixed
- Camera reconnection no longer requires app restart (Story 2.2)
```

---

## 5. Bump the Version

The version lives in `main.py` as `__version__ = "X.Y.Z"` and in `pyinstaller.spec` (if used).  
Follow semantic versioning:
- **Patch (Z):** Bug fix, no new features
- **Minor (Y):** New feature, backwards-compatible
- **Major (X):** Breaking change to calibration format, settings schema, or behaviour

---

## 6. Commit & Tag

```bash
git add CHANGELOG.md main.py
git commit -m "Release vX.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

The tag push triggers the CI `build-windows-exe` job automatically. Monitor it on GitHub Actions.

---

## 7. Attach Release Notes on GitHub

Once the CI build completes and attaches the `.exe`:
- Go to GitHub → Releases → the new tag
- Paste the CHANGELOG section for this version as the release description
- Verify the `.exe` artifact is attached

---

## 8. Record the Build

In a comment on the GitHub Release (or a release log doc), record:
- Git commit SHA the `.exe` was built from
- Date and time of CI build
- Windows runner version (shown in the Actions log)

---

## Post-Release

- Check for any issues filed in the first 48 hours after distribution
- If a critical bug is found: patch release (bump Z), fix on `main`, re-run from Step 1
- Schedule a post-implementation review if this was a major release
