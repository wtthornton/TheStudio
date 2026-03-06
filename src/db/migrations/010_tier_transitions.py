"""Migration 010: Tier transitions audit table.

Creates the tier_transitions table for storing tier promotion/demotion audit trail.
Required for Story 3.3: Execute Tier Promotion Gate.

Architecture reference: thestudioarc/23-admin-control-ui.md
"""

MIGRATION_ID = "010_tier_transitions"
DEPENDS_ON = ["009_compliance_results"]

UP = """
-- Tier transitions audit table
CREATE TABLE IF NOT EXISTS tier_transitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id UUID NOT NULL REFERENCES repo_profile(id) ON DELETE CASCADE,
    from_tier VARCHAR(50) NOT NULL,
    to_tier VARCHAR(50) NOT NULL,
    triggered_by VARCHAR(255) NOT NULL,
    compliance_score FLOAT,
    compliance_result_id UUID REFERENCES compliance_results(id) ON DELETE SET NULL,
    reason TEXT NOT NULL,
    transitioned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS ix_tier_transitions_repo_id
    ON tier_transitions(repo_id);
CREATE INDEX IF NOT EXISTS ix_tier_transitions_transitioned_at
    ON tier_transitions(transitioned_at DESC);
CREATE INDEX IF NOT EXISTS ix_tier_transitions_repo_time
    ON tier_transitions(repo_id, transitioned_at DESC);

-- Comments
COMMENT ON TABLE tier_transitions IS
    'Tier transition audit trail — records all tier promotions and demotions (Story 3.3)';
COMMENT ON COLUMN tier_transitions.from_tier IS
    'Tier before transition (observe, suggest, execute)';
COMMENT ON COLUMN tier_transitions.to_tier IS
    'Tier after transition (observe, suggest, execute)';
COMMENT ON COLUMN tier_transitions.triggered_by IS
    'Who/what triggered this transition (for audit)';
COMMENT ON COLUMN tier_transitions.compliance_score IS
    'Compliance score at time of transition (null for demotions)';
COMMENT ON COLUMN tier_transitions.compliance_result_id IS
    'Reference to compliance check that enabled this transition';
COMMENT ON COLUMN tier_transitions.reason IS
    'Reason for transition (promotion reason or demotion justification)';
"""

DOWN = """
DROP TABLE IF EXISTS tier_transitions CASCADE;
"""
