#!/usr/bin/env bash
# PreToolUse hook: Block writes to protected files
FILE=$(echo "$TOOL_INPUT" 2>/dev/null | jq -r '.file_path // .path // empty' 2>/dev/null)

if [ -z "$FILE" ]; then
  exit 0
fi

PROTECTED=".env .env.local .env.production .env.staging"
BASENAME=$(basename "$FILE")

for p in $PROTECTED; do
  if [ "$BASENAME" = "$p" ]; then
    echo "BLOCKED: Cannot edit protected file: $FILE" >&2
    exit 2
  fi
done

# Block credentials/secrets files
if echo "$FILE" | grep -qE '(credentials|secrets|\.ssh)'; then
  echo "BLOCKED: Cannot edit sensitive file: $FILE" >&2
  exit 2
fi

exit 0
