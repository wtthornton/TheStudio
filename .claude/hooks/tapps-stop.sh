#!/usr/bin/env bash
# Stop hook: Show cached validation status and remind about final validation

TAPPS_DIR=".tapps-mcp"

# Check for cached validation results
if [ -f "$TAPPS_DIR/.validation-progress.json" ]; then
  FILE_COUNT=$(jq -r '.file_count // "unknown"' "$TAPPS_DIR/.validation-progress.json" 2>/dev/null)
  STATUS=$(jq -r '.status // "unknown"' "$TAPPS_DIR/.validation-progress.json" 2>/dev/null)
  echo "Last validation: $FILE_COUNT files, status: $STATUS"
fi

echo "Reminder: Run tapps_validate_changed() before ending the session to ensure all edits pass quality gates."
exit 0
