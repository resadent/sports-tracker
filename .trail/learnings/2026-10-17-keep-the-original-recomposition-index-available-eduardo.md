---
title: Keep the original recomposition index available
author: Eduardo
date: 2026-10-17
branch: dev
touches:
  - MEASUREMENT_UPGRADE.md
  - src/sports_tracker/api/v1/endpoints/measurements.py
  - src/sports_tracker/schemas/measurements.py
  - src/sports_tracker/static/js/dashboard.js
  - tests/api/test_03_measurements_api.py
  - tests/browser/check_measurement_dashboard.py
  - ".gemini/settings.json"
  - backups/.gitkeep
  - opencode.json
---

## Decided
The user explicitly requested restoring the recomposition index after the dashboard upgrade. Restore the original formula: 100 times (current weight / weight N readings earlier minus current waist / waist N readings earlier), rounded to two decimals. Keep the saved recomp_window value and its request override. Label the lookback as readings, since each metric counts its own recorded values. Add its own chart using the same month / last-30-days selection. Calendar-day moving averages and matched-date comparisons remain available.

## Tried and ruled out
Retiring the original recomposition index during the upgrade was reversed at the user's request. This supersedes the retirement decision in the October 17 preservation learning. Showing calendar days for this original reading-count lookback would mislabel its behavior.

## Watch out
No stored data or setting values need migration. Missing metrics, insufficient history or a zero baseline produce no index; keep original zero records untouched. Compute history before filtering the output so a date-range query retains its baselines. Regression tests restore the snapshot's original recomposition expectations and cover sparse dates, saved settings, overrides and zero baselines.
