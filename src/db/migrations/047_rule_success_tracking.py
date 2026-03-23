"""Migration 047: Add rule success tracking columns to trust_tier_rules.

Adds columns for tracking auto-merge success metrics on trust-tier rules:
  - merge_count         — total auto-merges under this rule
  - revert_count        — reverts detected for auto-merges under this rule
  - deactivation_reason — why the rule was auto-deactivated (null if still active)

Epic 42 Story 42.11.
"""

SQL_UP = [
    """
    ALTER TABLE trust_tier_rules
        ADD COLUMN IF NOT EXISTS merge_count         INTEGER NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS revert_count        INTEGER NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS deactivation_reason TEXT;
    """,
    "COMMENT ON COLUMN trust_tier_rules.merge_count IS 'Total Execute-tier auto-merges under this rule (Epic 42)';",
    "COMMENT ON COLUMN trust_tier_rules.revert_count IS 'Reverts detected for auto-merges under this rule (Epic 42)';",
    "COMMENT ON COLUMN trust_tier_rules.deactivation_reason IS 'Auto-deactivation reason; NULL when rule is active (Epic 42)';",
]

SQL_DOWN = [
    """
    ALTER TABLE trust_tier_rules
        DROP COLUMN IF EXISTS merge_count,
        DROP COLUMN IF EXISTS revert_count,
        DROP COLUMN IF EXISTS deactivation_reason;
    """,
]
