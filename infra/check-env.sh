#!/usr/bin/env bash
# Pre-flight validation for TheStudio production deployment.
# Checks that all required secrets are set and meet minimum security standards.
#
# Usage: ./check-env.sh [path/to/.env]
# Exit 0 on success, exit 1 on any failure.

set -euo pipefail

ENV_FILE="${1:-$(dirname "$0")/.env}"
ERRORS=0

red()   { printf '\033[0;31m%s\033[0m\n' "$1"; }
green() { printf '\033[0;32m%s\033[0m\n' "$1"; }
warn()  { printf '\033[0;33m%s\033[0m\n' "$1"; }

fail() {
    red "FAIL: $1"
    ERRORS=$((ERRORS + 1))
}

pass() {
    green "OK:   $1"
}

echo "=== TheStudio Pre-Flight Environment Check ==="
echo ""

# Load .env if it exists
if [ -f "$ENV_FILE" ]; then
    echo "Loading: $ENV_FILE"
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
else
    fail ".env file not found at $ENV_FILE"
    echo ""
    echo "Copy infra/.env.example to infra/.env and fill in values."
    exit 1
fi

echo ""

# --- Required variables ---

# POSTGRES_PASSWORD
if [ -z "${POSTGRES_PASSWORD:-}" ]; then
    fail "POSTGRES_PASSWORD is not set"
elif [ "${POSTGRES_PASSWORD}" = "thestudio_dev" ]; then
    fail "POSTGRES_PASSWORD is set to the insecure default 'thestudio_dev'"
elif [ ${#POSTGRES_PASSWORD} -lt 12 ]; then
    fail "POSTGRES_PASSWORD is too short (${#POSTGRES_PASSWORD} chars, minimum 12)"
else
    pass "POSTGRES_PASSWORD is set (${#POSTGRES_PASSWORD} chars)"
fi

# THESTUDIO_ENCRYPTION_KEY
if [ -z "${THESTUDIO_ENCRYPTION_KEY:-}" ]; then
    fail "THESTUDIO_ENCRYPTION_KEY is not set"
elif [ "${THESTUDIO_ENCRYPTION_KEY}" = "hWaGRA3AtIn5jP9TYc3Vu56PS9JQHkFpcekh9PWg7Ac=" ]; then
    fail "THESTUDIO_ENCRYPTION_KEY is set to the insecure dev default"
elif ! echo "${THESTUDIO_ENCRYPTION_KEY}" | base64 -d > /dev/null 2>&1; then
    fail "THESTUDIO_ENCRYPTION_KEY is not valid base64"
else
    pass "THESTUDIO_ENCRYPTION_KEY is set and valid base64"
fi

# THESTUDIO_ANTHROPIC_API_KEY
if [ -z "${THESTUDIO_ANTHROPIC_API_KEY:-}" ]; then
    fail "THESTUDIO_ANTHROPIC_API_KEY is not set"
else
    pass "THESTUDIO_ANTHROPIC_API_KEY is set"
fi

# --- Recommended variables ---

if [ -z "${THESTUDIO_WEBHOOK_SECRET:-}" ]; then
    warn "WARN: THESTUDIO_WEBHOOK_SECRET is not set (webhook signature validation disabled)"
elif [ "${THESTUDIO_WEBHOOK_SECRET}" = "test-webhook-secret" ]; then
    fail "THESTUDIO_WEBHOOK_SECRET is set to the insecure test value"
else
    pass "THESTUDIO_WEBHOOK_SECRET is set"
fi

# --- Known insecure values grep ---

echo ""
echo "--- Checking for known insecure values ---"

INSECURE_FOUND=0
for val in "thestudio_dev" "test-webhook-secret" "hWaGRA3AtIn5jP9TYc3Vu56PS9JQHkFpcekh9PWg7Ac="; do
    if grep -q "$val" "$ENV_FILE" 2>/dev/null; then
        fail "Found insecure value '$val' in $ENV_FILE"
        INSECURE_FOUND=1
    fi
done

if [ $INSECURE_FOUND -eq 0 ]; then
    pass "No known insecure defaults found in .env"
fi

# --- Summary ---

echo ""
echo "=== Summary ==="
if [ $ERRORS -gt 0 ]; then
    red "$ERRORS error(s) found. Fix before deploying."
    exit 1
else
    green "All checks passed. Ready to deploy."
    exit 0
fi
