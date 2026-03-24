#!/usr/bin/env bash
# Create infra/.env for production with generated secrets.
# Use --mock to run the production stack with mock LLM/GitHub (no real API keys).
#
# Usage:
#   ./setup-prod-env.sh          # Generate secrets; you must set THESTUDIO_ANTHROPIC_API_KEY in .env
#   ./setup-prod-env.sh --mock   # Generate secrets + mock providers (stack runs without real keys)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
MOCK=false

for arg in "$@"; do
    case "$arg" in
        --mock) MOCK=true ;;
        -h|--help)
            echo "Usage: $0 [--mock]"
            echo "  --mock  Use mock LLM/GitHub providers and placeholder API key (stack runs without real keys)"
            exit 0
            ;;
    esac
done

if [ -f "$ENV_FILE" ] && [ "$MOCK" = false ]; then
    echo ".env already exists at $ENV_FILE"
    echo "To regenerate, remove it first or use --mock to create a mock-mode .env."
    exit 0
fi

echo "=== TheStudio production .env setup ==="
echo ""

POSTGRES_PASSWORD="$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")"
THESTUDIO_ENCRYPTION_KEY="$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")"
THESTUDIO_WEBHOOK_SECRET="$(python3 -c "import secrets; print(secrets.token_hex(32))")"
ADMIN_PASSWORD="$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")"
# Generate Caddy bcrypt hash and escape $ for Docker Compose
ADMIN_PASSWORD_HASH="$(docker run --rm caddy:2.9-alpine caddy hash-password --plaintext "$ADMIN_PASSWORD" 2>/dev/null | sed 's/\$/\$\$/g')"

if [ "$MOCK" = true ]; then
    THESTUDIO_ANTHROPIC_API_KEY="sk-mock-placeholder-for-production-stack"
    THESTUDIO_LLM_PROVIDER="mock"
    THESTUDIO_GITHUB_PROVIDER="mock"
    echo "Using mock providers (no real API keys required)."
else
    THESTUDIO_ANTHROPIC_API_KEY=""
    THESTUDIO_LLM_PROVIDER="anthropic"
    THESTUDIO_GITHUB_PROVIDER="real"
    echo "Production mode: set THESTUDIO_ANTHROPIC_API_KEY (and optionally GitHub App) in .env after this script."
fi

cat > "$ENV_FILE" << EOF
# TheStudio Production Environment Variables
# Created by setup-prod-env.sh. Run infra/check-env.sh before deploying.
# For production: docker compose -f docker-compose.prod.yml up -d

# ─── REQUIRED ────────────────────────────────────────────────────────────────
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
THESTUDIO_ENCRYPTION_KEY=$THESTUDIO_ENCRYPTION_KEY
THESTUDIO_ANTHROPIC_API_KEY=$THESTUDIO_ANTHROPIC_API_KEY

# ─── RECOMMENDED ─────────────────────────────────────────────────────────────
THESTUDIO_WEBHOOK_SECRET=$THESTUDIO_WEBHOOK_SECRET
THESTUDIO_GITHUB_APP_ID=
THESTUDIO_GITHUB_PRIVATE_KEY_PATH=

# ─── ADMIN UI AUTH ───────────────────────────────────────────────────────────
# Caddy Basic Auth for /admin/* routes. Password: $ADMIN_PASSWORD
ADMIN_USER=admin
ADMIN_PASSWORD_HASH=$ADMIN_PASSWORD_HASH

# ─── OPTIONAL ────────────────────────────────────────────────────────────────
THESTUDIO_LLM_PROVIDER=$THESTUDIO_LLM_PROVIDER
THESTUDIO_GITHUB_PROVIDER=$THESTUDIO_GITHUB_PROVIDER
# HTTPS: false = HTTP only (default, use http://localhost:9080); true = TLS on 9443
# THESTUDIO_HTTPS_ENABLED=false
# Poll intake (Epic 17 — backup when webhooks unavailable)
# THESTUDIO_INTAKE_POLL_ENABLED=false
# THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES=10
# THESTUDIO_INTAKE_POLL_TOKEN=
# THESTUDIO_OTEL_EXPORTER=console
EOF

echo "Wrote $ENV_FILE"
echo ""
echo "Admin UI credentials:"
echo "  Username: admin"
echo "  Password: $ADMIN_PASSWORD"
echo ""
echo "IMPORTANT: Save this password — it is not recoverable from the hash."
echo ""
echo "After first deploy, seed the admin user in the RBAC table:"
echo "  docker compose -f docker-compose.prod.yml exec postgres \\"
echo "    psql -U thestudio -d thestudio -c \\"
echo "    \"INSERT INTO user_roles (id, user_id, role, created_by) VALUES (gen_random_uuid(), 'admin', 'admin', 'seed') ON CONFLICT (user_id) DO NOTHING;\""
echo ""
if [ "$MOCK" = false ]; then
    echo "Next: edit .env and set THESTUDIO_ANTHROPIC_API_KEY (and GitHub App vars if using real provider)."
fi
echo "Then: ./check-env.sh && docker compose -f docker-compose.prod.yml up -d"
echo ""
