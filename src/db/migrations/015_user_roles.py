"""Migration 015: Create user_roles table for RBAC.

Story 4.8: RBAC — Role Definitions, API Enforcement.
Derived from UserRoleRow model in src/admin/rbac.py.
"""

MIGRATION_ID = "015_user_roles"
DEPENDS_ON = ["014_settings"]

UP = """
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'operator', 'viewer');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL UNIQUE,
    role user_role NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by VARCHAR(255) NULL
);

COMMENT ON TABLE user_roles IS 'User role assignments for Admin UI RBAC';
CREATE INDEX IF NOT EXISTS ix_user_roles_user_id ON user_roles (user_id);
"""

DOWN = """
DROP TABLE IF EXISTS user_roles;
DROP TYPE IF EXISTS user_role;
"""
