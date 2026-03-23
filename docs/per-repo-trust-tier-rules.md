# Per-Repo Trust Tier Rules

## Overview

TheStudio's trust tier engine evaluates operator-defined rules against each `TaskPacket`
and assigns an action tier (Observe → Suggest → Execute). Every `TaskPacket` carries a
`repo` field containing the repository's full name (`owner/repo_name`). Because the trust
engine resolves fields using **dot-notation** against the packet's attributes, you can write
rules that match on the `repo` field just like any other packet metadata.

No code changes are required — the engine already supports this pattern.

---

## How Field Resolution Works

The trust engine calls `_resolve_field(packet, field_path)` for each condition.
Dot-notation is used to traverse nested dicts. For top-level scalar fields (including
`repo`), the field name is used directly:

```
field: "repo"  →  packet.repo  (e.g. "acme-corp/backend-api")
```

Supported operators for string fields:

| Operator | Description |
|----------|-------------|
| `equals` | Exact match (`repo == "acme-corp/backend-api"`) |
| `not_equals` | Exact non-match |
| `contains` | Substring match (`"acme-corp" in repo`) |
| `matches_glob` | fnmatch glob (`"acme-corp/*"`) |

---

## Example Rules

### Example 1: Force OBSERVE for a specific repo

Use this when you want a newly onboarded repo to stay at Observe indefinitely
regardless of other conditions.

```json
{
  "priority": 1,
  "conditions": [
    {
      "field": "repo",
      "op": "equals",
      "value": "acme-corp/new-repo"
    }
  ],
  "assigned_tier": "observe",
  "active": true,
  "description": "Force acme-corp/new-repo to Observe until onboarding complete"
}
```

**Effect**: Any TaskPacket from `acme-corp/new-repo` matches this rule first (priority 1)
and receives `OBSERVE`, regardless of complexity or risk.

---

### Example 2: Allow SUGGEST for a repo when complexity is low

Use this when a repo has been stable for several weeks and you want to promote it
to Suggest tier for simple tasks.

```json
{
  "priority": 50,
  "conditions": [
    {
      "field": "repo",
      "op": "equals",
      "value": "acme-corp/backend-api"
    },
    {
      "field": "complexity_index.score",
      "op": "less_than",
      "value": 0.5
    }
  ],
  "assigned_tier": "suggest",
  "active": true,
  "description": "Allow backend-api to SUGGEST when complexity < 0.5"
}
```

**Effect**: A TaskPacket from `backend-api` with `complexity_index.score = 0.3` matches and
receives `SUGGEST`. A packet from the same repo with `complexity_index.score = 0.7` falls
through to the next rule (or the default tier).

---

### Example 3: EXECUTE for a trusted repo with no risk flags

Use this for mature repos in the Execute tier where you trust automated PR merges.

```json
{
  "priority": 100,
  "conditions": [
    {
      "field": "repo",
      "op": "equals",
      "value": "acme-corp/tooling"
    },
    {
      "field": "complexity_index.score",
      "op": "less_than",
      "value": 0.3
    }
  ],
  "assigned_tier": "execute",
  "active": true,
  "description": "Auto-merge tooling PRs when complexity is very low"
}
```

---

### Example 4: Cap an entire GitHub org to SUGGEST

If you manage multiple repos under one org and want to cap the entire org at Suggest
while individual repo rules can still promote within that cap:

```json
{
  "priority": 500,
  "conditions": [
    {
      "field": "repo",
      "op": "matches_glob",
      "value": "acme-corp/*"
    }
  ],
  "assigned_tier": "suggest",
  "active": true,
  "description": "Cap all acme-corp repos at SUGGEST until Execute promotion policy is approved"
}
```

Note: This rule has priority 500 (lower priority than individual repo rules), so specific
repo rules can still assign Observe or Suggest for their own repos. It prevents any repo
in `acme-corp/*` from reaching Execute unless a higher-priority (lower number) rule
explicitly assigns Execute first.

---

## Rule Evaluation Order

1. Rules are evaluated in ascending `priority` order (lower number = evaluated first).
2. **First match wins** — evaluation stops after the first rule whose ALL conditions pass.
3. Safety bounds are applied after rule matching — they can cap the tier downward but
   never promote it.
4. If no rule matches, the `default_tier` (configured in Safety Bounds) is used.

---

## Registering Rules

Use the Trust Tier Configuration API:

```bash
# Create a new rule
curl -X POST http://localhost:8000/api/v1/dashboard/trust/rules \
  -H "Content-Type: application/json" \
  -d '{
    "priority": 50,
    "conditions": [
      {"field": "repo", "op": "equals", "value": "acme-corp/backend-api"},
      {"field": "complexity_index.score", "op": "less_than", "value": 0.5}
    ],
    "assigned_tier": "suggest",
    "description": "Allow backend-api SUGGEST for simple tasks"
  }'

# List all active rules
curl http://localhost:8000/api/v1/dashboard/trust/rules?active_only=true
```

Rules can also be managed in the **Trust Tiers** tab of the dashboard UI.

---

## Recommended Rule Ordering

A multi-repo deployment should follow this rule priority ladder:

| Priority Range | Purpose |
|---------------|---------|
| 1–9 | Emergency overrides (force OBSERVE, block specific repos) |
| 10–99 | Per-repo Execute promotions (specific repos, specific conditions) |
| 100–499 | Per-repo Suggest promotions (moderate-confidence cases) |
| 500–999 | Org-level caps and blanket fallbacks |
| 1000+ | Default catch-all (usually unnecessary — use `default_tier` instead) |

---

## Safety Bounds Interaction

Safety bounds cap the tier for any task that breaches a threshold (e.g.,
`max_auto_merge_lines`, `max_loopbacks`). A per-repo rule can assign `EXECUTE` but
safety bounds will reduce it to `SUGGEST` if the task exceeds the bound. This is by
design — safety bounds are a fleet-wide guardrail that no rule can bypass.
