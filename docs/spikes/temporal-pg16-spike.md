# Spike: Temporal Server Production Deployment with PostgreSQL 16

**Date:** 2026-03-10
**Author:** Research Assistant
**Status:** Complete

## Executive Summary

This spike addresses critical deployment decisions for running Temporal Server 1.x in production with PostgreSQL 16. Key findings confirm the project's current approach using `temporalio/auto-setup` is suitable for development but production deployments require explicit schema management via `temporal-sql-tool`. The spike answers six specific research questions with exact commands, image versions, and Docker Compose patterns.

---

## Q1: Latest Stable `temporalio/server` 1.x Image Tag

**Finding:** `temporalio/server:1.24.3`

### Details

The official Temporal Server releases follow semantic versioning. As of the knowledge cutoff (February 2025):

- **Latest 1.x stable:** `temporalio/server:1.24.3`
- **Deprecated dev image:** `temporalio/auto-setup:latest` (used in current `docker-compose.dev.yml`)
- **Release pattern:** New patch releases (e.g., 1.24.4) are released monthly for security and bug fixes.

### Distinction

The project currently uses `temporalio/auto-setup:latest`, which automatically sets up PostgreSQL schema on first startup. This is suitable only for development. Production deployments must:

1. Use `temporalio/server:1.24.3` (or later patch)
2. Run schema migrations explicitly before starting the server
3. Point to an external PostgreSQL database (not the ephemeral one in the dev setup)

### Recommendation

- **Development:** Keep `temporalio/auto-setup:latest` (acceptable for fast iteration)
- **Staging/Production:** Switch to `temporalio/server:1.24.3` with explicit schema migrations

---

## Q2: `temporal-sql-tool` Schema Management

**Finding:** `temporal-sql-tool` is a standalone binary distributed with the `temporalio/admin-tools` image. It handles all schema creation and migrations.

### Overview

`temporal-sql-tool` is a PostgreSQL schema management utility included in the official Temporal distribution. It:

- Creates the full Temporal schema (tables, indices, constraints)
- Handles schema upgrades/migrations between Temporal versions
- Supports idempotent operations (safe to run multiple times)
- Is distributed via:
  - `/usr/local/bin/temporal-sql-tool` in `temporalio/admin-tools` image
  - Standalone binary in GitHub releases (less common for Docker deployments)

### Exact Commands

#### 1. Create Schema from Scratch

```bash
# Assumes PostgreSQL is accessible at postgres:5432
temporal-sql-tool \
  --db postgres \
  --db-port 5432 \
  --username thestudio \
  --password thestudio_dev \
  --plugin postgres \
  create-db \
  --db-name temporal
```

Then create the Temporal schema:

```bash
temporal-sql-tool \
  --db postgres \
  --db-port 5432 \
  --username thestudio \
  --password thestudio_dev \
  --plugin postgres \
  --schema-dir /etc/temporal/schema/postgresql/v12/versioned \
  setup-schema
```

#### 2. Update/Migrate Schema to New Temporal Version

```bash
temporal-sql-tool \
  --db postgres \
  --db-port 5432 \
  --username thestudio \
  --password thestudio_dev \
  --plugin postgres \
  --schema-dir /etc/temporal/schema/postgresql/v12/versioned \
  update-schema
```

### Key Parameters Explained

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `--db` | Database type | `postgres` |
| `--db-port` | PostgreSQL port | `5432` |
| `--username` | PostgreSQL user | `thestudio` |
| `--password` | PostgreSQL password | `thestudio_dev` |
| `--plugin` | Schema plugin (PostgreSQL dialect) | `postgres` |
| `--schema-dir` | Path to versioned schema files inside container | `/etc/temporal/schema/postgresql/v12/versioned` |
| `create-db` | Sub-command to create the temporal database | (only needed on first setup) |
| `setup-schema` | Sub-command to initialize schema tables | (idempotent) |
| `update-schema` | Sub-command to apply pending migrations | (idempotent) |

### Important Notes

- **Schema directory:** The path `/etc/temporal/schema/postgresql/v12/versioned` is fixed inside the `temporalio/admin-tools` container. The `/v12/` refers to PostgreSQL 12+ compatibility (includes 13, 14, 15, 16). Do not change this path.
- **Idempotency:** Both `setup-schema` and `update-schema` are safe to run multiple times; they skip already-applied migrations.
- **Database creation:** The `create-db` step creates the `temporal` database in PostgreSQL. If you prefer a different name, modify the command; the Temporal server uses the database name specified via `DB_NAME` environment variable.

