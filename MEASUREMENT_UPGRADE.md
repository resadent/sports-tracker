# Measurement dashboard upgrade

The pre-change project is tagged on GitHub as
`snapshot-before-measurement-improvements-20261017` (commit `cf639dc`).
A private local project archive and PostgreSQL SQL/custom backups are in
`backups/`, dated 20261017. Database backups and environment files are not
published to GitHub.

## Preserving existing data

Migration `a5b6c7d8e9f5` only adds nullable context/deletion columns and preference
columns with defaults. It does not rewrite measurements, dates, IDs, timestamps,
accounts, workouts, or existing averaging settings. The database stays in kg/cm.
Display-unit changes do not convert stored values; partial edits send only changed
fields, preserving the precision of untouched measurements.

Before deployment, the backup was restored into a separate PostgreSQL database and
upgraded. Checksums of every original column in users, settings, muscles, exercises,
exercise associations, sessions, workout sets and measurements matched the original
baseline. The baseline includes 41 measurements. Local checksums are stored in
`backups/data_fingerprint_before_measurements_20261017.json`.

To verify that baseline again (later intentional edits will produce differences):

```bash
PYTHONPATH=src .venv/bin/python scripts/data_fingerprint.py --verify backups/data_fingerprint_before_measurements_20261017.json
```

For a future upgrade, use `--record backups/new-baseline.json` before the migration.
The command only reads database rows and writes a private checksum manifest.

## Dashboard behavior

- The month / last-30-days dropdown remains the chart window selector.
- Weight and waist have separate charts sharing the same date bounds. Dates are
  spaced by elapsed time, and missing measurements remain missing. Raw lines break
  across gaps greater than 7 days; average lines break across gaps greater than the
  configured averaging window.
- Averages use calendar days, including the measurement date. A 7-day average on
  October 17 includes available readings dated October 11–17. Each metric is
  averaged independently. Filtering the API response warms up from earlier history.
- Summaries show the latest entry as of the window end, its date, a recent average
  with its reading count, and change between the first and last readings in the
  selected period. Joint comparisons use two dates with both metrics recorded.
- The original recomposition index is restored in its own chart, with its saved
  recomp_window setting. Its lookback counts previous readings independently for
  weight and waist, so baseline dates can differ. The index uses the original
  formula, 100 × (weight / earlier weight − waist / earlier waist). Missing or zero
  baseline values produce no index. Calendar-day averages remain unchanged.
- Legacy zero measurements remain visible in history, but are excluded from
  averages and comparisons. New values must be finite and greater than zero.
- Logging a change greater than 10% from the existing or previous reading asks for
  confirmation. This is a typo check, not a health threshold.
- Notes are optional. Two to five repeat waist readings are retained individually;
  their mean, rounded to two decimal places in cm, becomes the waist value.
- Selecting an existing date loads its values. Edit also allows correcting its date;
  a date already occupied by another entry cannot be overwritten through correction.
- Deletion hides the record while preserving its ID and values. Use Undo or Deleted
  entries to restore it, including after reloading. A deleted date must be restored
  before logging onto it again.
- Unit and reminder preferences belong to the signed-in account. Reminders are
  shown when the dashboard is opened; 0 disables each reminder. There are no
  background push notifications.
- Chart.js 4.5.1 is bundled locally with its MIT license so charts load without CDN
  access. No additional runtime Python dependencies were introduced.

## CSV import/export

Exports include the complete active measurement history in canonical kg/cm,
including notes and individual repeat readings. The API returns `{csv_text: ...}`;
use the dashboard Export CSV button for a download.

Import accepts these columns:

| Column | Format |
| --- | --- |
| date | Required, YYYY-MM-DD |
| weight_kg or weight_lb | Optional positive finite number; only one unit per row |
| waist_cm or waist_in | Optional positive finite number; only one unit per row |
| notes | Optional, up to 1000 characters |
| waist_readings | Optional, 2–5 cm values separated by `|` |

At least one measurement is required for each imported row. Repeat readings imply
waist_cm; if both are supplied, the waist value must agree with their mean.

Preview is the default and changes nothing. Existing dates are kept by default.
Selecting Update supplied fields explicitly allows changes on existing dates;
omitted or blank numeric cells leave existing values unchanged. A supplied blank
notes cell clears notes. Deleted entries are always skipped. Duplicate dates within
a file and invalid rows reject the complete file before any writes. Limits are
1 MB and 5000 rows. Old zero values can be exported for reference but must be
corrected before importing them as new measurements.

## Verification

Run the isolated API suite:

```bash
TEST_DATABASE_URL=sqlite:// .venv/bin/pytest -q
```

Run the browser regression check with the optional `browser-test` dependencies:

```bash
python tests/browser/check_measurement_dashboard.py
```

The browser check always launches a separate server and temporary SQLite database.
It verifies precision preservation through edits and unit changes, repeat readings,
date correction, deletion/restore (including after reload), reminders, CSV preview
and import/export, chart dates, and mobile layout. Screenshots go to
`/tmp/sports-tracker-browser-artifacts/` by default.
