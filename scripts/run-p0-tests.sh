#!/usr/bin/env bash
# scripts/run-p0-tests.sh — P0 Deployment Test Harness
#
# Single script to run all P0 tests against the deployed Docker stack.
# Sources credentials from infra/.env, validates stack health, runs all
# test suites, and saves structured results to docs/eval-results/.
#
# Usage:
#   ./scripts/run-p0-tests.sh              # Run all P0 suites
#   ./scripts/run-p0-tests.sh --skip-eval  # Skip eval suite (saves ~$5)
#   ./scripts/run-p0-tests.sh --health     # Health check only
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Colours (if terminal supports them)
# ---------------------------------------------------------------------------
if [[ -t 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; NC=''
fi
info()  { echo -e "${GREEN}[P0]${NC} $*"; }
warn()  { echo -e "${YELLOW}[P0]${NC} $*"; }
fail()  { echo -e "${RED}[P0]${NC} $*"; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
SKIP_EVAL=false
HEALTH_ONLY=false
for arg in "$@"; do
    case "$arg" in
        --skip-eval) SKIP_EVAL=true ;;
        --health)    HEALTH_ONLY=true ;;
        --help|-h)
            echo "Usage: $0 [--skip-eval] [--health] [--help]"
            echo "  --skip-eval  Skip eval suite (saves ~\$5 in API calls)"
            echo "  --health     Run health check only, then exit"
            exit 0 ;;
        *) fail "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# 1. Source credentials from infra/.env
# ---------------------------------------------------------------------------
info "Sourcing credentials from infra/.env..."
if [[ ! -f infra/.env ]]; then
    fail "infra/.env not found. Run infra/setup-prod-env.sh first."
    exit 1
fi
set -a
# shellcheck disable=SC1091
source infra/.env
set +a

# Get GitHub token from gh CLI (not stored in .env)
if command -v gh &>/dev/null; then
    THESTUDIO_GITHUB_TOKEN="$(gh auth token 2>/dev/null || true)"
    export THESTUDIO_GITHUB_TOKEN
fi
export THESTUDIO_GITHUB_TEST_REPO="${THESTUDIO_GITHUB_TEST_REPO:-wtthornton/thestudio-production-test-rig}"

# ---------------------------------------------------------------------------
# 2. Validate credentials (not empty, not placeholder)
# ---------------------------------------------------------------------------
info "Validating credentials..."
CRED_OK=true

if [[ -z "${THESTUDIO_ANTHROPIC_API_KEY:-}" ]]; then
    fail "THESTUDIO_ANTHROPIC_API_KEY is empty"
    CRED_OK=false
elif [[ ! "${THESTUDIO_ANTHROPIC_API_KEY}" == sk-ant-* ]]; then
    fail "THESTUDIO_ANTHROPIC_API_KEY does not start with sk-ant- (placeholder?)"
    CRED_OK=false
fi

if [[ -z "${THESTUDIO_GITHUB_TOKEN:-}" ]]; then
    warn "THESTUDIO_GITHUB_TOKEN is empty (GitHub integration tests will fail)"
fi

if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
    fail "POSTGRES_PASSWORD is empty"
    CRED_OK=false
elif [[ "${POSTGRES_PASSWORD}" == "thestudio_dev" ]]; then
    fail "POSTGRES_PASSWORD is the dev placeholder 'thestudio_dev' — use a real password"
    CRED_OK=false
fi

if [[ -z "${ADMIN_USER:-}" ]]; then
    fail "ADMIN_USER is empty"
    CRED_OK=false
fi

if [[ -z "${ADMIN_PASSWORD:-}" ]]; then
    fail "ADMIN_PASSWORD is empty (needed for admin API tests)"
    CRED_OK=false
fi

if [[ -z "${THESTUDIO_WEBHOOK_SECRET:-}" ]]; then
    fail "THESTUDIO_WEBHOOK_SECRET is empty (needed for webhook HMAC tests)"
    CRED_OK=false
