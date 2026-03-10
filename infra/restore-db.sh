#!/usr/bin/env bash
# Restore a TheStudio database backup and verify integrity.
#
# Usage:
#   Host:    ./restore-db.sh <backup_file> [container_name]
#   Sidecar: ./restore-db.sh --sidecar <backup_file>
#
# The backup file should be a .sql.gz produced by backup-db.sh.
# WARNING: This drops and recreates the thestudio database.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <backup_file.sql.gz> [container_name]"
    echo "       $0 --sidecar <backup_file.sql.gz>"
    exit 1
fi

SIDECAR=false
if [ "$1" = "--sidecar" ]; then
    SIDECAR=true
    shift
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "[$(date -Iseconds)] Restoring from: $BACKUP_FILE"

run_sql() {
    if [ "$SIDECAR" = true ]; then
        PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD not set}" \
            psql -h postgres -U thestudio -d postgres "$@"
    else
        local container="${2:-thestudio-postgres-1}"
        docker exec -i "$container" psql -U thestudio -d postgres "$@"
    fi
}

restore_sql() {
    if [ "$SIDECAR" = true ]; then
        PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD not set}" \
            psql -h postgres -U thestudio -d thestudio
    else
        local container="${1:-thestudio-postgres-1}"
        docker exec -i "$container" psql -U thestudio -d thestudio
    fi
}

CONTAINER="${2:-thestudio-postgres-1}"

# Drop and recreate the database
echo "Dropping and recreating thestudio database..."
run_sql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'thestudio' AND pid <> pg_backend_pid();" 2>/dev/null || true
run_sql -c "DROP DATABASE IF EXISTS thestudio;"
run_sql -c "CREATE DATABASE thestudio OWNER thestudio;"

# Restore
echo "Restoring data..."
if [ "$SIDECAR" = true ]; then
    gunzip -c "$BACKUP_FILE" | restore_sql
else
    gunzip -c "$BACKUP_FILE" | restore_sql "$CONTAINER"
fi

# Verify
echo ""
echo "=== Restore Verification ==="

verify_query() {
    local label="$1"
    local query="$2"
    if [ "$SIDECAR" = true ]; then
        local result
        result=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h postgres -U thestudio -d thestudio -t -c "$query" 2>/dev/null | tr -d ' ')
        echo "$label: $result"
    else
        local result
        result=$(docker exec "$CONTAINER" psql -U thestudio -d thestudio -t -c "$query" 2>/dev/null | tr -d ' ')
        echo "$label: $result"
    fi
}

# Check tables exist
verify_query "Tables" "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
verify_query "Repos" "SELECT count(*) FROM repositories;" 2>/dev/null || echo "Repos: table not found (may be expected on fresh install)"

echo ""
echo "[$(date -Iseconds)] Restore complete."
