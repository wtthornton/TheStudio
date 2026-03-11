"""Migration 017: Add poll config columns to repo_profile.

Epic 17 — Poll for Issues as Backup to Webhooks.
Adds poll_enabled and poll_interval_minutes for optional polling intake.
"""

MIGRATION_ID = "017_repo_profile_poll"
DEPENDS_ON = ["016_audit_log"]

UP = """
-- Add poll_enabled (opt-in per repo)
ALTER TABLE repo_profile
    ADD COLUMN IF NOT EXISTS poll_enabled BOOLEAN NOT NULL DEFAULT FALSE;

-- Add poll_interval_minutes (NULL = use global default)
ALTER TABLE repo_profile
    ADD COLUMN IF NOT EXISTS poll_interval_minutes INTEGER DEFAULT NULL;

COMMENT ON COLUMN repo_profile.poll_enabled IS
    'Enable issue polling for this repo (backup when webhooks unavailable)';
COMMENT ON COLUMN repo_profile.poll_interval_minutes IS
    'Poll interval in minutes; NULL = use THESTUDIO_INTAKE_POLL_INTERVAL_MINUTES';

CREATE INDEX IF NOT EXISTS ix_repo_profile_poll_enabled
    ON repo_profile(poll_enabled)
    WHERE poll_enabled = TRUE;
"""

DOWN = """
DROP INDEX IF EXISTS ix_repo_profile_poll_enabled;
ALTER TABLE repo_profile DROP COLUMN IF EXISTS poll_interval_minutes;
ALTER TABLE repo_profile DROP COLUMN IF EXISTS poll_enabled;
"""
