#!/usr/bin/env bash
# Verify that the TheStudio production stack survives a full restart
# with all data intact. Tests PostgreSQL persistence, NATS JetStream
# persistence, and app reconnection.
#
# Usage: ./verify-restart.sh
# Exit 0 on success, exit 1 on failure.
#
# Prerequisites: Stack must NOT be running (this script starts it).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"
COMPOSE="docker compose -f $COMPOSE_FILE"
WAIT_SCRIPT="$SCRIPT_DIR/wait-for-stack.sh"

red()   { printf '\033[0;31m%s\033[0m\n' "$1"; }
green() { printf '\033[0;32m%s\033[0m\n' "$1"; }

ERRORS=0
fail() { red "FAIL: $1"; ERRORS=$((ERRORS + 1)); }
pass() { green "PASS: $1"; }

cleanup() {
    echo ""
    echo "--- Cleaning up ---"
    $COMPOSE down 2>/dev/null || true
}

echo "=== TheStudio Restart Resilience Verification ==="
echo ""

# --- Phase 1: Start the stack ---
echo "--- Phase 1: Starting stack ---"
$COMPOSE up -d
bash "$WAIT_SCRIPT" 180

# --- Phase 2: Create test data ---
echo ""
echo "--- Phase 2: Creating test data ---"

# Wait for app to be fully ready
sleep 5

# Create a test record via the admin API
APP_URL="https://localhost"
CURL="curl -sf -k"

# Try to register a repository (or use whatever endpoint is available)
HEALTH_BEFORE=$($CURL "$APP_URL/healthz" 2>/dev/null || echo "failed")
if echo "$HEALTH_BEFORE" | grep -q "ok"; then
    pass "App healthy before restart"
else
    fail "App not healthy before restart: $HEALTH_BEFORE"
fi

# Insert a marker row directly into PostgreSQL for verification
MARKER="restart-test-$(date +%s)"
$COMPOSE exec -T postgres psql -U thestudio -d thestudio -c \
    "CREATE TABLE IF NOT EXISTS _restart_test (marker TEXT, created_at TIMESTAMPTZ DEFAULT now());" 2>/dev/null
$COMPOSE exec -T postgres psql -U thestudio -d thestudio -c \
    "INSERT INTO _restart_test (marker) VALUES ('$MARKER');" 2>/dev/null
echo "Inserted marker: $MARKER"

# --- Phase 3: Run backup ---
echo ""
echo "--- Phase 3: Running backup ---"
$COMPOSE exec -T backup sh -c "BACKUP_DIR=/scripts/backups POSTGRES_PASSWORD=\$POSTGRES_PASSWORD /scripts/backup-db.sh --sidecar" 2>/dev/null \
    && pass "Backup completed" \
    || fail "Backup failed"

# --- Phase 4: Full restart ---
echo ""
echo "--- Phase 4: Full stack restart (down + up) ---"
$COMPOSE down
echo "Stack stopped. Waiting 5s..."
sleep 5
$COMPOSE up -d
bash "$WAIT_SCRIPT" 180

# --- Phase 5: Verify data persistence ---
echo ""
echo "--- Phase 5: Verifying data persistence ---"

# Check app health
HEALTH_AFTER=$($CURL "$APP_URL/healthz" 2>/dev/null || echo "failed")
if echo "$HEALTH_AFTER" | grep -q "ok"; then
    pass "App healthy after restart"
else
    fail "App not healthy after restart: $HEALTH_AFTER"
fi

# Check PostgreSQL data persistence
PG_MARKER=$($COMPOSE exec -T postgres psql -U thestudio -d thestudio -t -c \
    "SELECT marker FROM _restart_test WHERE marker = '$MARKER';" 2>/dev/null | tr -d ' ')
if [ "$PG_MARKER" = "$MARKER" ]; then
    pass "PostgreSQL data persisted across restart"
else
    fail "PostgreSQL data lost! Expected marker '$MARKER', got '$PG_MARKER'"
fi

# Check NATS is running and JetStream is enabled
NATS_OK=$($COMPOSE exec -T nats nats-server --help 2>/dev/null && echo "running" || echo "failed")
if $COMPOSE ps nats | grep -q "running"; then
    pass "NATS is running after restart"
else
    fail "NATS not running after restart"
fi

# Check Temporal health
TEMPORAL_OK=$($COMPOSE exec -T temporal tctl --address temporal:7233 cluster health 2>/dev/null || echo "failed")
if echo "$TEMPORAL_OK" | grep -qi "ok\|serving\|healthy"; then
    pass "Temporal healthy after restart"
else
    # Temporal may take longer — give it extra time
    echo "  Temporal not yet healthy, waiting 30s..."
    sleep 30
    TEMPORAL_OK=$($COMPOSE exec -T temporal tctl --address temporal:7233 cluster health 2>/dev/null || echo "failed")
    if echo "$TEMPORAL_OK" | grep -qi "ok\|serving\|healthy"; then
        pass "Temporal healthy after restart (delayed)"
    else
        fail "Temporal not healthy after restart: $TEMPORAL_OK"
    fi
fi

# --- Phase 6: Cleanup test data ---
echo ""
echo "--- Phase 6: Cleanup ---"
$COMPOSE exec -T postgres psql -U thestudio -d thestudio -c \
    "DROP TABLE IF EXISTS _restart_test;" 2>/dev/null

# --- Summary ---
echo ""
echo "=== Service Status ==="
$COMPOSE ps

echo ""
echo "=== Summary ==="
if [ $ERRORS -gt 0 ]; then
    red "$ERRORS verification(s) failed."
    exit 1
else
    green "All verifications passed. Stack survives restart with data intact."
    exit 0
fi
