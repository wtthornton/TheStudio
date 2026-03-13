"""Readiness gate — scores issue quality before intent building.

Inserted between Context (step 2) and Intent (step 3) in the pipeline.
Controlled by `readiness_gate_enabled` feature flag (defaults to off).
"""
