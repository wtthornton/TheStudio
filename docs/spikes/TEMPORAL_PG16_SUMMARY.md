# Temporal PostgreSQL 16 Spike — Quick Reference

**Full spike document:** `docs/spikes/temporal-pg16-spike.md`

## Six Questions Answered

| # | Question | Answer |
|----|----------|--------|
| **Q1** | Latest stable `temporalio/server` 1.x tag? | `temporalio/server:1.24.3` |
| **Q2** | How does `temporal-sql-tool` work? | Included in `temporalio/admin-tools:1.24.3`; runs schema setup before main server starts |
| **Q3** | Is it in `temporalio/server` image? | **No.** Distributed only in `temporalio/admin-tools` |
| **Q4** | PostgreSQL 16 compatibility issues? | **None.** Fully supported; same schema files work for PG 12-16+ |
| **Q5** | Recommended Docker Compose pattern? | **Init container pattern** — migrations as a separate service with `depends_on: service_completed_successfully` |
| **Q6** | Healthcheck for Temporal server? | `tctl --address temporal:7233 cluster health` with 30s start_period |

## Implementation Checklist for Migration

- [ ] Update `docker-compose.dev.yml`: replace `temporalio/auto-setup:latest` with `temporalio/server:1.24.3`
- [ ] Add init container `temporal-migrations` using `temporalio/admin-tools:1.24.3`
- [ ] Add `depends_on: temporal-migrations: condition: service_completed_successfully` to temporal service
- [ ] Set `DB_NAME: temporal` environment variable on server
- [ ] Update healthcheck to use `tctl cluster health` (already in spike doc)
- [ ] Test with: `docker compose up --abort-on-container-exit`
- [ ] Verify: `docker compose exec temporal tctl cluster health`

## Critical Points

1. **Current dev setup is fine:** `temporalio/auto-setup:latest` is acceptable for local development. Only production/staging need changes.
2. **Migrations must run first:** `temporal-migrations` container MUST complete before `temporal` service starts.
3. **No special PG16 config needed:** Use standard connection strings; Temporal handles it automatically.
4. **Explicit schema setup is idempotent:** Safe to run multiple times or re-apply without data loss.
5. **Tool is included:** `temporal-sql-tool` is pre-packaged in `temporalio/admin-tools` — no downloads or installations needed.

## Example Docker Compose Snippet

Full version with all services is in the spike document. Here's the key pattern:

```yaml
services:
  temporal-migrations:
    image: temporalio/admin-tools:1.24.3
    depends_on:
      postgres:
        condition: service_healthy
    restart: "no"
    entrypoint:
      - sh
      - -c
      - |
        temporal-sql-tool --db postgres --db-port 5432 --username thestudio \
          --password thestudio_dev --plugin postgres create-db --db-name temporal && \
        temporal-sql-tool --db postgres --db-port 5432 --username thestudio \
          --password thestudio_dev --plugin postgres \
          --schema-dir /etc/temporal/schema/postgresql/v12/versioned setup-schema

  temporal:
    image: temporalio/server:1.24.3
    depends_on:
      temporal-migrations:
        condition: service_completed_successfully
    environment:
      DB: postgres
      DB_PORT: "5432"
      POSTGRES_USER: thestudio
      POSTGRES_PWD: thestudio_dev
      POSTGRES_SEEDS: postgres
      DB_NAME: temporal
    healthcheck:
      test: ["CMD", "tctl", "--address", "temporal:7233", "cluster", "health"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
```

## Next Steps

1. Review `docs/spikes/temporal-pg16-spike.md` for full details and Kubernetes examples
2. Plan migration to staging environment
3. Test full stack with new Docker Compose pattern
4. Update deployment documentation with schema migration runbook
