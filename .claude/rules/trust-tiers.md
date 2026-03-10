---
paths:
  - "src/publisher/**"
  - "src/compliance/**"
  - "src/repo/**"
description: "Trust tier governance rules"
---

# Trust Tiers

- **Observe** — Read-only. No PR writes. Build visibility signals.
- **Suggest** — Draft PR only. Guarded writes. No ready-for-review until verification + QA pass.
- **Execute** — Full workflow. Compliance-checked. Human merge by default.

Publisher behavior is tier-gated. Never bypass tier checks.
Promotion requires explicit lifecycle gates + compliance health checks.
