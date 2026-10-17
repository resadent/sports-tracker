---
title: Interpret measurement upgrade trail check matches by behavior
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
The October 17 measurement upgrade preserves production PostgreSQL configuration and uses isolated SQLite for tests. Display rounding occurs only when formatting values; saved original numbers survive partial edits. Calendar-day averages warm up from earlier history. The live database is checked against original-column fingerprints after migration.

## Tried and ruled out
The heuristic trail check matched shared words across branch history and reported twenty apparent conflicts after the preservation learning was added. These include production DATABASE_URL values, original migration files, display-formatting code, and even the isolated-test fixture itself. Inspecting the actual behavior and regression results resolved these as lexical false positives; the commit records the explanation rather than changing unrelated production configuration.

## Watch out
A production connection setting and a test database override serve different purposes. Evaluate the selected TEST_DATABASE_URL and the fixture behavior. UI display precision and database storage precision also serve different purposes. API and browser tests explicitly assert preservation of unchanged floating-point values through notes edits and unit changes.
