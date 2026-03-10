#!/usr/bin/env bash
# convert-agents.sh — Wrapper for convert-agents.py
# Generates tool-specific agent files from canonical persona source.
# Usage:
#   scripts/convert-agents.sh          # Generate files
#   scripts/convert-agents.sh --check  # Check for drift (exit 1 if out of sync)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python "$SCRIPT_DIR/convert-agents.py" "$@"
