# 24 — OpenClaw Sidecar Integration (Optional)

## Purpose

Describe how OpenClaw can connect to the platform as an optional sidecar in later phases, without becoming a dependency or a source of truth.

## Intent

The intent is to allow richer interaction surfaces and optional centralized tool brokering while keeping the core platform fully functional without OpenClaw.

The platform must run 100% without OpenClaw:
- GitHub webhooks start workflows through the Ingress Service
- Temporal, Postgres, JetStream, tool servers, verification, QA, and Publisher remain the system rails
- only Publisher writes to GitHub

## Where OpenClaw fits

OpenClaw can be added as a sidecar that provides:
- an interactive operator console for humans (beyond GitHub comments)
- optional multi-channel inputs (Slack, Teams, web chat)
- optional tool brokering for high-risk tools (if desired)
- consistent RBAC and audit logging surface aligned to Admin API

OpenClaw does not:
- own workflow state
- store TaskPackets or intent as source of truth
- write to GitHub directly

## Integration patterns

Phase 3: Operator console
- OpenClaw connects to Admin API to read status and issue control actions
- OpenClaw can display TaskPacket, intent, plan, provenance, and signals
- OpenClaw actions are audited through Admin API

Phase 4: Optional tool broker (high-risk calls only)
- Primary Agent requests high-risk tool calls through OpenClaw
- OpenClaw enforces role and overlay policy, budgets, and correlation id requirements
- OpenClaw forwards to tool servers
- most read-only tools remain direct to tool servers

## Guardrails

- OpenClaw never receives GitHub write credentials
- OpenClaw never stores secrets beyond transient request context
- OpenClaw must not become a hidden state store; all durable state is in Postgres and Temporal
