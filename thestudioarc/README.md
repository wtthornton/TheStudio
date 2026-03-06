# TheStudio

**TheStudio** - Intent in. Proof out.

This repository contains TheStudio architecture documentation for a system that converts GitHub issues into high-quality pull requests using agents, a bench of experts, hard quality gates, and outcome-driven learning.

## Start Here

- `00-overview.md`
- `15-system-runtime-flow.md`

## Key Diagrams

- `assets/master-system-map.svg`
- `assets/overview-agent-platform-planes.svg`
- `assets/runtime-system-flow.svg`
- `assets/runtime-learning-loop.svg`
- `assets/expert-recruiter-creation-flow.svg`
- `assets/expert-router-selection-flow.svg`
- `assets/context-manager-flow.svg`
- `assets/assembler-synthesis-flow.svg`
- `assets/service-context-pack-lifecycle.svg`
- `assets/expert-library-governance.svg`
- `assets/expert-taxonomy-map.svg`

## Standards and Runtime Files

- `20-coding-standards.md`
- `21-project-structure.md`
- `22-architecture-guardrails.md`
- `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `POLICIES.md`, `EVALS.md`

## Admin UI

- `23-admin-control-ui.md`
- `assets/admin-ui-architecture.svg`
- `assets/hybrid-runtime-topology.svg` (global control plane vs per-repo execution planes)

## GitHub standards

See `00-overview.md` and `15-system-runtime-flow.md` for the platform standard label taxonomy, Projects v2 field model, and the PR evidence comment format.
- `assets/role-overlay-enforcement-flow.svg` (role and overlay enforcement)
- `assets/github-control-surface.svg`
- `assets/repo-registration-lifecycle.svg`
- `assets/workflow-idempotency-guard.svg`
- `assets/provenance-minimum-record.svg`

## Operational contract

Operational policies for retries, idempotency, quarantine, QA taxonomy, and repo tier compliance are documented in `15-system-runtime-flow.md`, `POLICIES.md`, `TOOLS.md`, and the gate docs.

## Optional integrations

- `24-openclaw-sidecar.md`

## Tool Hub

- `25-tool-hub-mcp-toolkit.md`
- `assets/tool-hub-mcp-architecture.svg`

## Model runtime

- `26-model-runtime-and-routing.md`
- `assets/model-runtime-and-routing.svg`

## Roadmap

- **MERIDIAN-ROADMAP-AGGRESSIVE.md** — VP Success review of thestudioarc and a high, aggressive roadmap (5 phases, ~40–50 weeks). Bar and success criteria per phase; scope cut before date slip. Meridian is not in charge of delivery; she holds the build to this bar.

## Release

TheStudio Phase 1 (final_phase1)

