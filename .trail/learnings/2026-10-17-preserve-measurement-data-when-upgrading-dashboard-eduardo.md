---
title: Preserve measurement data when upgrading dashboard
author: Eduardo
date: 2026-10-17
branch: dev
touches:
  - Readme.md
  - pyproject.toml
  - src/sports_tracker/api/v1/endpoints/measurements.py
  - src/sports_tracker/api/v1/endpoints/user_settings.py
  - src/sports_tracker/db/models/measurement.py
  - src/sports_tracker/db/models/user_settings.py
  - src/sports_tracker/db/repositories/measurement_repo.py
  - src/sports_tracker/db/repositories/user_settings_repo.py
  - src/sports_tracker/schemas/measurements.py
  - src/sports_tracker/schemas/user_settings.py
---

## Decided
Before measurement changes, snapshot the full working project and back up PostgreSQL. Keep private data and .env out of GitHub. The 2026-10-17 baseline is tagged snapshot-before-measurement-improvements-20261017. Use additive migrations and verify all original database columns by checksum on a restored rehearsal database and again after deployment. Keep kg/cm storage and existing setting values. Calendar-day averaging replaces the former reading-count calculation; recomp_window is retained but its unsupported score is retired. Preserve the selectable month / last-30-days chart window.

## Tried and ruled out
Do not migrate or round old measurements to implement display units. Send only changed fields in partial edits so notes-only edits preserve numeric precision. Do not connect sparse dates at equal spacing or carry waist averages onto weight-only readings. CSV import previews first, keeps existing dates by default, validates all rows before writes, and never revives deleted entries. Do not use the live training database for pytest; fixtures drop tables. Use in-memory SQLite or a disposable PostgreSQL database.

## Watch out
Deletions are now soft; restore retains IDs and values. Deleted dates are reserved, and the dashboard exposes recoverable entries after reload. Zero legacy values stay stored but are excluded from trends; new zero/non-finite input is rejected. The app currently runs in Docker; check DAEMON_SETUP.md. Sandbox TestClient event-loop hangs require running isolated tests outside the sandbox. Browser regressions launch their own temporary SQLite database and server. Reminders are in-app, not background push.
