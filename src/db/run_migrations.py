"""Run all database migrations in order.

Handles both migration styles:
- Legacy (001-008): SQL_UP as list of statements + migrate_up() coroutine
- Modern (009-014): UP as single SQL string + MIGRATION_ID constant

Usage:
    python -m src.db.run_migrations
"""

import asyncio
import importlib
import logging
import re
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.settings import settings

logger = logging.getLogger(__name__)

# Ordered list of migration modules
MIGRATIONS = [
    "src.db.migrations.001_taskpacket",
    "src.db.migrations.002_repo_profile",
    "src.db.migrations.003_taskpacket_enrichment",
    "src.db.migrations.004_intent_spec",
    "src.db.migrations.005_expert_library",
    "src.db.migrations.006_complexity_index_v1",
    "src.db.migrations.007_quarantine_dead_letter",
    "src.db.migrations.008_trust_tier_persistence",
    "src.db.migrations.009_compliance_results",
    "src.db.migrations.010_tier_transitions",
    "src.db.migrations.011_repo_profile_admin_ui",
    "src.db.migrations.012_tool_catalog",
    "src.db.migrations.013_model_audit",
    "src.db.migrations.014_settings",
    "src.db.migrations.015_user_roles",
    "src.db.migrations.016_audit_log",
    "src.db.migrations.017_repo_profile_poll",
    "src.db.migrations.018_audit_event_repo_profile_updated",
]


def _split_sql(sql: str) -> list[str]:
    """Split a multi-statement SQL string into individual statements.

    Handles DO $$ ... END $$ blocks as single statements.
    """
    statements: list[str] = []
    current: list[str] = []
    in_dollar_block = False

    for line in sql.split("\n"):
        stripped = line.strip()
        # Skip empty lines and comments at statement boundaries
        if not stripped or (stripped.startswith("--") and not in_dollar_block and not current):
            continue

        current.append(line)

        # Track DO $$ ... END $$ blocks
        if re.search(r"DO\s+\$\$", stripped, re.IGNORECASE):
            in_dollar_block = True
        if in_dollar_block and re.search(r"END\s+\$\$\s*;", stripped, re.IGNORECASE):
            in_dollar_block = False
            statements.append("\n".join(current))
            current = []
            continue

        # Regular statement ending with semicolon (outside dollar blocks)
        if not in_dollar_block and stripped.endswith(";"):
            statements.append("\n".join(current))
            current = []

    # Catch any trailing content without semicolon
    remainder = "\n".join(current).strip()
    if remainder:
        statements.append(remainder)

    return [s.strip() for s in statements if s.strip()]


async def run_all() -> None:
    """Apply all migrations, skipping those already applied."""
    engine = create_async_engine(settings.database_url)

    # Create migration tracking table if it doesn't exist
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS _migrations (
                name VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        result = await conn.execute(text("SELECT name FROM _migrations"))
        applied = {row[0] for row in result.fetchall()}

    for module_path in MIGRATIONS:
        name = module_path.rsplit(".", 1)[-1]
        if name in applied:
            logger.info("Skip (already applied): %s", name)
            continue

        mod = importlib.import_module(module_path)

        async with engine.begin() as conn:
            # Modern style: single UP string — split into individual statements
            if hasattr(mod, "UP"):
                for stmt in _split_sql(mod.UP):
                    await conn.execute(text(stmt))
            # Legacy style: SQL_UP list
            elif hasattr(mod, "SQL_UP"):
                for stmt in mod.SQL_UP:
                    await conn.execute(text(stmt))
            else:
                logger.warning("No UP or SQL_UP found in %s, skipping", name)
                continue

            await conn.execute(
                text("INSERT INTO _migrations (name) VALUES (:name)"),
                {"name": name},
            )
            logger.info("Applied: %s", name)

    await engine.dispose()
    logger.info("All migrations complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(run_all())
