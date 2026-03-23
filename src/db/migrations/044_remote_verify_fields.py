"""Migration 044: Add remote verification fields to repo_profile.

Adds the configuration fields required for Epic 40 (Remote Verification):
  - remote_verification_enabled (bool, default false)
  - test_command (str, default 'python -m pytest --tb=short -q')
  - lint_command (str, default 'ruff check .')
  - install_command (str, default 'pip install -e .')
  - verify_timeout_seconds (int, default 900)
  - clone_depth (int, default 1)
  - remote_verify_mode (str, default 'subprocess')

Epic 40, Story 40.0.
"""

SQL_UP = [
    """
    ALTER TABLE repo_profile
        ADD COLUMN IF NOT EXISTS remote_verification_enabled BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS test_command VARCHAR(512) NOT NULL DEFAULT 'python -m pytest --tb=short -q',
        ADD COLUMN IF NOT EXISTS lint_command VARCHAR(512) NOT NULL DEFAULT 'ruff check .',
        ADD COLUMN IF NOT EXISTS install_command VARCHAR(512) NOT NULL DEFAULT 'pip install -e .',
        ADD COLUMN IF NOT EXISTS verify_timeout_seconds INTEGER NOT NULL DEFAULT 900,
        ADD COLUMN IF NOT EXISTS clone_depth INTEGER NOT NULL DEFAULT 1,
        ADD COLUMN IF NOT EXISTS remote_verify_mode VARCHAR(32) NOT NULL DEFAULT 'subprocess';
    """,
    "COMMENT ON COLUMN repo_profile.remote_verification_enabled IS 'When True, verify_activity clones the branch and runs the repo''s own test suite';",
    "COMMENT ON COLUMN repo_profile.test_command IS 'Command to run the repo''s test suite in the cloned workspace';",
    "COMMENT ON COLUMN repo_profile.lint_command IS 'Command to run the repo''s linter in the cloned workspace';",
    "COMMENT ON COLUMN repo_profile.install_command IS 'Command to install repo dependencies before running tests/lint';",
    "COMMENT ON COLUMN repo_profile.verify_timeout_seconds IS 'Total wall-clock timeout (seconds) for the entire remote verification run';",
    "COMMENT ON COLUMN repo_profile.clone_depth IS 'Git shallow clone depth; set higher for repos that need full history';",
    "COMMENT ON COLUMN repo_profile.remote_verify_mode IS 'Execution mode for remote verification: subprocess or container';",
]

SQL_DOWN = [
    """
    ALTER TABLE repo_profile
        DROP COLUMN IF EXISTS remote_verification_enabled,
        DROP COLUMN IF EXISTS test_command,
        DROP COLUMN IF EXISTS lint_command,
        DROP COLUMN IF EXISTS install_command,
        DROP COLUMN IF EXISTS verify_timeout_seconds,
        DROP COLUMN IF EXISTS clone_depth,
        DROP COLUMN IF EXISTS remote_verify_mode;
    """,
]
