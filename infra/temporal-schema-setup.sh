#!/usr/bin/env bash
# Idempotent Temporal schema setup/migration for PostgreSQL.
#
# Usage: ./temporal-schema-setup.sh
#
# Runs temporal-sql-tool to create the Temporal database and apply
# schema migrations. Safe to run multiple times — setup-schema and
# update-schema are idempotent.
#
# Requires: docker compose stack with postgres running.
# Alternatively, runs the temporal-migrations service directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.prod.yml"
COMPOSE="docker compose -f $COMPOSE_FILE"

echo "=== Temporal Schema Setup ==="
echo ""

# Ensure postgres is running
if ! $COMPOSE ps postgres | grep -q "running"; then
    echo "Starting postgres..."
    $COMPOSE up -d postgres
    echo "Waiting for postgres healthcheck..."
    sleep 10
fi

# Run the temporal-migrations service (one-shot container)
echo "Running temporal-migrations service..."
$COMPOSE run --rm temporal-migrations

echo ""
echo "Temporal schema setup complete."
echo "You can now start the Temporal server:"
echo "  $COMPOSE up -d temporal"
