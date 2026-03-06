# Complexity Index v1

**Version:** 1.0
**Date:** 2026-03-06
**Story:** 2.1 (Epic 2 — Learning + Multi-Repo)

---

## Purpose

The Complexity Index quantifies task difficulty for fair outcome normalization in the learning loop. Without complexity normalization, hard tasks would unfairly penalize expert reputation, and easy tasks would inflate it.

## Dimensions

| Dimension | Description | Source | Range |
|-----------|-------------|--------|-------|
| `scope_breadth` | Number of files/components likely modified | ScopeResult.affected_files_estimate | 1–3 (1=single file, 2=few files, 3=cross-module) |
| `risk_flag_count` | Count of risk labels on the issue | risk_flags dict | 0–6 |
| `dependency_count` | Number of external dependencies touched | ScopeResult.components (heuristic) | 0–10 |
| `lines_estimate` | Estimated lines changed | Derived from scope and complexity | 0–500+ |
| `expert_coverage` | Count of expert classes required | EffectiveRolePolicy.mandatory_expert_classes | 0–5 |

## Formula

```
complexity_score = (
    scope_breadth * 2.0
    + risk_flag_count * 3.0
    + dependency_count * 1.0
    + (lines_estimate / 50.0)
    + expert_coverage * 1.5
)
```

**Weights rationale:**
- Risk flags have highest weight (3.0) — they indicate compliance, security, or governance concerns
- Scope breadth is moderately weighted (2.0) — multi-file changes are harder than single-file
- Expert coverage is moderately weighted (1.5) — more experts = more coordination overhead
- Dependencies and lines are lower weighted (1.0, 0.02 per line) — these are softer signals

## Bands

| Band | Score Range | Description |
|------|-------------|-------------|
| `low` | 0.0 – 5.0 | Simple, single-file change with no risk flags |
| `medium` | 5.1 – 12.0 | Multi-file or has 1 risk flag or requires experts |
| `high` | 12.1+ | Cross-module, multiple risk flags, or governance-sensitive |

## Schema

The ComplexityIndex is stored as JSONB on the TaskPacket:

```json
{
  "score": 8.5,
  "band": "medium",
  "dimensions": {
    "scope_breadth": 2,
    "risk_flag_count": 1,
    "dependency_count": 3,
    "lines_estimate": 75,
    "expert_coverage": 1
  }
}
```

## Usage

### Outcome Ingestor (normalization)

When normalizing verification/QA outcomes:
- **High complexity:** Failures are weighted less negatively; successes are weighted more positively
- **Low complexity:** Failures and successes have standard weight
- **Formula:** `normalized_weight = raw_weight * complexity_multiplier(band)`

### Reputation Engine (fair attribution)

When attributing outcomes to experts:
- High-complexity success → stronger positive signal
- High-complexity failure → weaker negative signal (task was hard)
- Low-complexity failure → stronger negative signal (task was easy)

### Reporting and Admin UI

Complexity Index enables:
- Fair comparison of single-pass success rates across repos with different task distributions
- Identification of repos that consistently receive high-complexity tasks
- Expert performance normalized by difficulty

## Migration

The `complexity_index` column changes from `VARCHAR(20)` (v0 band only) to `JSONB` (v1 full structure). The migration:
1. Adds a new `complexity_index_v1` JSONB column
2. Migrates existing band values to `{"score": null, "band": "<value>", "dimensions": null}` format
3. Drops the old `complexity_index` column
4. Renames `complexity_index_v1` to `complexity_index`

---

*Architecture document for Complexity Index v1. See thestudioarc/12-outcome-ingestor.md for usage in learning loop.*
