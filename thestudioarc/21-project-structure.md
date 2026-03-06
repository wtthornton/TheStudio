# 21 — Project Structure (AI-Coded OSS Python)

## Purpose

Define a predictable project structure that scales to many services and tool servers while staying easy for agents to navigate. The structure must reduce ambiguity, avoid spaghetti coupling, and support progressive disclosure.

## Intent

AI-coded projects fail when structure is inconsistent. The intent is to:
- make discovery deterministic for the Context Manager
- make implementation predictable for the Primary Agent
- make review and QA validation straightforward
- support hundreds of services without requiring a service expert for each

---

## Monorepo Layout (recommended for multi-service systems)

Top-level structure:

- docs/                  architecture and runbooks
- agents/                agent skill packs and agent configuration
- tools/                 tool servers (FastAPI) and shared tool libs
- services/              product services (FastAPI, workers, jobs)
- libs/                  shared libraries, strongly versioned
- infra/                 local dev compose, deploy manifests
- .github/               workflows, issue templates

---

## Service Layout (FastAPI service)

- src/
  - api/                 routers, request/response models
  - domain/              domain logic, business rules
  - services/            orchestration logic
  - repositories/        persistence boundaries
  - integrations/        partner APIs
  - observability/       otel init, logging, metrics
  - settings.py          config and pydantic settings
- tests/
  - unit/
  - integration/
- pyproject.toml
- README.md

FastAPI reference for splitting into multiple files: https://fastapi.tiangolo.com/tutorial/bigger-applications/

---

## Tool Server Layout (FastAPI)

- src/
  - endpoints/           tool endpoints
  - adapters/            API clients (GitHub, CI)
  - policy/              allowlist checks and validation
  - logging/             structured logging
- tests/
- pyproject.toml

---

## Documentation Conventions

- Each service should have a Service Context Pack (or be covered by a shared pack) in docs/service-packs/
- Each pack includes:
  - purpose and invariants
  - key APIs and contracts
  - failure modes and runbooks
  - dependencies and consumers

## Agent-Friendly Conventions

- keep src layout consistent across services
- name modules by purpose, not by person or team
- avoid circular imports and hidden side effects
- keep a README per service describing purpose, invariants, and run commands
- store Service Context Packs in a predictable location so Context Manager can always find them
