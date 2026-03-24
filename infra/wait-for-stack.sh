#!/usr/bin/env bash
# Wait for the TheStudio production stack to become healthy.
# Polls each service health endpoint until all report healthy or timeout.
#
# Usage: ./wait-for-stack.sh [timeout_seconds]
# Exit 0 when all healthy, exit 1 on timeout.

set -euo pipefail

TIMEOUT="${1:-120}"
COMPOSE_FILE="$(dirname "$0")/docker-compose.prod.yml"
INTERVAL=5
ELAPSED=0

echo "Waiting for stack to become healthy (timeout: ${TIMEOUT}s)..."

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Get health status of all services
    UNHEALTHY=$(docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null \
        | grep -v '"temporal-migrations"' \
        | grep -c '"Health":"unhealthy"\|"Health":""' 2>/dev/null || true)

    HEALTHY=$(docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null \
        | grep -v '"temporal-migrations"' \
        | grep -c '"Health":"healthy"' 2>/dev/null || true)

    RUNNING=$(docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null \
        | grep -v '"temporal-migrations"' \
        | grep -c '"State":"running"' 2>/dev/null || true)

    echo "[${ELAPSED}s] Running: $RUNNING | Healthy: $HEALTHY | Unhealthy: $UNHEALTHY"

    # Check individual services
    ALL_READY=true

    # App health (the primary indicator)
    # Default: HTTP on 9080 (THESTUDIO_HTTPS_ENABLED=false). With HTTPS: 9443.
    if curl -sf -o /dev/null http://localhost:9080/healthz 2>/dev/null; then
        echo "  app: healthy (HTTP :9080)"
    elif curl -sf -o /dev/null -k https://localhost:9443/healthz 2>/dev/null; then
        echo "  app: healthy (HTTPS :9443)"
    elif curl -sf -o /dev/null -k https://localhost/healthz 2>/dev/null; then
        echo "  app: healthy (HTTPS :443)"
    elif curl -sf -o /dev/null http://localhost:8000/healthz 2>/dev/null; then
        echo "  app: healthy (direct :8000)"
    else
        echo "  app: not ready"
        ALL_READY=false
    fi

    if [ "$ALL_READY" = true ] && [ "$HEALTHY" -ge 2 ]; then
        echo ""
        echo "Stack is healthy after ${ELAPSED}s."
        docker compose -f "$COMPOSE_FILE" ps
        exit 0
    fi

    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

echo ""
echo "TIMEOUT: Stack did not become healthy within ${TIMEOUT}s."
docker compose -f "$COMPOSE_FILE" ps
docker compose -f "$COMPOSE_FILE" logs --tail=20
exit 1
