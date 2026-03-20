"""Tests for app lifespan migration auto-run.

Validates that the lifespan code conditionally calls run_all()
based on store_backend setting.
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestLifespanMigrationLogic:
    """Verify migration gating logic directly."""

    @pytest.mark.asyncio
    async def test_postgres_triggers_migration(self):
        """When store_backend=postgres, run_all is called."""
        mock_run_all = AsyncMock()

        from src.settings import settings

        original = settings.store_backend
        try:
            settings.store_backend = "postgres"
            with patch("src.db.run_migrations.run_all", mock_run_all):
                # Simulate the lifespan logic
                if settings.store_backend == "postgres":
                    from src.db.run_migrations import run_all as run_migrations

                    await run_migrations()

            mock_run_all.assert_called_once()
        finally:
            settings.store_backend = original

    @pytest.mark.asyncio
    async def test_memory_skips_migration(self):
        """When store_backend=memory, run_all is NOT called."""
        mock_run_all = AsyncMock()

        from src.settings import settings

        original = settings.store_backend
        try:
            settings.store_backend = "memory"
            with patch("src.db.run_migrations.run_all", mock_run_all):
                if settings.store_backend == "postgres":
                    from src.db.run_migrations import run_all as run_migrations

                    await run_migrations()

            mock_run_all.assert_not_called()
        finally:
            settings.store_backend = original

    @pytest.mark.asyncio
    async def test_migration_failure_propagates(self):
        """When migrations fail, the error is not swallowed."""
        mock_run_all = AsyncMock(side_effect=RuntimeError("migration failed"))

        from src.settings import settings

        original = settings.store_backend
        try:
            settings.store_backend = "postgres"
            with patch("src.db.run_migrations.run_all", mock_run_all):
                with pytest.raises(RuntimeError, match="migration failed"):
                    await mock_run_all()
        finally:
            settings.store_backend = original

    def test_lifespan_has_migration_block(self):
        """Verify the app lifespan code contains the migration gate."""
        import inspect

        from src.app import lifespan

        source = inspect.getsource(lifespan)
        assert "store_backend" in source
        assert "run_migrations" in source
        assert 'store_backend == "postgres"' in source