fi

if [[ "$CRED_OK" == "false" ]]; then
    fail "Credential validation failed. Check infra/.env."
    exit 1
fi
info "Credentials OK."

# Export ADMIN_PASSWORD and ADMIN_USER for pytest fixtures
export ADMIN_USER="${ADMIN_USER:-admin}"
export ADMIN_PASSWORD

# Also export the real database URL for Postgres integration tests
export THESTUDIO_DATABASE_URL="postgresql+asyncpg://thestudio:${POSTGRES_PASSWORD}@localhost:5434/thestudio"

# ---------------------------------------------------------------------------
# 3. Health gate
# ---------------------------------------------------------------------------
info "Running health gate..."
python -m tests.p0.health
HEALTH_EXIT=$?
if [[ $HEALTH_EXIT -ne 0 ]]; then
    fail "Health gate failed. Fix Docker stack before running P0 tests."
    exit 1
fi
info "Health gate passed."

if [[ "$HEALTH_ONLY" == "true" ]]; then
    info "Health-only mode — exiting."
    exit 0
fi

# ---------------------------------------------------------------------------
# 4. Run test suites
# ---------------------------------------------------------------------------
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
RESULTS_DIR="docs/eval-results"
mkdir -p "$RESULTS_DIR"
SUMMARY_FILE="$RESULTS_DIR/p0-${TIMESTAMP}.md"

OVERALL_EXIT=0
declare -A SUITE_RESULTS
declare -A SUITE_DURATIONS

declare -A SUITE_TESTS_PASSED
declare -A SUITE_TESTS_FAILED
declare -A SUITE_TESTS_SKIPPED
declare -A SUITE_TESTS_TOTAL
declare -A SUITE_COSTS

run_suite() {
    local name="$1"
    local cmd="$2"
    local output_file="$RESULTS_DIR/${name}-${TIMESTAMP}.txt"

    info "Running suite: ${name}..."
    local start_time
    start_time=$(date +%s)

    set +e
    eval "$cmd" 2>&1 | tee "$output_file"
    local exit_code=${PIPESTATUS[0]}
    set -e

    local end_time
    end_time=$(date +%s)
    local duration=$(( end_time - start_time ))

    SUITE_RESULTS[$name]=$exit_code
    SUITE_DURATIONS[$name]=$duration

    # Parse pytest summary line: "X passed, Y failed, Z skipped"
    local summary_line
    summary_line=$(grep -E '(passed|failed|error|skipped)' "$output_file" | tail -1 || true)
    SUITE_TESTS_PASSED[$name]=$(echo "$summary_line" | grep -oP '\d+(?= passed)' || echo "0")
    SUITE_TESTS_FAILED[$name]=$(echo "$summary_line" | grep -oP '\d+(?= failed)' || echo "0")
    SUITE_TESTS_SKIPPED[$name]=$(echo "$summary_line" | grep -oP '\d+(?= skipped)' || echo "0")
    local p="${SUITE_TESTS_PASSED[$name]:-0}" f="${SUITE_TESTS_FAILED[$name]:-0}" s="${SUITE_TESTS_SKIPPED[$name]:-0}"
    SUITE_TESTS_TOTAL[$name]=$(( p + f + s ))

    # Extract cost from eval harness output (format: "cost=$X.XXXX")
    local cost
    cost=$(grep -oP 'cost=\$[\d.]+' "$output_file" | grep -oP '[\d.]+' | awk '{s+=$1} END {printf "%.4f", s}' 2>/dev/null || echo "0.0000")
    SUITE_COSTS[$name]="$cost"

    if [[ $exit_code -eq 0 ]]; then
        info "Suite ${name}: PASSED (${duration}s, ${p} tests)"
    else
        fail "Suite ${name}: FAILED (exit ${exit_code}, ${duration}s)"
        OVERALL_EXIT=1
    fi
}

