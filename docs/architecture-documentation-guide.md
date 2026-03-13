# How TheStudio Architecture Documentation Was Created

A guide for replicating this documentation approach in other projects.

## Overview

TheStudio's architecture documentation is a set of 25+ interconnected Markdown files organized in a numbered sequence (`00-overview.md` through `26-model-runtime-and-routing.md`), plus supporting policy, standards, and persona files. The documents describe an AI-augmented software delivery platform using structured prose, tables, ASCII-style flow descriptions, and SVG diagram placeholders.

## Documentation Structure

### Numbered Document Sequence

Each document follows a consistent template:

```
# NN - Title

## Purpose
What this component does and why it exists.

## Intent
What correctness means for this component.

## Plane Placement
Agent Plane vs Platform Plane responsibilities.

## Key Inputs / Key Outputs
Data contracts.

## Internal Flow
Step-by-step numbered flow description.

## Diagram
![Diagram Name](assets/diagram-name.svg)

## Admin UI Integration
How this component exposes status to the admin layer.
```

### File Organization

```
thestudioarc/
  00-overview.md              # System overview and master index
  01-expert-bench-architecture.md
  02-expert-taxonomy.md
  03-context-manager.md       # through 15-system-runtime-flow.md
  20-coding-standards.md      # Standards block (20-22)
  23-admin-control-ui.md      # Extensions (23-26)
  assets/                     # SVG diagrams (referenced, generated separately)
  personas/                   # Agent persona definitions
  epics/                      # Work epics and stories
  examples/                   # Walkthrough scenarios
  SOUL.md                     # Core operating principles
  TOOLS.md                    # Tool governance
  POLICIES.md                 # Policy definitions
  EVALS.md                    # Evaluation criteria
  AGENTS.md                   # Agent configuration
```

### Cross-Referencing

Documents reference each other by filename (e.g., "See `08-agent-roles.md`") and share a common vocabulary defined in `00-overview.md` (Core System Artifacts section). This creates a navigable web without requiring a wiki engine.

## Tools and Technologies Used

### Documentation Authoring

| Tool | Purpose | Notes |
|------|---------|-------|
| **Markdown** (CommonMark / GFM) | All documentation | Plain `.md` files, no proprietary format |
| **Git** | Version control | Docs live alongside code in the same repo |
| **VS Code / Cursor** | Editor | Any Markdown editor works |
| **AI assistants** (Claude) | Co-authoring | Used to draft, review, and iterate on architecture docs |

### Diagram Approach

The architecture references **SVG diagrams** stored in an `assets/` directory. The diagrams are referenced in Markdown using standard image syntax:

```markdown
![Master Architecture Map](assets/master-system-map.svg)
```

Recommended tools for creating the SVGs:

| Tool | Type | Best For |
|------|------|----------|
| **Mermaid** | Text-to-diagram | Flowcharts, sequence diagrams, state machines. Renders in GitHub natively. |
| **D2** | Text-to-diagram | Complex architecture diagrams with better layout control than Mermaid |
| **Excalidraw** | Hand-drawn style | Whiteboard-style diagrams, exports to SVG |
| **draw.io / diagrams.net** | GUI editor | Detailed infrastructure and deployment topology diagrams |
| **PlantUML** | Text-to-diagram | Sequence diagrams and class diagrams |

### Project Tech Stack (what the docs describe)

| Technology | Version | Role in System |
|------------|---------|----------------|
| **Python** | 3.12+ | Primary language |
| **FastAPI** | 0.115+ | HTTP API framework, tool servers |
| **Pydantic** | 2.10+ | Data validation, settings, domain models |
| **SQLAlchemy** (async) | 2.0+ | ORM and database access |
| **asyncpg** | 0.30+ | PostgreSQL async driver |
| **PostgreSQL** | 16 | Primary database (with pgvector for retrieval) |
| **Temporal** | 1.25+ (server), 1.9+ (Python SDK) | Durable workflow orchestration and loopbacks |
| **NATS JetStream** | 2.10+ | Signal stream (verification, QA, outcome events) |
| **OpenTelemetry** | 1.29+ | Distributed tracing, metrics, logging |
| **httpx** | 0.28+ | Async HTTP client |
| **Claude Agent SDK** | 0.1.40+ | AI agent execution |
| **Jinja2** | 3.1+ | Template rendering |
| **slowapi** | 0.1.9+ | Rate limiting |
| **cryptography** | 44.0+ | Encryption (secrets, tokens) |
| **Ruff** | 0.8+ | Linting and formatting (single tool) |
| **pytest** | 8.3+ | Testing framework |
| **mypy** | 1.14+ | Static type checking |
| **Playwright** | 1.49+ | Browser-based E2E testing |
| **bandit** | 1.8+ | Security scanning |
| **pip-audit** | 2.7+ | Dependency vulnerability scanning |
| **Docker Compose** | - | Local dev and production deployment |
| **Hatchling** | - | Python build backend |

### Infrastructure (Docker Compose Stack)

```
PostgreSQL 16-alpine     -> Primary DB + Temporal backend
Temporal 1.25            -> Durable workflow engine
Temporal UI              -> Workflow visibility dashboard
NATS 2.10-alpine         -> JetStream signal stream
FastAPI app              -> Platform API (port 8000)
```

## How to Replicate This Approach

### 1. Start with `00-overview.md`

Write a single overview document that:
- States what the system does in one sentence
- Lists core artifacts and domain objects
- Provides a documentation map (numbered file list)
- References the master architecture diagram

### 2. Number Your Documents

Use a numbering scheme that groups related concerns:
- `00-09`: Core architecture (overview, key subsystems)
- `10-19`: Domain-specific layers (intent, verification, QA, outcomes)
- `20-29`: Standards, guardrails, tooling, infrastructure

### 3. Use the Purpose/Intent Pattern

Every document answers:
- **Purpose**: What does this component do?
- **Intent**: What does correctness look like?

This pattern was inspired by the system's own "Intent Specification" concept -- defining correctness before implementation.

### 4. Separate Agent Plane from Platform Plane

Each document identifies whether the component provides:
- **Judgment and synthesis** (Agent Plane)
- **Durability, enforcement, and evidence** (Platform Plane)

This separation prevents conversational AI state from becoming the source of truth.

### 5. Define Personas for Human Processes

The `personas/` directory defines structured roles for epic creation, sprint planning, and review. Each persona has:
- A clear responsibility boundary
- A structured output format
- A review checklist

### 6. Keep Docs in the Repo

All documentation lives in the same Git repository as the code. This ensures:
- Docs are versioned with the code
- PRs can include doc changes alongside code changes
- No external wiki to fall out of sync

### 7. Enforce with AI

The documentation set itself was iteratively created and reviewed using AI assistants (Claude), with human review at each stage. The persona chain (Saga -> Meridian -> Helm -> Meridian) provides a structured review workflow.

## Key Design Decisions

1. **Markdown over wikis** -- portable, versionable, reviewable in PRs
2. **Numbered files over nested folders** -- flat discovery, clear reading order
3. **SVG placeholders** -- diagrams referenced before they exist, filled in iteratively
4. **Consistent template** -- every doc follows Purpose/Intent/Flow/Diagram structure
5. **Cross-referencing by filename** -- no links that break, just `See 08-agent-roles.md`
6. **Personas as docs** -- human processes documented with the same rigor as system architecture
7. **Co-authored with AI** -- Claude used for drafting, iterating, and reviewing; human for final approval
