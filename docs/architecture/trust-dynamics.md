# Trust Dynamics Architecture

> Story 2.6: Trust Tier Transitions + Decay + Drift

## Overview

The Trust Dynamics system ensures reputation stays fresh and accurately reflects
expert performance over time. It consists of three interconnected mechanisms:

1. **Trust Tiers**: Discrete reputation states (shadow → probation → trusted)
2. **Decay**: Time-based weight reduction for inactive experts
3. **Drift**: Trend detection triggering tier transitions

## Trust Tiers

### Tier Definitions

| Tier | Description | Thresholds |
|------|-------------|------------|
| `shadow` | New or degraded expert | confidence < 0.3 OR samples < 10 |
| `probation` | Proving reliability | confidence ≥ 0.3 AND samples ≥ 10 |
| `trusted` | Reliable expert | confidence ≥ 0.7 AND samples ≥ 30 AND weight ≥ 0.5 AND drift ≠ declining |

### Tier Computation

```python
def compute_tier(
    weight: float,
    confidence: float,
    samples: int,
    drift: DriftDirection = DriftDirection.STABLE,
) -> TrustTier:
    """Compute tier on write, not read."""
```

The tier is computed each time a weight update occurs. This ensures the persisted
tier is always consistent with the underlying metrics.

### Tier Transitions

Transitions are recorded when the computed tier differs from the current tier:

```python
@dataclass
class TierTransition:
    expert_id: UUID
    context_key: str
    from_tier: TrustTier
    to_tier: TrustTier
    reason: str  # "normal", "sustained_decline", "sustained_improvement"
    timestamp: datetime
```

**Drift-triggered transitions**: After `DRIFT_SUSTAINED_COUNT` (default: 3)
consecutive declining updates, a trusted expert is demoted. Similarly, sustained
improvement can promote a probation expert.

## Decay

### Purpose

Decay ensures that experts who haven't had recent outcomes don't retain stale
high weights indefinitely. It applies exponential decay based on inactivity.

### Decay Formula

```python
decay_factor = max(decay_floor, decay_rate ** days_inactive)

# Defaults:
# - decay_rate: 0.98 (2% per day)
# - decay_floor: 0.5 (minimum 50% retained)
```

For an expert inactive for 30 days:
- decay_factor = 0.98^30 ≈ 0.545
- A weight of 0.8 becomes 0.8 * 0.545 ≈ 0.436

### Decay Scheduler

The `DecayScheduler` runs on a configurable schedule (default: daily) and:

1. Finds experts with `last_outcome_at > decay_period_days`
2. Applies decay to weight and confidence
3. Records decay results for observability

```python
scheduler = DecayScheduler(
    get_inactive_experts=lambda days: [...],
    apply_decay_fn=lambda expert_id, context_key, decayed: ...,
    decay_period_days=7,  # Inactivity threshold
)
```

## Drift

### Purpose

Drift detection identifies whether an expert's performance is trending up, down,
or stable over a rolling window of recent weights.

### Drift Computation

Uses linear regression over the weight history:

```python
def compute_drift(
    weight_history: list[float],
    window_size: int = 10,
    improving_threshold: float = 0.05,
    declining_threshold: float = -0.05,
) -> DriftDirection:
```

| Slope | Direction |
|-------|-----------|
| > 0.05 | `improving` |
| < -0.05 | `declining` |
| otherwise | `stable` |

### Drift Score

A normalized score in [-1, 1] for observability:

```python
drift_score = tanh(slope / 0.05)
```

- `+1.0`: Strong improvement
- `-1.0`: Strong decline
- `0.0`: Stable

## Database Schema

Migration `008_trust_tier_persistence.py` adds:

```sql
-- Enum types
CREATE TYPE trust_tier AS ENUM ('shadow', 'probation', 'trusted');
CREATE TYPE drift_direction AS ENUM ('improving', 'stable', 'declining');

-- New columns on expert_reputation
ALTER TABLE expert_reputation ADD COLUMN trust_tier trust_tier DEFAULT 'shadow';
ALTER TABLE expert_reputation ADD COLUMN tier_changed_at TIMESTAMPTZ;
ALTER TABLE expert_reputation ADD COLUMN last_outcome_at TIMESTAMPTZ;
ALTER TABLE expert_reputation ADD COLUMN drift_direction drift_direction DEFAULT 'stable';
ALTER TABLE expert_reputation ADD COLUMN drift_score FLOAT DEFAULT 0.0;

-- Indexes
CREATE INDEX ix_expert_reputation_trust_tier ON expert_reputation(trust_tier);
CREATE INDEX ix_expert_reputation_last_outcome_at ON expert_reputation(last_outcome_at);
```

## Signal Emission

When a tier transition occurs, the system emits a `trust_tier_changed` signal:

```python
{
    "event": "trust_tier_changed",
    "expert_id": "uuid",
    "context_key": "repo:project:complexity",
    "from_tier": "probation",
    "to_tier": "trusted",
    "reason": "normal",
    "timestamp": "2026-03-06T..."
}
```

The Router can subscribe to these signals to adjust expert selection immediately.

## Integration Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ ReputationIndicator │ │   engine.py     │     │   Database      │
│   (from Outcome     │────►  update_weight() ────► persist tier  │
│    Ingestor)    │     │   - compute_tier │     │   last_outcome  │
└─────────────────┘     │   - compute_drift│     │   drift_score   │
                        └─────────────────┘     └─────────────────┘
                                │
                                ▼ (if tier changed)
                        ┌─────────────────┐
                        │ trust_tier_changed │
                        │     signal      │
                        └─────────────────┘

┌─────────────────┐     ┌─────────────────┐
│  DecayScheduler │     │   Database      │
│   (cron/daily)  │────► apply_decay()   │
│                 │     │  - reduce weight │
│                 │     │  - reduce conf   │
└─────────────────┘     └─────────────────┘
```

## Test Coverage (26 tests)

| Category | Tests |
|----------|-------|
| Tier computation | 5 |
| Tier transitions | 5 |
| Decay computation | 4 |
| Decay scheduler | 3 |
| Drift computation | 5 |
| Drift score | 3 |
| Drift for expert | 1 |

## References

- Architecture: `thestudioarc/06-reputation-engine.md` (lines 70-110)
- Phase 2 spec: `thestudioarc/MERIDIAN-ROADMAP-AGGRESSIVE.md` (lines 108-135)
- Sprint plan: `docs/plans/epic-2-sprint-2-plan.md`
