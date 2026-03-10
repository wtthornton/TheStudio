#!/usr/bin/env bash
# Database backup script for TheStudio production.
# Can be run manually or by the backup sidecar container.
#
# Usage:
#   Host:      ./backup-db.sh [container_name]
#   Sidecar:   ./backup-db.sh --sidecar  (connects via hostname instead of docker exec)

set -euo pipefail

BACKUP_DIR="$(dirname "$0")/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/thestudio_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

echo "[$(date -Iseconds)] Starting backup..."

if [ "${1:-}" = "--sidecar" ]; then
    # Running inside Docker network — connect via hostname
    PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD not set}" \
        pg_dump -h postgres -U thestudio thestudio | gzip > "$BACKUP_FILE"
else
    # Running from host — use docker exec
    CONTAINER="${1:-thestudio-postgres-1}"
    docker exec "$CONTAINER" pg_dump -U thestudio thestudio | gzip > "$BACKUP_FILE"
fi

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[$(date -Iseconds)] Backup saved: $BACKUP_FILE ($SIZE)"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "thestudio_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
REMAINING=$(find "$BACKUP_DIR" -name "thestudio_*.sql.gz" | wc -l)
echo "[$(date -Iseconds)] Retention: removed backups older than ${RETENTION_DAYS} days. ${REMAINING} backups on disk."
