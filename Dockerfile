# syntax=docker/dockerfile:1

# ---- Stage 1: install third-party deps into a self-contained directory ----
# python:3.13-slim is Debian trixie, matching the glibc of the distroless runtime below.
FROM python:3.13-slim-trixie AS deps
WORKDIR /build
COPY pyproject.toml ./
# Runtime deps come from pyproject.toml; requirements.txt is a full venv freeze
# (it includes pytest and psycopg2, which the app does not use).
RUN pip install --no-cache-dir --target=/deps \
    $(python -c "import tomllib; print(*tomllib.load(open('pyproject.toml','rb'))['project']['dependencies'])")

# ---- Stage 2: distroless Debian 13 runtime (no shell, no pip, non-root) ----
FROM gcr.io/distroless/python3-debian13:nonroot
WORKDIR /app
COPY --from=deps /deps /deps
COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src
ENV PYTHONPATH=/deps:/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
# distroless ENTRYPOINT is ["/usr/bin/python3"]; compose services append their args.
