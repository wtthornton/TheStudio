"""Migration 041: Add completed_at column to taskpacket table.

Records when a TaskPacket reached a terminal status (PUBLISHED, REJECTED,
FAILED, ABORTED). Used by Epic 39 analytics queries for throughput and
bottleneck calculations.

Backfills existing terminal TaskPackets from updated_at (best approximation).

Epic 39 Story 39.0a.
"""

SQL_UP = [
    # Add completed_at column (nullable — historical records will have NULL until backfilled)
    """
    ALTER TABLE taskpacket
    ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
    """,
    # Backfill: set completed_at = updated_at for existing terminal TaskPackets
    """
    UPDATE taskpacket
    SET completed_at = updated_at
    WHERE status IN ('published', 'rejected', 'failed', 'aborted')
      AND completed_at IS NULL;
    """,
    # Index for analytics range queries on completion time
    "CREATE INDEX IF NOT EXISTS ix_taskpacket_completed_at ON taskpacket (completed_at);",
]

SQL_DOWN = [
    "DROP INDEX IF EXISTS ix_taskpacket_completed_at;",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS completed_at;",
]
