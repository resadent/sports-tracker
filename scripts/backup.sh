#!/usr/bin/env bash
set -euo pipefail

# Script directory and repository root
SCRIPT_DIR="$(dirname "$(realpath "${BASH_SOURCE[0]}")")"
REPO_ROOT="$(dirname "${SCRIPT_DIR}")"
BACKUP_DIR="${REPO_ROOT}/backups"

# Default configuration
DB_HOST="${POSTGRES_HOST:-127.0.0.1}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
DB_NAME="${POSTGRES_DB:-training}"
CONTAINER_NAME="${DOCKER_CONTAINER:-training_postgres}"
FORMAT="${BACKUP_FORMAT:-all}" # sql, dump, or all

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

# Allow CLI override arguments
print_help() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  -f, --format <all|sql|dump>   Backup format (default: all)
  -o, --output-dir <DIR>        Destination directory (default: ./backups)
  -d, --database <DB>           Database name (default: ${DB_NAME})
  -h, --host <HOST>             Database host (default: ${DB_HOST})
  -p, --port <PORT>             Database port (default: ${DB_PORT})
  -U, --user <USER>             Database user (default: ${DB_USER})
  --help                        Display this help message
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--format)
            FORMAT="$2"
            shift 2
            ;;
        -o|--output-dir)
            BACKUP_DIR="$2"
            shift 2
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
            echo "Unknown option: $1" >&2
            print_help
            exit 1
            ;;
    esac
done

mkdir -p "${BACKUP_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BASE_NAME="${DB_NAME}_backup_${TIMESTAMP}"

echo "==> Starting backup of database '${DB_NAME}'..."

# Determine method: host pg_dump or docker exec
HAS_PG_DUMP=false
if command -v pg_dump >/dev/null 2>&1; then
    HAS_PG_DUMP=true
fi

if [[ "${HAS_PG_DUMP}" == "true" ]]; then
    echo "==> Using local pg_dump tool"

    if [[ "${FORMAT}" == "all" || "${FORMAT}" == "sql" ]]; then
        SQL_FILE="${BACKUP_DIR}/${BASE_NAME}.sql"
        PGPASSWORD="${DB_PASSWORD}" pg_dump \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            --clean \
            --if-exists \
            -F p \
            -f "${SQL_FILE}"
        # Strip transaction_timeout if dumped from newer pg_dump against pg 16
        sed -i '/transaction_timeout/d' "${SQL_FILE}" 2>/dev/null || true
        echo "  [+] SQL backup created: ${SQL_FILE} ($(du -h "${SQL_FILE}" | cut -f1))"
    fi

    if [[ "${FORMAT}" == "all" || "${FORMAT}" == "dump" ]]; then
        DUMP_FILE="${BACKUP_DIR}/${BASE_NAME}.dump"
        PGPASSWORD="${DB_PASSWORD}" pg_dump \
            -h "${DB_HOST}" \
            -p "${DB_PORT}" \
            -U "${DB_USER}" \
            -d "${DB_NAME}" \
            -F c \
            -f "${DUMP_FILE}"
        echo "  [+] Custom dump created: ${DUMP_FILE} ($(du -h "${DUMP_FILE}" | cut -f1))"
    fi

elif command -v docker >/dev/null 2>&1 && docker ps >/dev/null 2>&1; then
    echo "==> Using docker exec on container '${CONTAINER_NAME}'"

    if [[ "${FORMAT}" == "all" || "${FORMAT}" == "sql" ]]; then
        SQL_FILE="${BACKUP_DIR}/${BASE_NAME}.sql"
        docker exec -t "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" --clean --if-exists > "${SQL_FILE}"
        sed -i '/transaction_timeout/d' "${SQL_FILE}" 2>/dev/null || true
        echo "  [+] SQL backup created: ${SQL_FILE} ($(du -h "${SQL_FILE}" | cut -f1))"
    fi

    if [[ "${FORMAT}" == "all" || "${FORMAT}" == "dump" ]]; then
        DUMP_FILE="${BACKUP_DIR}/${BASE_NAME}.dump"
        docker exec "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" -F c > "${DUMP_FILE}"
        echo "  [+] Custom dump created: ${DUMP_FILE} ($(du -h "${DUMP_FILE}" | cut -f1))"
    fi
else
    echo "[-] Error: Neither local pg_dump nor accessible docker command found." >&2
    exit 1
fi

echo "==> Backup completed successfully!"