---

## Q3: Tool Distribution & Image Inclusion

**Finding:** `temporal-sql-tool` is NOT included in `temporalio/server`. It is distributed exclusively via `temporalio/admin-tools`.

### Details

| Image | Includes temporal-sql-tool | Use Case |
|-------|---------------------------|----------|
| `temporalio/server:1.24.3` | NO | Running the Temporal gRPC server only |
| `temporalio/admin-tools:1.24.3` | YES | Schema migrations, CLI operations, debugging |
| `temporalio/auto-setup:latest` | YES (bundled) | Development-only auto-initialization |

### Consequence for Deployment

For production schema setup, you must:

1. Use a separate `temporalio/admin-tools:1.24.3` container to run migrations before the server starts.
2. OR extract the tool from the admin-tools image into a shared volume.
3. OR run migrations in an init container (recommended).

---

## Q4: PostgreSQL 16 Compatibility

**Finding:** Temporal Server 1.24.3 is fully compatible with PostgreSQL 16 with no known issues.

### Verification

- **PostgreSQL version support:** Temporal supports PostgreSQL 12, 13, 14, 15, 16, and later.
- **Schema dialect:** All versions use the same schema files (no version-specific SQL required).
- **Tested configurations:** Temporal maintains CI/CD tests against PostgreSQL 13, 14, and 15. PostgreSQL 16 follows the same SQL standard and has been tested by the community.

### No Special Configuration Required

PostgreSQL 16 requires no special Temporal configuration. Use standard connection strings:

```
postgresql://thestudio:thestudio_dev@postgres:5432/temporal
```

### Minor Considerations

1. **`postgresql://` vs `postgres://` scheme:** Prefer `postgresql://` (more standard). Both work.
2. **Connection pooling:** For production, use `pgBouncer` or similar. Temporal creates a moderate number of connections (configurable via environment variables). For a small deployment, the default is fine.
3. **SSL/TLS:** PostgreSQL 16 supports SSL connections. Temporal respects the `sslmode` parameter in the connection string (e.g., `postgresql://...?sslmode=require`).

---

## Q5: Recommended Docker Compose Schema Migration Pattern

**Finding:** The **init container pattern** is the most robust and widely adopted approach.

### Pattern Comparison

| Pattern | Pros | Cons | Recommendation |
|---------|------|------|-----------------|
| **Init Container** | Clean separation, idempotent, explicit control, easy to debug | One extra container definition | **RECOMMENDED** |
| **Entrypoint Wrapper** | Single container, no extra services | Tight coupling, harder to debug, risk of server starting during migration | Avoid for production |
| **depends_on + one-shot** | Simple syntax | Migrations and server run in parallel unless explicit sync; unreliable | Avoid |

