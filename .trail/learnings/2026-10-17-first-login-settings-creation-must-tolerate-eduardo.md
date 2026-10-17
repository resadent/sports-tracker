---
title: First-login settings creation must tolerate concurrent requests
author: Eduardo
date: 2026-10-17
branch: dev
touches:
  - src/sports_tracker/db/repositories/user_settings_repo.py
  - ".gemini/settings.json"
  - backups/.gitkeep
  - opencode.json
  - tests/api/test_08_settings_concurrency.py
---

## Decided
UserSettingsRepository.get_or_create handles a unique-constraint collision by rolling back and loading the settings row created by the other request. A new dashboard loads settings and measurement series concurrently; both endpoints call get_or_create.

## Tried and ruled out
An intermittent initial dashboard timeout looked like a chart-library load problem. Preview-server logs identified UNIQUE constraint failed: user_settings.user_id. A real concurrent-session regression test reproduces two missing-row reads before inserts and verifies one shared resulting row.

## Watch out
Browser tests with previously used accounts hide this race because their settings rows already exist. The standalone browser test creates a fresh temporary database and account each time. If rollback is followed by no matching settings row, re-raise the original database error instead of hiding it.
