"""Migration 042: Add pr_merge_status column to taskpacket table.

Tracks the merge status of the associated pull request: open, merged, or closed.
Updated by the Epic 38 webhook bridge (Story 38.24) or a polling activity.

Epic 39 Story 39.0b.
"""

SQL_UP = [
    # Create the enum type
    """
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'pr_merge_status_enum') THEN
            CREATE TYPE pr_merge_status_enum AS ENUM ('open', 'merged', 'closed');
        END IF;
    END $$;
    """,
    # Add the nullable column (only set for PUBLISHED tasks with a PR)
    """
    ALTER TABLE taskpacket
    ADD COLUMN IF NOT EXISTS pr_merge_status pr_merge_status_enum;
    """,
    # Index to support analytics queries filtering by merge status
    "CREATE INDEX IF NOT EXISTS ix_taskpacket_pr_merge_status ON taskpacket (pr_merge_status);",
]

SQL_DOWN = [
    "DROP INDEX IF EXISTS ix_taskpacket_pr_merge_status;",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS pr_merge_status;",
    "DROP TYPE IF EXISTS pr_merge_status_enum;",
]
