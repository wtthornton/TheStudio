"""Migration 050: Add pipeline_comments_enabled to repo_profile.

Adds a nullable boolean column that provides a per-repo override for the
global THESTUDIO_PIPELINE_COMMENTS_ENABLED setting (Epic 38.23).

NULL  = inherit global setting (default behaviour — no change for existing rows)
TRUE  = always post pipeline comments for this repo
FALSE = never post pipeline comments for this repo
"""

SQL_UP = [
    """ALTER TABLE repo_profile
       ADD COLUMN IF NOT EXISTS pipeline_comments_enabled BOOLEAN DEFAULT NULL;""",
    """COMMENT ON COLUMN repo_profile.pipeline_comments_enabled IS
       'Per-repo pipeline comment override (Epic 38.23). '
       'NULL = inherit global flag; TRUE/FALSE = explicit enable/disable.';""",
]

SQL_DOWN = [
    "ALTER TABLE repo_profile DROP COLUMN IF EXISTS pipeline_comments_enabled;",
]
