"""Settings table for Admin Settings UI.

Story 12.1: Settings Data Model & Encrypted Storage.
Stores key-value platform settings with Fernet encryption for sensitive values.
"""

MIGRATION_ID = "014_settings"
DEPENDS_ON = ["013_model_audit"]

UP = """
-- Setting category enum
DO $$ BEGIN
    CREATE TYPE setting_category AS ENUM (
        'api_keys', 'infrastructure', 'feature_flags', 'agent_config', 'secrets'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(255) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    encrypted BOOLEAN NOT NULL DEFAULT FALSE,
    category setting_category NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by VARCHAR(255) NOT NULL
);

COMMENT ON TABLE settings IS 'Platform settings with encrypted sensitive values';
COMMENT ON COLUMN settings.key IS 'Setting identifier (e.g. anthropic_api_key)';
COMMENT ON COLUMN settings.value IS 'Setting value (Fernet-encrypted if sensitive)';
COMMENT ON COLUMN settings.encrypted IS 'Whether the value is Fernet-encrypted';
COMMENT ON COLUMN settings.category IS 'UI grouping category';
COMMENT ON COLUMN settings.updated_at IS 'Last update timestamp';
COMMENT ON COLUMN settings.updated_by IS 'User who last updated this setting';

CREATE INDEX IF NOT EXISTS ix_settings_key ON settings (key);
CREATE INDEX IF NOT EXISTS ix_settings_category ON settings (category);
"""

DOWN = """
DROP TABLE IF EXISTS settings;
DROP TYPE IF EXISTS setting_category;
"""
