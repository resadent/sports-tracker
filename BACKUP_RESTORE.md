# Database Backup & Restore Guide

This guide provides instructions on how to back up and restore the PostgreSQL database used by **Sports Tracker**.

---

## 1. Overview & Current Backup

The Sports Tracker database runs on **PostgreSQL 16** (container `training_postgres` exposed on `127.0.0.1:5432`).

### Database Details
- **Database Name:** `training`
- **Default User:** `postgres`
- **Default Password:** `postgres` (or as configured in `.env`)
- **Default Host / Port:** `127.0.0.1:5432`

### Current Backup Files
A fresh backup has already been generated in the [`backups/`](backups/) directory:

| File | Format | Description |
| --- | --- | --- |
| [`backups/training_backup_20260910_000748.sql`](backups/training_backup_20260910_000748.sql) | Plain SQL (`.sql`) | Full schema + data dump with clean DROP IF EXISTS statements |
| [`backups/training_backup_20260910_000748.dump`](backups/training_backup_20260910_000748.dump) | Custom PostgreSQL (`.dump`) | Compressed PostgreSQL custom archive |
| [`backups/training_backup_latest.sql`](backups/training_backup_latest.sql) | Symlink | Points to the most recent SQL backup |
| [`backups/training_backup_latest.dump`](backups/training_backup_latest.dump) | Symlink | Points to the most recent custom dump |

The backup includes all tables and relationships:
- `users` (user accounts & bcrypt password hashes)
- `user_settings` (user moving average & recomp configuration)
- `muscles` (muscle groups catalog)
- `exercises` (exercise library)
- `exercise_muscle` (exercise-to-muscle relations)
- `sessions` (logged workout sessions)
- `workout_sets` (individual sets, reps, weights, types)
- `measurements` (body measurements & history)
- `alembic_version` (schema migration state)

---

## 2. Quick Start: Using Automated Scripts

Automated scripts are provided in [`scripts/`](scripts/) to simplify backup and restore operations. Both scripts automatically read connection details from `.env` if present.

### Creating a Backup

Run [`scripts/backup.sh`](scripts/backup.sh):
```bash
./scripts/backup.sh
```

#### Options:
- `-f, --format <all|sql|dump>`: Choose output format (default: `all`)
- `-o, --output-dir <DIR>`: Custom destination directory (default: `backups/`)
- `-d, --database <DB>`: Custom database name (default: `training`)
- `-h, --host <HOST>`: Database host (default: `127.0.0.1`)
- `-p, --port <PORT>`: Database port (default: `5432`)
- `-U, --user <USER>`: Database user (default: `postgres`)

**Example:**
```bash
# Create only a compressed .dump file
./scripts/backup.sh -f dump

# Save to a specific folder
./scripts/backup.sh -o /path/to/my_backups
```

### Restoring a Backup

Run [`scripts/restore.sh`](scripts/restore.sh) passing the backup file:
```bash
./scripts/restore.sh backups/training_backup_latest.sql
```

The script will ask for confirmation before applying changes. To bypass the prompt (e.g. in automated workflows), pass `-y`:
```bash
./scripts/restore.sh backups/training_backup_latest.sql -y
```

You can also restore into a different database for testing:
```bash
./scripts/restore.sh backups/training_backup_latest.sql -d training_test -y
```

---

## 3. Manual Backup Instructions

If you prefer to run native PostgreSQL or Docker commands directly, use the instructions below.

### Method A: Using Local PostgreSQL Client (`pg_dump`)

> **Note:** Client binaries (`pg_dump`, `psql`, `pg_restore`) are installed in `~/.local/bin/` which is in `$PATH`.

#### Plain SQL Format:
```bash
PGPASSWORD="postgres" pg_dump \
  -h 127.0.0.1 \
  -p 5432 \
  -U postgres \
  -d training \
  --clean \
  --if-exists \
  -F p \
  -f backups/training_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Compressed Custom Dump Format:
```bash
PGPASSWORD="postgres" pg_dump \
  -h 127.0.0.1 \
  -p 5432 \
  -U postgres \
  -d training \
  -F c \
  -f backups/training_backup_$(date +%Y%m%d_%H%M%S).dump
