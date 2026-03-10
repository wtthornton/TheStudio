---
description: "TheStudio 9-step pipeline awareness"
---

# Pipeline Stage Mapping

When editing files, know which pipeline stage you're in:

| Directory | Stage | Upstream | Downstream |
|---|---|---|---|
| src/intake/ | 1. Intake | GitHub webhook | Context Manager |
| src/context/ | 2. Context | Intake | Intent Builder |
| src/intent/ | 3. Intent | Context | Router |
| src/routing/ | 4. Router | Intent | Assembler |
| src/assembler/ | 5. Assembler | Router + Experts | Primary Agent |
| src/agent/ | 6. Implement | Assembler | Verification |
| src/verification/ | 7. Verify | Primary Agent | QA Agent |
| src/qa/ | 8. QA | Verification | Publisher |
| src/publisher/ | 9. Publish | QA | GitHub (draft PR) |

Cross-cutting: src/models/ (TaskPacket), src/reputation/, src/outcome/, src/observability/, src/db/

Key invariant: Gates fail closed. Loopbacks carry evidence. TaskPacket is the single source of truth.
