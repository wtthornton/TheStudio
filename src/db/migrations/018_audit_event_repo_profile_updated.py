"""Migration 018: Add repo_profile_updated to audit_event_type enum.

Code emits AuditEventType.REPO_PROFILE_UPDATED but 016_audit_log did not
include it. Add the value so profile PATCH can log audit events.
"""

MIGRATION_ID = "018_audit_event_repo_profile_updated"
DEPENDS_ON = ["017_repo_profile_poll"]

UP = """
ALTER TYPE audit_event_type ADD VALUE IF NOT EXISTS 'repo_profile_updated';
"""

DOWN = """
-- Enum values cannot be removed in PostgreSQL; downgrade is a no-op.
"""
