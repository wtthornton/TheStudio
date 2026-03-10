#!/usr/bin/env bash
# PostToolUse hook: Detect Python file edits and suggest quality check
FILE=$(echo "$TOOL_INPUT" 2>/dev/null | jq -r '.file_path // .path // empty' 2>/dev/null)

if [ -n "$FILE" ] && echo "$FILE" | grep -q '\.py$'; then
  echo "Python file edited: $FILE"
  echo "Consider running tapps_quick_check(\"$FILE\") for scoring + quality gate + security scan."
fi
exit 0
