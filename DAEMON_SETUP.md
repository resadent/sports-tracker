# Running Sports Tracker as a Background Daemon on Boot

This document explains how Sports Tracker is configured to start automatically in the background on every system boot without requiring interactive login.

---

## Architecture Overview

The system consists of two primary components running headlessly:

1. **Database & Cache (PostgreSQL & Redis):** Managed by Docker with the `restart: unless-stopped` restart policy.
2. **FastAPI Application (Uvicorn):** Managed as a `systemd` user service with **lingering enabled** so it starts at system boot before user login.

---

## 1. Docker Auto-Start Configuration

In [`docker-compose.yml`](docker-compose.yml), both the `db` and `redis` services are set to `restart: unless-stopped`:

```yaml
services:
  db:
    image: postgres:16
    container_name: training_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: training
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7
    container_name: training_redis
    restart: unless-stopped
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

Because the Docker daemon (`docker.service`) is enabled at boot, Docker automatically restores running containers on startup.

---

## 2. Enabling Systemd User Lingering

To allow user-level systemd services to run at boot without an active user session/login:

```bash
loginctl enable-linger
```

You can verify lingering is active with:
```bash
loginctl show-user $USER --property=Linger
# Expected output: Linger=yes
```

---

## 3. Systemd Service Configuration

The service unit is located at:
`~/.config/systemd/user/sports-tracker.service`

```ini
[Unit]
Description=Sports Tracker FastAPI Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/chuwi/sports-tracker
ExecStart=/home/chuwi/sports-tracker/.venv/bin/uvicorn sports_tracker.main:app --host 0.0.0.0 --port 8000 --ssl-certfile /home/chuwi/.config/sports-tracker/certs/cert.pem --ssl-keyfile /home/chuwi/.config/sports-tracker/certs/key.pem
Restart=always
RestartSec=5s
Environment=PYTHONPATH=/home/chuwi/sports-tracker/src
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
```

---

## 4. Enabling & Starting the Service

If modifying the unit file or enabling it for the first time:

```bash
# Reload systemd user manager
systemctl --user daemon-reload

# Enable service at boot and start it immediately
systemctl --user enable --now sports-tracker.service
```

---

## 5. Management Commands

| Action | Command |
| :--- | :--- |
| **Check service status** | `systemctl --user status sports-tracker.service` |
| **View live logs** | `journalctl --user -u sports-tracker.service -f` |
| **Restart service** | `systemctl --user restart sports-tracker.service` |
| **Stop service** | `systemctl --user stop sports-tracker.service` |
| **Disable autostart** | `systemctl --user disable sports-tracker.service` |

---

## 6. Verifying Health

Verify the service is running and properly communicating with PostgreSQL and Redis:

```bash
curl -sk https://127.0.0.1:8000/api/v1/health
```

(`-k` skips certificate verification, which a self-signed certificate always fails.)

Expected response:
```json
{"status":"ok","db":"ok","redis":"ok"}
```

---

## 7. TLS (Self-Signed Certificate)

The daemon serves **HTTPS only** using a self-signed certificate stored in
`~/.config/sports-tracker/certs/` (kept outside the repo so it can never be
committed).

To (re)generate the certificate — e.g. after your public IP or DDNS domain
changes:

```bash
scripts/generate-tls-cert.sh                     # IPs only
scripts/generate-tls-cert.sh myname.duckdns.org  # include DDNS domain
```

The script auto-detects the LAN IP and public IP and puts them (plus
`localhost`, and the domain when given) into the certificate's
`subjectAltName`. Then restart the daemon:

```bash
systemctl --user restart sports-tracker.service
```

Because the certificate is self-signed, browsers will show a one-time
warning (`NET::ERR_CERT_AUTHORITY_INVALID`) — use *Advanced → Proceed* to
continue, or install `cert.pem` as a trusted CA on your devices to remove
the warning. Tools like `curl` need `-k` (or `--cacert ~/.config/sports-tracker/certs/cert.pem`).

Plain `http://` no longer works on port 8000 once TLS is enabled — use
`https://` everywhere, including on the LAN.

---

## 8. (Optional) Celery Worker Daemon

If background task processing with Celery is needed, create `~/.config/systemd/user/sports-tracker-celery.service`:

```ini
[Unit]
Description=Sports Tracker Celery Worker
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/chuwi/sports-tracker
ExecStart=/home/chuwi/sports-tracker/.venv/bin/celery -A sports_tracker.tasks.celery_app worker --loglevel=info
Restart=always
RestartSec=5s
Environment=PYTHONPATH=/home/chuwi/sports-tracker/src

[Install]
WantedBy=default.target
```

Enable and start with:
```bash
systemctl --user enable --now sports-tracker-celery.service
```
