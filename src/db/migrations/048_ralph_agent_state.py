"""Migration 048: Create ralph_agent_state table.

Stores per-session key/value state for the RalphAgent state backend.
Used by PostgresStateBackend to persist agent session data across
Temporal activity retries and loopback cycles.

Epic 43 Story 43.6.
"""

SQL_UP = [
    """
    CREATE TABLE IF NOT EXISTS ralph_agent_state (
        id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
        taskpacket_id   UUID         NOT NULL,
        key_name        VARCHAR(64)  NOT NULL,
        value_json      TEXT         NOT NULL,
        updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_ralph_agent_state_task_key UNIQUE (taskpacket_id, key_name)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_ralph_agent_state_taskpacket_id ON ralph_agent_state (taskpacket_id);",
    "COMMENT ON TABLE ralph_agent_state IS 'Per-session key/value state for RalphAgent (Epic 43)';",
    "COMMENT ON COLUMN ralph_agent_state.taskpacket_id IS 'TaskPacket this state belongs to';",
    "COMMENT ON COLUMN ralph_agent_state.key_name IS 'State key (max 64 chars)';",
    "COMMENT ON COLUMN ralph_agent_state.value_json IS 'JSON-serialised state value';",
    "COMMENT ON COLUMN ralph_agent_state.updated_at IS 'Last upsert timestamp — used for session TTL checks';",
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS ralph_agent_state;",
]
