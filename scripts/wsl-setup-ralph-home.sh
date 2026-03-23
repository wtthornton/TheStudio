#!/usr/bin/env bash
# One-time: ensure ~/.ralph is a git clone of frankbria/ralph-claude-code (WSL).
set -eu
RALPH_HOME="${HOME}/.ralph"
REPO_URL="https://github.com/frankbria/ralph-claude-code.git"

if [[ -d "${RALPH_HOME}/.git" ]]; then
  echo "Ralph home is already a git repo: ${RALPH_HOME}"
  cd "${RALPH_HOME}"
  git pull --ff-only
  git log -1 --oneline
  exit 0
fi

if [[ -d "${RALPH_HOME}" ]]; then
  backup="${RALPH_HOME}.backup.$(date +%Y%m%d%H%M%S)"
  echo "Moving non-git ${RALPH_HOME} -> ${backup}"
  mv "${RALPH_HOME}" "${backup}"
fi

echo "Cloning ${REPO_URL} -> ${RALPH_HOME}"
git clone "${REPO_URL}" "${RALPH_HOME}"
cd "${RALPH_HOME}"
git log -1 --oneline
git remote -v
