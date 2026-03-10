#!/bin/bash
# Database backup script for TheStudio production
# Usage: ./backup-db.sh [container_name]
# Backups are stored in ./backups/ with timestamp

set -euo pipefail

CONTAINER="${1:-thestudio-postgres-1}"
BACKUP_DIR="$(dirname "$0")/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/thestudio_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Backing up TheStudio database..."
docker exec "$CONTAINER" pg_dump -U thestudio thestudio | gzip > "$BACKUP_FILE"

echo "Backup saved to: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"

# Keep only last 30 backups
cd "$BACKUP_DIR"
ls -1t thestudio_*.sql.gz 2>/dev/null | tail -n +31 | xargs -r rm
echo "Cleanup complete (kept last 30 backups)."
