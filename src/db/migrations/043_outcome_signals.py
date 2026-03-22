"""Migration 043: Create outcome_signals table.

Persists validated outcome signals (verification_passed, verification_failed,
verification_exhausted, qa_passed, qa_defect, qa_rework) to PostgreSQL for
analytics queries in Epic 39 Slice 2 (Reputation & Outcomes Feed).

Replaces the in-memory `_signals` list in src/outcome/ingestor.py.

Epic 39 Story 39.0c.
"""

SQL_UP = [
    """
    CREATE TABLE IF NOT EXISTS outcome_signals (
        id             UUID         PRIMARY KEY,
        task_id        UUID,
        correlation_id UUID,
        signal_type    VARCHAR(100) NOT NULL,
        payload        JSONB        NOT NULL DEFAULT '{}',
        signal_at      TIMESTAMPTZ  NOT NULL,
        created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_outcome_signals_task_id    ON outcome_signals (task_id);",
    "CREATE INDEX IF NOT EXISTS ix_outcome_signals_created_at ON outcome_signals (created_at);",
    "CREATE INDEX IF NOT EXISTS ix_outcome_signals_signal_type ON outcome_signals (signal_type);",
]

SQL_DOWN = [
    "DROP TABLE IF EXISTS outcome_signals;",
]
