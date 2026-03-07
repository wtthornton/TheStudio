"""Migration 013: Model call audit table.

Creates the model_call_audit table for persisting LLM call audit records.

Story 8.8: PostgreSQL Implementations — 3 Critical Stores
Architecture reference: thestudioarc/26-model-runtime-and-routing.md
"""

MIGRATION_ID = "013_model_audit"
DEPENDS_ON = ["012_tool_catalog"]

UP = """
CREATE TABLE IF NOT EXISTS model_call_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_id UUID,
    task_id UUID,
    step VARCHAR(100) NOT NULL DEFAULT '',
    role VARCHAR(100) NOT NULL DEFAULT '',
    overlays JSONB NOT NULL DEFAULT '[]',
    provider VARCHAR(100) NOT NULL DEFAULT '',
    model VARCHAR(100) NOT NULL DEFAULT '',
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    cost DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    latency_ms DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    error_class VARCHAR(100),
    fallback_chain JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_model_audit_task_id ON model_call_audit(task_id);
CREATE INDEX IF NOT EXISTS ix_model_audit_step ON model_call_audit(step);
CREATE INDEX IF NOT EXISTS ix_model_audit_provider ON model_call_audit(provider);
CREATE INDEX IF NOT EXISTS ix_model_audit_created_at ON model_call_audit(created_at DESC);

COMMENT ON TABLE model_call_audit IS 'LLM call audit trail (Story 8.8)';
"""

DOWN = """
DROP TABLE IF EXISTS model_call_audit CASCADE;
"""
