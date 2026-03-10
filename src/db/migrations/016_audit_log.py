"""Migration 016: Create audit_log table.

Stores admin action audit trail. Derived from AuditLogRow model in src/admin/audit.py.
"""

MIGRATION_ID = "016_audit_log"
DEPENDS_ON = ["015_user_roles"]

UP = """
DO $$ BEGIN
    CREATE TYPE audit_event_type AS ENUM (
        'repo_registered', 'repo_tier_changed', 'repo_paused', 'repo_resumed',
        'repo_disabled', 'repo_writes_enabled', 'repo_writes_disabled',
        'settings_changed'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor VARCHAR(255) NOT NULL,
    event_type audit_event_type NOT NULL,
    target_id VARCHAR(255) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

COMMENT ON TABLE audit_log IS 'Audit log for admin actions';
CREATE INDEX IF NOT EXISTS ix_audit_log_timestamp ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_audit_log_actor ON audit_log (actor);
CREATE INDEX IF NOT EXISTS ix_audit_log_event_type ON audit_log (event_type);
"""

DOWN = """
DROP TABLE IF EXISTS audit_log;
DROP TYPE IF EXISTS audit_event_type;
"""
