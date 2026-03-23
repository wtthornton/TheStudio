"""Migration 045: Add execute-tier fields for Epic 42 Slice 1.

Adds columns required for execute-tier promotion:
  - taskpacket.matched_rule_id (UUID, nullable) — the trust-tier rule that matched
  - taskpacket.auto_merged (bool, default false) — whether auto-merge was enabled
  - trust_tier_rules.dry_run (bool, default false) — trial mode for rules
"""

SQL_UP = [
    """
    ALTER TABLE taskpacket
        ADD COLUMN IF NOT EXISTS matched_rule_id UUID,
        ADD COLUMN IF NOT EXISTS auto_merged BOOLEAN NOT NULL DEFAULT FALSE;
    """,
    """
    ALTER TABLE trust_tier_rules
        ADD COLUMN IF NOT EXISTS dry_run BOOLEAN NOT NULL DEFAULT FALSE;
    """,
    "COMMENT ON COLUMN taskpacket.matched_rule_id IS 'UUID of the trust-tier rule that matched this packet (Epic 42)';",
    "COMMENT ON COLUMN taskpacket.auto_merged IS 'True when the Publisher successfully enabled auto-merge on the PR (Epic 42)';",
    "COMMENT ON COLUMN trust_tier_rules.dry_run IS 'When True, the rule evaluates to SUGGEST instead of its assigned tier (Epic 42)';",
]

SQL_DOWN = [
    """
    ALTER TABLE taskpacket
        DROP COLUMN IF EXISTS matched_rule_id,
        DROP COLUMN IF EXISTS auto_merged;
    """,
    """
    ALTER TABLE trust_tier_rules
        DROP COLUMN IF EXISTS dry_run;
    """,
]
