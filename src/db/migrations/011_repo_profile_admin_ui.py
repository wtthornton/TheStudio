"""Migration 011: Add Admin UI columns to repo_profile.

Adds columns needed for Admin UI repo management (Story 4.1):
- default_branch: Repository's default branch name
- deleted_at: Soft delete timestamp
- writes_enabled: Publisher freeze control (default True)

Architecture reference: thestudioarc/23-admin-control-ui.md
"""

MIGRATION_ID = "011_repo_profile_admin_ui"
DEPENDS_ON = ["010_tier_transitions"]

UP = """
-- Add default_branch column (nullable for existing rows, then backfill)
ALTER TABLE repo_profile
    ADD COLUMN IF NOT EXISTS default_branch VARCHAR(255) DEFAULT 'main';

-- Add soft delete column
ALTER TABLE repo_profile
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;

-- Add writes_enabled for Publisher freeze control
ALTER TABLE repo_profile
    ADD COLUMN IF NOT EXISTS writes_enabled BOOLEAN NOT NULL DEFAULT TRUE;

-- Index for soft delete queries (exclude deleted repos by default)
CREATE INDEX IF NOT EXISTS ix_repo_profile_deleted_at
    ON repo_profile(deleted_at)
    WHERE deleted_at IS NULL;

-- Index for writes_enabled queries
CREATE INDEX IF NOT EXISTS ix_repo_profile_writes_enabled
    ON repo_profile(writes_enabled);

-- Comments
COMMENT ON COLUMN repo_profile.default_branch IS
    'Default branch name for this repository (e.g., main, master)';
COMMENT ON COLUMN repo_profile.deleted_at IS
    'Soft delete timestamp — NULL means active, non-NULL means deleted';
COMMENT ON COLUMN repo_profile.writes_enabled IS
    'Publisher write control — FALSE = Publisher freeze (no GitHub writes)';
"""

DOWN = """
DROP INDEX IF EXISTS ix_repo_profile_writes_enabled;
DROP INDEX IF EXISTS ix_repo_profile_deleted_at;
ALTER TABLE repo_profile DROP COLUMN IF EXISTS writes_enabled;
ALTER TABLE repo_profile DROP COLUMN IF EXISTS deleted_at;
ALTER TABLE repo_profile DROP COLUMN IF EXISTS default_branch;
"""