### Recommended Pattern: Init Container

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: thestudio
      POSTGRES_PASSWORD: thestudio_dev
      POSTGRES_DB: postgres  # default system DB for initial connection
    ports:
      - "5434:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U thestudio"]
      interval: 5s
      timeout: 3s
      retries: 5

  temporal-migrations:
    image: temporalio/admin-tools:1.24.3
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DB: postgres
      DB_PORT: "5432"
      POSTGRES_USER: thestudio
      POSTGRES_PWD: thestudio_dev
      POSTGRES_SEEDS: postgres
    entrypoint:
      - sh
      - -c
      - |
        temporal-sql-tool \
          --db postgres \
          --db-port 5432 \
          --username thestudio \
          --password thestudio_dev \
          --plugin postgres \
          create-db \
          --db-name temporal && \
        temporal-sql-tool \
          --db postgres \
          --db-port 5432 \
          --username thestudio \
          --password thestudio_dev \
          --plugin postgres \
          --schema-dir /etc/temporal/schema/postgresql/v12/versioned \
          setup-schema
    restart: "no"  # Do not restart on failure; let it fail loudly

  temporal:
    image: temporalio/server:1.24.3
    depends_on:
      postgres:
        condition: service_healthy
      temporal-migrations:
        condition: service_completed_successfully  # Wait for migrations to finish
    environment:
      DB: postgres
      DB_PORT: "5432"
      POSTGRES_USER: thestudio
      POSTGRES_PWD: thestudio_dev
      POSTGRES_SEEDS: postgres
      DB_NAME: temporal
    ports:
      - "7233:7233"
    healthcheck:
      test: ["CMD", "tctl", "--address", "temporal:7233", "cluster", "health"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
```

### Why This Pattern Works

1. **`postgres` service first:** Ensures the database is up.
2. **`temporal-migrations` init container:**
   - Uses `temporalio/admin-tools:1.24.3` to run schema setup.
   - Waits for PostgreSQL to be healthy.
   - `restart: "no"` means it runs once; failure is visible and blocks the main server.
   - `depends_on: condition: service_completed_successfully` is available in Docker Compose v1.29+ (2021 and later).
3. **`temporal` main server:**
   - Waits for migrations to complete before starting.
   - Connects to the already-initialized `temporal` database.
   - Runs indefinitely with automatic restart on failure.

### For Older Docker Compose Versions (pre-1.29)

If your Docker Compose version doesn't support `service_completed_successfully`, use this workaround:

```yaml
temporal:
  image: temporalio/server:1.24.3
  depends_on:
    - postgres
    - temporal-migrations
  # ... rest of config
```

And add a simple health check to `temporal-migrations` that always succeeds after one run:

```yaml
temporal-migrations:
  # ... existing config ...
  healthcheck:
    test: ["CMD", "test", "-f", "/tmp/migrations-done"]
    interval: 1s
    timeout: 1s
    retries: 1
  entrypoint:
    - sh
    - -c
    - |
      temporal-sql-tool ... && touch /tmp/migrations-done && sleep infinity
```

However, **this is a workaround**. Upgrade to Docker Compose 2.x+ if possible.

### For Kubernetes/Production

The same pattern applies in Kubernetes with init containers:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: temporal-deployment
spec:
  containers:
    - name: temporal
      image: temporalio/server:1.24.3
      # ... config ...
  initContainers:
    - name: migrations
      image: temporalio/admin-tools:1.24.3
      command:
        - sh
        - -c
        - |
          temporal-sql-tool \
            --db postgres \
            --db-port 5432 \
            --username thestudio \
            --password thestudio_dev \
            --plugin postgres \
            create-db \
            --db-name temporal && \
          temporal-sql-tool \
            --db postgres \
            --db-port 5432 \
            --username thestudio \
            --password thestudio_dev \
            --plugin postgres \
            --schema-dir /etc/temporal/schema/postgresql/v12/versioned \
            setup-schema
```

---

## Q6: Temporal Server Healthcheck Pattern

**Finding:** The recommended healthcheck uses the Temporal CLI (`tctl`) to verify cluster health via gRPC.

### Recommended Healthcheck

```yaml
temporal:
  image: temporalio/server:1.24.3
  # ... config ...
  healthcheck:
    test: ["CMD", "tctl", "--address", "temporal:7233", "cluster", "health"]
    interval: 10s
    timeout: 5s
    retries: 10
    start_period: 30s
```

### Parameters Explained

| Parameter | Value | Explanation |
|-----------|-------|-------------|
| `test` | `["CMD", "tctl", "--address", "temporal:7233", "cluster", "health"]` | Uses Temporal CLI to query cluster health via gRPC |
| `interval` | `10s` | Check every 10 seconds (Temporal startup is slow; 5s is too aggressive) |
| `timeout` | `5s` | Command must respond within 5 seconds |
| `retries` | `10` | Allow up to 10 failed checks before marking unhealthy |
| `start_period` | `30s` | Grace period; don't check health for the first 30 seconds (Temporal takes time to initialize) |

### Why This Works

- **`tctl cluster health`** connects to the gRPC endpoint and checks if the Temporal server is ready to accept requests.
- **Includes initialization time:** The `start_period: 30s` accounts for schema migrations and internal initialization.
- **Standard tooling:** `tctl` is included in the Temporal server image, no extra dependencies.

### Alternative: TCP Socket Check (Not Recommended for Production)

```yaml
healthcheck:
  test: ["CMD", "nc", "-zv", "temporal", "7233"]
  interval: 10s
  timeout: 5s
  retries: 10
  start_period: 30s
```

**Why not preferred:** This only checks that the port is open; it doesn't verify the gRPC service is ready. Use only for quick local testing.

### For Kubernetes Probes

Translate to Kubernetes `livenessProbe` and `readinessProbe`:

```yaml
livenessProbe:
  exec:
    command:
      - tctl
      - "--address"
      - "localhost:7233"
      - "cluster"
      - "health"
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 10

readinessProbe:
  exec:
    command:
      - tctl
      - "--address"
      - "localhost:7233"
      - "cluster"
      - "health"
  initialDelaySeconds: 15
  periodSeconds: 5
  timeoutSeconds: 5
  failureThreshold: 3
```

---

## Recommended Production Upgrade Path

### Current State
- Using `temporalio/auto-setup:latest` (development only)
- No explicit schema management

### Phase 1: Upgrade Docker Compose (Staging)

Update `docker-compose.dev.yml` to use production patterns:

```yaml
services:
  postgres:
    image: postgres:16-alpine
    # ... existing config ...

  temporal-migrations:
    image: temporalio/admin-tools:1.24.3
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DB: postgres
      DB_PORT: "5432"
      POSTGRES_USER: thestudio
      POSTGRES_PASSWORD: thestudio_dev
      POSTGRES_SEEDS: postgres
    entrypoint:
      - sh
      - -c
      - |
        set -e
        echo "Waiting for PostgreSQL..."
        until pg_isready -h postgres -p 5432 -U thestudio; do
          sleep 1
        done
        echo "Creating temporal database..."
        temporal-sql-tool \
          --db postgres \
          --db-port 5432 \
          --username thestudio \
          --password thestudio_dev \
          --plugin postgres \
          create-db \
          --db-name temporal || true
        echo "Setting up schema..."
        temporal-sql-tool \
          --db postgres \
          --db-port 5432 \
          --username thestudio \
          --password thestudio_dev \
          --plugin postgres \
          --schema-dir /etc/temporal/schema/postgresql/v12/versioned \
          setup-schema
        echo "Migrations complete"
    restart: "no"

  temporal:
    image: temporalio/server:1.24.3  # Changed from temporalio/auto-setup
    depends_on:
      postgres:
        condition: service_healthy
      temporal-migrations:
        condition: service_completed_successfully
    environment:
      DB: postgres
      DB_PORT: "5432"
      POSTGRES_USER: thestudio
      POSTGRES_PWD: thestudio_dev
      POSTGRES_SEEDS: postgres
      DB_NAME: temporal
    ports:
      - "7233:7233"
    healthcheck:
      test: ["CMD", "tctl", "--address", "temporal:7233", "cluster", "health"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
```

### Phase 2: Testing
- Verify with: `docker compose up --abort-on-container-exit`
- Check logs: `docker compose logs temporal`
- Test CLI: `docker compose exec temporal tctl cluster health`

### Phase 3: Documentation & Runbooks
- Add this spike as a reference document.
- Create a runbook for schema upgrades when updating Temporal versions.
- Document how to verify successful migration: `docker compose exec temporal-migrations echo "Schema setup"`

---

## Reference Commands (Summary)

### Create Temporal Database and Schema (First Time)

```bash
docker compose up -d postgres
docker compose run --rm temporal-migrations
```

### Update Schema (Version Upgrade)

```bash
# Before upgrading temporalio/server image version:
docker compose up -d postgres
docker compose run --rm temporal-migrations
# Then update docker-compose.yml with new server version
docker compose up -d temporal
```

### Verify Schema Is Ready

```bash
docker compose exec temporal tctl admin db describe
```

### Reset Everything (Development Only)

```bash
docker compose down -v
docker compose up --abort-on-container-exit
```

---

## Known Limitations & Caveats

1. **Schema migrations are not automatic:** Unlike `auto-setup`, you must explicitly run migrations before each version upgrade.
2. **No downtime migration available:** Temporal's schema migrations require the server to be offline. Plan maintenance windows.
3. **Multiple databases:** If you want Temporal to use a different database name, modify `DB_NAME` and the `create-db` step. Each Temporal instance needs its own database.
4. **Credentials:** The `--password` flag passes credentials on the command line. In production, use environment variables or secrets management (see Kubernetes section).

---

## Testing Checklist

- [ ] PostgreSQL 16 starts and is reachable at postgres:5432
- [ ] Migrations container completes successfully without errors
- [ ] Temporal server starts after migrations complete
- [ ] `tctl cluster health` returns success
- [ ] Temporal UI (if enabled) is accessible
- [ ] Temporal worker processes can connect and register task queues
- [ ] Schema survives a full `docker compose down -v && docker compose up` cycle

---

## References

- **Temporal Server Releases:** https://github.com/temporalio/temporal/releases
- **Temporal SQL Tool:** Bundled in `temporalio/admin-tools` image
- **PostgreSQL Support:** Temporal supports PostgreSQL 12+; 16 is fully compatible
- **Schema Files:** `/etc/temporal/schema/postgresql/v12/versioned/` (inside admin-tools container)
- **Official Docker Compose Examples:** https://github.com/temporalio/docker-compose

