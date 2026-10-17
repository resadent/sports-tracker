# Sports Tracker

A FastAPI application to track daily sports activities: log exercises, sessions and
workout sets, and monitor progress over time.

## Features

- User registration and login (bcrypt password hashing, JWT access tokens)
- Exercise catalog with the muscles each exercise trains (many-to-many)
- Training sessions with nested workout sets (reps / weight)
- Modify or delete individual workout sets; delete whole sessions
- Per-user data isolation (sessions and sets are only visible to their owner)
- Health check endpoint (DB + Redis)
- Alembic migrations and idempotent seed data

## Tech stack

- Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic
- PostgreSQL (dev/prod), SQLite (tests by default)
- Redis + Celery (optional, for background tasks)
- PyJWT + bcrypt for authentication

## Getting started

### 1. Start the database (PostgreSQL + Redis)

Requires Docker:

```bash
docker compose up -d db redis
```

### 2. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # or: uv pip install -e ".[dev]"
```

### 3. Configure environment

```bash
cp .env.example .env
```

The defaults in `src/sports_tracker/settings/settings.py` work out of the box with
`docker compose` (Postgres on `127.0.0.1:5432`, Redis on `6379`).

### 4. Create the schema and seed data

```bash
alembic upgrade head
python -m sports_tracker.db.seed_data
```

### 5. Run the API

```bash
uvicorn sports_tracker.main:app --reload
```

Interactive docs: http://127.0.0.1:8000/docs

## Deployment (Docker)

The whole stack runs in `docker compose`. The app image is built in two stages: deps
are pip-installed into a self-contained directory in a `python:3.13-slim` builder, and
the runtime is **distroless Debian 13** (`gcr.io/distroless/python3-debian13:nonroot` —
Python 3.13, no shell, no pip, non-root user).

```bash
sudo docker compose build      # build the sports-tracker image
sudo docker compose up -d      # db, redis, migrations (one-shot), then the app
```

- `db` keeps its existing `postgres_data` volume, so data is preserved across rebuilds.
- The app reads the host `.env` (`env_file`), but `DATABASE_URL` / `REDIS_URL` are
  overridden to point at the compose network (`db:5432`, `redis:6379`).
- Logs: `sudo docker compose logs -f app`
- One-off commands (e.g. a Celery worker, if you add tasks):
  `sudo docker compose run --rm app -m celery -A sports_tracker.tasks.celery_app worker --loglevel=info`
- To debug the image there is no shell for: switch the app image to
  `gcr.io/distroless/python3-debian13:debug-nonroot` in a scratch Dockerfile.

If you previously ran the app as the `sports-tracker.service` systemd user daemon,
disable it so port 8000 is free: `systemctl --user disable --now sports-tracker.service`
(see [DAEMON_SETUP.md](DAEMON_SETUP.md) for the legacy setup).

## Running tests

Tests run against an isolated **in-memory SQLite** database by default — no Docker or
Postgres needed, and your real database is never touched:

```bash
pytest
```

To run against PostgreSQL instead, use a dedicated disposable test database. The test fixture drops and recreates its tables; never point it at your live database:

```bash
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/training_test pytest
```

Browser regression checks create a temporary SQLite database and a separate server:

```bash
uv pip install -e '.[dev,browser-test]'
# Uses local Chrome/Chromium if installed; otherwise install Playwright Chromium:
python -m playwright install chromium
python tests/browser/check_measurement_dashboard.py
```

See [Measurement upgrade](MEASUREMENT_UPGRADE.md) for the dashboard behavior and preservation checks.

## Database Backup & Restore

To back up or restore the PostgreSQL database, see the complete guide in [BACKUP_RESTORE.md](BACKUP_RESTORE.md).

Quick commands:
```bash
# Create a backup (outputs .sql and .dump to ./backups/)
./scripts/backup.sh

# Restore from a backup file
./scripts/restore.sh backups/training_backup_latest.sql
```

## API overview (all under `/api/v1`)

| Method | Path | Description | Auth |
| --- | --- | --- | --- |
| POST | `/users` | Register a user | no |
| POST | `/auth/login` | Get a bearer token (OAuth2 form) | no |
| GET | `/users/me` | Current user | yes |
| GET | `/exercises` | List exercises (with muscles) | yes |
| POST | `/exercises` | Create an exercise (optionally with `muscle_ids`) | yes |
| GET | `/muscles` | List muscles | yes |
| POST | `/sessions` | Create a session with nested `workout_sets` | yes |
| GET | `/sessions` | List own sessions | yes |
| GET | `/sessions/{id}` | Session detail | yes |
| DELETE | `/sessions/{id}` | Delete session (cascades to sets) | yes |
| PATCH | `/sessions/{id}/workout-sets/{set_id}` | Update a set (reps/weight) | yes |
| DELETE | `/sessions/{id}/workout-sets/{set_id}` | Delete a set | yes |
| GET | `/measurements` | Own active measurement history | yes |
| POST | `/measurements` | Add or update measurements for a date | yes |
| GET | `/measurements/series` | Calendar-day averages and reading counts | yes |
| PATCH | `/measurements/{id}` | Correct date, metrics, notes or repeats | yes |
| DELETE | `/measurements/{id}` | Reversibly delete an entry | yes |
| GET | `/measurements/deleted` | Own recoverable deleted entries | yes |
| POST | `/measurements/{id}/restore` | Restore a deleted entry | yes |
| GET | `/measurements/export` | CSV in a JSON csv_text field (kg/cm) | yes |
| POST | `/measurements/import` | Preview/import CSV; keep existing dates by default | yes |
| GET / PATCH | `/settings` | Averages, units and in-app reminders | yes |
| GET | `/health` | DB + Redis health | no |

## License

todo
