"""Migration 046: Create auto_merge_outcomes table.

Tracks the post-merge outcome of each auto-merged PR (succeeded, reverted,
or issue_detected) for rule health analysis and dashboard visibility.

Epic 42 Story 42.10.
"""

SQL_UP = [
    """
    CREATE TABLE IF NOT EXISTS auto_merge_outcomes (
        id                  UUID         PRIMARY KEY,
        taskpacket_id       UUID         NOT NULL,
        rule_id             UUID,
        pr_number           INTEGER      NOT NULL,
        repo                VARCHAR(500) NOT NULL,
        merged_at           TIMESTAMPTZ  NOT NULL,
        outcome             VARCHAR(50)  NOT NULL DEFAULT 'succeeded',
        detected_at         TIMESTAMPTZ,
        revert_sha          VARCHAR(100),
        linked_issue_number INTEGER,
        notes               TEXT,
        created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_auto_merge_outcomes_taskpacket_id ON auto_merge_outcomes (taskpacket_id);",
    "CREATE INDEX IF NOT EXISTS ix_auto_merge_outcomes_rule_id        ON auto_merge_outcomes (rule_id);",
    "CREATE INDEX IF NOT EXISTS ix_auto_merge_outcomes_outcome         ON auto_merge_outcomes (outcome);",
    "CREATE INDEX IF NOT EXISTS ix_auto_merge_outcomes_created_at      ON auto_merge_outcomes (created_at);",
    "COMMENT ON TABLE auto_merge_outcomes IS 'Post-merge outcomes for Execute-tier auto-merged PRs (Epic 42)';",
    "COMMENT ON COLUMN auto_merge_outcomes.outcome IS 'succeeded | reverted | issue_detected';",
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS auto_merge_outcomes;",
]