# Suite 1: P0 deployment tests (GitHub webhook + Postgres via Caddy)
run_suite "p0-deployed" "pytest tests/p0/ -m p0 -v "

# Suite 2: Eval tests (in-process with real LLM)
if [[ "$SKIP_EVAL" == "true" ]]; then
    warn "Skipping eval suite (--skip-eval)."
    SUITE_RESULTS[eval]="SKIPPED"
    SUITE_DURATIONS[eval]=0
else
    # -- Eval preflight guard (AC 2) --
    # Validate container LLM config before running eval tests.
    # Eval results are meaningless if the container is using mock provider.
    info "Running eval preflight guard..."
    python -m tests.p0.eval_preflight
    PREFLIGHT_EXIT=$?

    if [[ $PREFLIGHT_EXIT -eq 0 ]]; then
        info "Eval preflight OK."
        run_suite "eval" "pytest tests/eval/ -m requires_api_key -v "
    else
        fail "Eval preflight guard failed — skipping eval suite."
        SUITE_RESULTS[eval]="PREFLIGHT_FAIL"
        SUITE_DURATIONS[eval]=0
        OVERALL_EXIT=1
    fi
fi

# Suite 3: GitHub integration (adapter-level with real GitHub API)
run_suite "github-integration" "pytest tests/integration/test_real_github.py -m integration -v "

# Suite 4: Postgres integration (ORM-level with real Postgres)
# NOTE: This suite does drop_all/create_all on the test DB schema.
# We use a separate test database to avoid destroying the prod schema.
export THESTUDIO_DATABASE_URL="postgresql+asyncpg://thestudio:${POSTGRES_PASSWORD}@localhost:5434/thestudio_test"
# Create test DB if not exists
docker exec thestudio-prod-postgres-1 psql -U thestudio -d thestudio -c "SELECT 1 FROM pg_database WHERE datname='thestudio_test'" | grep -q 1 || \
    docker exec thestudio-prod-postgres-1 psql -U thestudio -d thestudio -c "CREATE DATABASE thestudio_test OWNER thestudio;"
run_suite "postgres-integration" "pytest tests/integration/test_postgres_backend.py -m integration -v"
# Restore prod database URL
export THESTUDIO_DATABASE_URL="postgresql+asyncpg://thestudio:${POSTGRES_PASSWORD}@localhost:5434/thestudio"

# ---------------------------------------------------------------------------
# 5. Generate results summary
# ---------------------------------------------------------------------------
info "Generating results summary..."

# Collect git info
GIT_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")"
GIT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"
GIT_DIRTY="clean"
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    GIT_DIRTY="dirty"
fi

# Calculate totals
TOTAL_DURATION=0
TOTAL_COST="0.0000"
TOTAL_PASSED=0
TOTAL_FAILED=0
for suite in "p0-deployed" "eval" "github-integration" "postgres-integration"; do
    d="${SUITE_DURATIONS[$suite]:-0}"
    TOTAL_DURATION=$(( TOTAL_DURATION + d ))
    c="${SUITE_COSTS[$suite]:-0.0000}"
    TOTAL_COST=$(awk "BEGIN {printf \"%.4f\", $TOTAL_COST + $c}")
    TOTAL_PASSED=$(( TOTAL_PASSED + ${SUITE_TESTS_PASSED[$suite]:-0} ))
    TOTAL_FAILED=$(( TOTAL_FAILED + ${SUITE_TESTS_FAILED[$suite]:-0} ))
done

cat > "$SUMMARY_FILE" << HEADER
# P0 Test Results — $(date +%Y-%m-%d) ${TIMESTAMP}

## Suite Summary

| Suite | Status | Tests | Passed | Failed | Skipped | Duration | Cost |
|---|---|---|---|---|---|---|---|
HEADER

