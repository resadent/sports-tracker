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

## Running tests

Tests run against an isolated **in-memory SQLite** database by default — no Docker or
Postgres needed, and your real database is never touched:

```bash
pytest
```

To run against PostgreSQL instead (e.g. in CI):

```bash
TEST_DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/training pytest
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
| GET | `/health` | DB + Redis health | no |

## License

todo
