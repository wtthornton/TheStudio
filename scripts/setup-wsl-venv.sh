#!/usr/bin/env bash
# Create a Linux-native venv for WSL (do not use Windows .venv from Bash).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv-wsl ]]; then
  echo "Creating .venv-wsl with $(command -v python3)..."
  python3 -m venv .venv-wsl
fi

# shellcheck source=/dev/null
source .venv-wsl/bin/activate

python -m pip install -U pip
pip install -e ".[dev]"

echo ""
echo "Done. In future sessions run:"
echo "  cd $ROOT && source .venv-wsl/bin/activate"
