#!/usr/bin/env bash
# PreCompact hook: Back up scoring context before compaction

TAPPS_DIR=".tapps-mcp"
mkdir -p "$TAPPS_DIR"

BACKUP_FILE="$TAPPS_DIR/pre-compact-context.json"
echo "{\"timestamp\": \"$(date -Iseconds)\", \"event\": \"pre-compact\"}" > "$BACKUP_FILE"
echo "TappsMCP context backed up to $BACKUP_FILE"
exit 0
