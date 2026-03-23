"""Migration 049: Add triage fields to taskpacket.

Adds issue_title, issue_body, triage_enrichment, and rejection_reason
columns to the taskpacket table. These were added to the ORM model
in Epic 36 (Planning Experience) but the migration was missed.
"""

SQL_UP = [
    "ALTER TABLE taskpacket ADD COLUMN IF NOT EXISTS issue_title VARCHAR(500);",
    "ALTER TABLE taskpacket ADD COLUMN IF NOT EXISTS issue_body VARCHAR(65535);",
    "ALTER TABLE taskpacket ADD COLUMN IF NOT EXISTS triage_enrichment JSONB;",
    "ALTER TABLE taskpacket ADD COLUMN IF NOT EXISTS rejection_reason VARCHAR(50);",
]

SQL_DOWN = [
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS rejection_reason;",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS triage_enrichment;",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS issue_body;",
    "ALTER TABLE taskpacket DROP COLUMN IF EXISTS issue_title;",
]