```

### Method B: Using Docker (`docker exec`)

If you prefer running commands directly through the Docker container:

#### Plain SQL:
```bash
docker exec -t training_postgres pg_dump \
  -U postgres \
  -d training \
  --clean \
  --if-exists > backups/training_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Compressed Custom Dump:
```bash
docker exec training_postgres pg_dump \
  -U postgres \
  -d training \
  -F c > backups/training_backup_$(date +%Y%m%d_%H%M%S).dump
```

---

## 4. Manual Restore Instructions

### Method A: Using Local PostgreSQL Client (`psql` / `pg_restore`)

#### 1. Restoring a Plain SQL file (`.sql`):
```bash
PGPASSWORD="postgres" psql \
  -h 127.0.0.1 \
  -p 5432 \
  -U postgres \
  -d training \
  -v ON_ERROR_STOP=1 \
  -f backups/training_backup_latest.sql
```

#### 2. Restoring a Custom Dump file (`.dump`):
```bash
PGPASSWORD="postgres" pg_restore \
  -h 127.0.0.1 \
  -p 5432 \
  -U postgres \
  -d training \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  backups/training_backup_latest.dump
```

#### 3. Restoring into a Clean / New Database:
To test the backup without touching the active `training` database:
```bash
# 1. Create a fresh database
PGPASSWORD="postgres" psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -c "CREATE DATABASE training_test;"

# 2. Restore into the test database
PGPASSWORD="postgres" psql -h 127.0.0.1 -p 5432 -U postgres -d training_test -f backups/training_backup_latest.sql

# 3. Verify data
PGPASSWORD="postgres" psql -h 127.0.0.1 -p 5432 -U postgres -d training_test -c "SELECT count(*) FROM users;"

# 4. Clean up after testing
PGPASSWORD="postgres" psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -c "DROP DATABASE training_test;"
```

### Method B: Using Docker (`docker exec`)

#### Restoring Plain SQL:
```bash
cat backups/training_backup_latest.sql | docker exec -i training_postgres psql -U postgres -d training
```

#### Restoring Custom Dump:
```bash
cat backups/training_backup_latest.dump | docker exec -i training_postgres pg_restore -U postgres -d training --clean --if-exists --no-owner --no-privileges
```

---

## 5. Verification After Restore

To verify that the database has been successfully restored, run:

1. **Check Table Row Counts:**
   ```bash
   .venv/bin/python3 -c "
   import psycopg
   conn = psycopg.connect('postgresql://postgres:postgres@127.0.0.1:5432/training')
   with conn.cursor() as cur:
       for t in ['users', 'user_settings', 'muscles', 'exercises', 'exercise_muscle', 'sessions', 'measurements']:
           cur.execute(f'SELECT count(*) FROM \"{t}\";')
           print(f'{t}: {cur.fetchone()[0]} rows')
   conn.close()
   "
   ```

2. **Verify API Health:**
   ```bash
   curl -s http://127.0.0.1:8000/api/v1/health | jq .
   ```
   Expected response:
   ```json
   {
     "status": "ok",
     "db": "healthy",
     "redis": "healthy"
   }
   ```

---

## 6. Automating Scheduled Backups (Cron)

To set up an automatic daily backup at 02:00 AM:

1. Open crontab:
   ```bash
   crontab -e
   ```
2. Add the following entry:
   ```cron
   0 2 * * * /home/chuwi/sports-tracker/scripts/backup.sh >> /home/chuwi/sports-tracker/backups/backup.log 2>&1
   ```
3. Optional: Automatically clean up backups older than 30 days:
   ```cron
   0 3 * * * find /home/chuwi/sports-tracker/backups -type f \( -name "*.sql" -o -name "*.dump" \) -mtime +30 -delete
   ```
