#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
REPO_ROOT="$(dirname "${SCRIPT_DIR}")"

# Default configuration
DB_HOST="${POSTGRES_HOST:-127.0.0.1}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
DB_NAME="${POSTGRES_DB:-training}"
CONTAINER_NAME="${DOCKER_CONTAINER:-training_postgres}"
ASSUME_YES=false
BACKUP_FILE=""

# Parse .env if available
ENV_FILE="${REPO_ROOT}/.env"
if [[ -f "${ENV_FILE}" ]]; then
    DB_URL=$(grep -E '^DATABASE_URL=' "${ENV_FILE}" | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
    if [[ -n "${DB_URL}" ]]; then
        CLEAN_URL="${DB_URL#*://}"
        if [[ "${CLEAN_URL}" =~ ^([^:]+):([^@]+)@([^:/]+)(:([0-9]+))?/(.+)$ ]]; then
            DB_USER="${BASH_REMATCH[1]}"
            DB_PASSWORD="${BASH_REMATCH[2]}"
            DB_HOST="${BASH_REMATCH[3]}"
            DB_PORT="${BASH_REMATCH[5]:-5432}"
            DB_NAME="${BASH_REMATCH[6]}"
        fi
    fi
fi

print_help() {
    cat <<EOF
Usage: $(basename "$0") <BACKUP_FILE> [OPTIONS]

Options:
  -y, --yes                     Skip confirmation prompt
  -d, --database <DB>           Target database name (default: ${DB_NAME})
  -h, --host <HOST>             Database host (default: ${DB_HOST})
  -p, --port <PORT>             Database port (default: ${DB_PORT})
  -U, --user <USER>             Database user (default: ${DB_USER})
  --help                        Display this help message

Examples:
  $(basename "$0") backups/training_backup_20260910.sql
  $(basename "$0") backups/training_backup_20260910.dump -y
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -y|--yes)
            ASSUME_YES=true
            shift
            ;;
        -d|--database)
            DB_NAME="$2"
            shift 2
            ;;
        -h|--host)
            DB_HOST="$2"
            shift 2
            ;;
        -p|--port)
            DB_PORT="$2"
            shift 2
            ;;
        -U|--user)
            DB_USER="$2"
            shift 2
            ;;
        --help)
            print_help
            exit 0
            ;;
        *)
            if [[ -z "${BACKUP_FILE}" ]]; then
                BACKUP_FILE="$1"
                shift
            else
                echo "Unknown option: $1" >&2
                print_help
                exit 1
            fi
            ;;
    esac
done

if [[ -z "${BACKUP_FILE}" ]]; then
    echo "[-] Error: No backup file specified." >&2
    print_help
    exit 1
fi

if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "[-] Error: Backup file '${BACKUP_FILE}' not found." >&2
    exit 1
fi

echo "========================================================="
echo " Restoring Database"
echo " File:     ${BACKUP_FILE}"
echo " Target:   ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "========================================================="

if [[ "${ASSUME_YES}" != "true" ]]; then
    read -r -p "WARNING: Restoring will overwrite existing data in '${DB_NAME}'. Continue? [y/N] " response
    case "${response}" in
        [yY][eE][sS]|[yY])
            ;;
        *)
            echo "Restore aborted by user."
            exit 0
            ;;
    esac
fi

HAS_LOCAL_TOOLS=false
if command -v psql >/dev/null 2>&1; then
    HAS_LOCAL_TOOLS=true
fi

if [[ "${HAS_LOCAL_TOOLS}" == "true" ]]; then
    echo "==> Restoring using local PostgreSQL client tools..."

    if [[ "${BACKUP_FILE}" == *.dump ]]; then
        PGPASSWORD="${DB_PASSWORD}" pg_restore \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            --clean \
            --if-exists \
            --no-owner \
            --no-privileges \
            "${BACKUP_FILE}" || true
    else
        PGPASSWORD="${DB_PASSWORD}" psql \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            -v ON_ERROR_STOP=1 \
            -f "${BACKUP_FILE}"
    fi

elif command -v docker >/dev/null 2>&1 && docker ps >/dev/null 2>&1; then
    echo "==> Restoring using docker exec on container '${CONTAINER_NAME}'..."

    if [[ "${BACKUP_FILE}" == *.dump ]]; then
        cat "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" pg_restore \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            --clean \
            --if-exists \
            --no-owner \
            --no-privileges || true
    else
        cat "${BACKUP_FILE}" | docker exec -i "${CONTAINER_NAME}" psql \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            -v ON_ERROR_STOP=1
    fi
else
    echo "[-] Error: Neither local psql/pg_restore nor accessible docker command found." >&2
    exit 1
fi

echo "==> Restore completed successfully!"
