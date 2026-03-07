"""Migration 012: Tool catalog tables.

Creates tool_suites, tool_entries, and tool_profiles tables
for persisting the Tool Hub catalog.

Story 8.8: PostgreSQL Implementations — 3 Critical Stores
Architecture reference: thestudioarc/25-tool-hub-mcp-toolkit.md
"""

MIGRATION_ID = "012_tool_catalog"
DEPENDS_ON = ["011_repo_profile_admin_ui"]

UP = """
-- Tool suites table
CREATE TABLE IF NOT EXISTS tool_suites (
    name VARCHAR(255) PRIMARY KEY,
    description TEXT NOT NULL DEFAULT '',
    approval_status VARCHAR(20) NOT NULL DEFAULT 'observe'
        CHECK (approval_status IN ('observe', 'suggest', 'execute')),
    version VARCHAR(50) NOT NULL DEFAULT '1.0.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tool entries table (belongs to a suite)
CREATE TABLE IF NOT EXISTS tool_entries (
    id SERIAL PRIMARY KEY,
    suite_name VARCHAR(255) NOT NULL REFERENCES tool_suites(name) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    capability VARCHAR(50) NOT NULL,
    read_only BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (suite_name, name)
);

-- Tool profiles table (maps repos to suites)
CREATE TABLE IF NOT EXISTS tool_profiles (
    profile_id VARCHAR(255) PRIMARY KEY,
    repo_id VARCHAR(255) NOT NULL,
    enabled_suites JSONB NOT NULL DEFAULT '[]',
    tier_scope VARCHAR(20) NOT NULL DEFAULT 'observe'
);

CREATE INDEX IF NOT EXISTS ix_tool_entries_suite ON tool_entries(suite_name);
CREATE INDEX IF NOT EXISTS ix_tool_profiles_repo ON tool_profiles(repo_id);

COMMENT ON TABLE tool_suites IS 'Tool Hub suite registry (Story 8.8)';
COMMENT ON TABLE tool_entries IS 'Individual tools within a suite';
COMMENT ON TABLE tool_profiles IS 'Repo-to-suite mapping with tier scope';
"""

DOWN = """
DROP TABLE IF EXISTS tool_profiles CASCADE;
DROP TABLE IF EXISTS tool_entries CASCADE;
DROP TABLE IF EXISTS tool_suites CASCADE;
"""
