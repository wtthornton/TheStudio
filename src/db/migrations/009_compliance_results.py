"""Migration 009: Compliance results table.

Creates the compliance_results table for storing compliance check audit trail.
Required for Story 3.1: Compliance Checker Core Checks.

Architecture reference: thestudioarc/23-admin-control-ui.md
"""

MIGRATION_ID = "009_compliance_results"
DEPENDS_ON = ["008_trust_tier_persistence"]

UP = """
-- Compliance results table for audit trail
CREATE TABLE IF NOT EXISTS compliance_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id UUID NOT NULL REFERENCES repo_profile(id) ON DELETE CASCADE,
    overall_passed BOOLEAN NOT NULL,
    score FLOAT NOT NULL CHECK (score >= 0 AND score <= 100),
    checks JSONB NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    triggered_by VARCHAR(255) NOT NULL
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS ix_compliance_results_repo_id
    ON compliance_results(repo_id);
CREATE INDEX IF NOT EXISTS ix_compliance_results_checked_at
    ON compliance_results(checked_at DESC);
CREATE INDEX IF NOT EXISTS ix_compliance_results_repo_checked
    ON compliance_results(repo_id, checked_at DESC);

-- Comments
COMMENT ON TABLE compliance_results IS
    'Compliance check results — persisted for audit trail (Story 3.1)';
COMMENT ON COLUMN compliance_results.repo_id IS
    'Reference to repo_profile that was checked';
COMMENT ON COLUMN compliance_results.overall_passed IS
    'True if all required checks passed';
COMMENT ON COLUMN compliance_results.score IS
    'Compliance score 0-100 (percentage of checks passed)';
COMMENT ON COLUMN compliance_results.checks IS
    'JSON array of individual check results with pass/fail and remediation hints';
COMMENT ON COLUMN compliance_results.triggered_by IS
    'Who/what triggered this compliance check (for audit)';
"""

DOWN = """
DROP TABLE IF EXISTS compliance_results CASCADE;
"""