for suite in "p0-deployed" "eval" "github-integration" "postgres-integration"; do
    result="${SUITE_RESULTS[$suite]:-N/A}"
    duration="${SUITE_DURATIONS[$suite]:-0}"
    tests="${SUITE_TESTS_TOTAL[$suite]:-0}"
    passed="${SUITE_TESTS_PASSED[$suite]:-0}"
    failed="${SUITE_TESTS_FAILED[$suite]:-0}"
    skipped="${SUITE_TESTS_SKIPPED[$suite]:-0}"
    cost="${SUITE_COSTS[$suite]:-0.0000}"
    if [[ "$result" == "0" ]]; then
        status="PASS"
    elif [[ "$result" == "SKIPPED" ]]; then
        status="SKIPPED"
    elif [[ "$result" == "PREFLIGHT_FAIL" ]]; then
        status="PREFLIGHT_FAIL"
    else
        status="FAIL (exit $result)"
    fi
    echo "| ${suite} | ${status} | ${tests} | ${passed} | ${failed} | ${skipped} | ${duration}s | \$${cost} |" >> "$SUMMARY_FILE"
done

cat >> "$SUMMARY_FILE" << TOTALS

**Total: ${TOTAL_PASSED} passed, ${TOTAL_FAILED} failed, ${TOTAL_DURATION}s, \$${TOTAL_COST}**

## Git Info

- Commit: \`${GIT_SHA}\`
- Branch: \`${GIT_BRANCH}\`
- Working tree: ${GIT_DIRTY}

TOTALS

# Failure details: extract FAILED lines from output files
HAS_FAILURES=false
for suite in "p0-deployed" "eval" "github-integration" "postgres-integration"; do
    result="${SUITE_RESULTS[$suite]:-0}"
    if [[ "$result" != "0" && "$result" != "SKIPPED" && "$result" != "PREFLIGHT_FAIL" ]]; then
        output_file="$RESULTS_DIR/${suite}-${TIMESTAMP}.txt"
        if [[ -f "$output_file" ]]; then
            if [[ "$HAS_FAILURES" == "false" ]]; then
                echo "## Failure Details" >> "$SUMMARY_FILE"
                echo "" >> "$SUMMARY_FILE"
                HAS_FAILURES=true
            fi
            echo "### ${suite}" >> "$SUMMARY_FILE"
            echo "" >> "$SUMMARY_FILE"
            echo '```' >> "$SUMMARY_FILE"
            # Extract FAILED test names and first line of failure
            grep -E '^FAILED ' "$output_file" | head -20 >> "$SUMMARY_FILE" || true
            echo '```' >> "$SUMMARY_FILE"
            echo "" >> "$SUMMARY_FILE"
        fi
    fi
done

cat >> "$SUMMARY_FILE" << FOOTER
## Environment

- Timestamp: ${TIMESTAMP}
- Caddy: https://localhost:9443
- LLM Provider: ${THESTUDIO_LLM_PROVIDER:-unknown}
- GitHub Test Repo: ${THESTUDIO_GITHUB_TEST_REPO}
- Overall: $(if [[ $OVERALL_EXIT -eq 0 ]]; then echo "PASS"; else echo "FAIL"; fi)

## Raw Output Files

FOOTER

for suite in "p0-deployed" "eval" "github-integration" "postgres-integration"; do
    echo "- \`${suite}-${TIMESTAMP}.txt\`" >> "$SUMMARY_FILE"
done

# Update latest pointer
echo "Latest run: [p0-${TIMESTAMP}.md](p0-${TIMESTAMP}.md)" > "$RESULTS_DIR/latest.md"

info "Results saved to ${SUMMARY_FILE}"

# ---------------------------------------------------------------------------
# 6. Final verdict
# ---------------------------------------------------------------------------
if [[ $OVERALL_EXIT -eq 0 ]]; then
    info "ALL P0 SUITES PASSED."
else
    fail "SOME P0 SUITES FAILED. See ${SUMMARY_FILE} for details."
fi

exit $OVERALL_EXIT
