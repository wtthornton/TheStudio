# Contributing to TheStudio

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Docker & Docker Compose (for full stack)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd thestudio

# Install with dev dependencies
pip install -e '.[dev]'

# Or with uv
uv sync --all-extras
```

### Running Tests

```bash
pytest
pytest --cov=src          # with coverage
pytest tests/unit/        # unit tests only
pytest tests/integration/ # integration tests only
```

### Running the Server

```bash
uvicorn src.app:app --reload
```

## Coding Standards

Full standards: [thestudioarc/20-coding-standards.md](thestudioarc/20-coding-standards.md)

### Tooling

| Tool | Purpose |
|------|---------|
| **Ruff** | Linting and formatting (single tool surface) |
| **pytest** | Testing framework |
| **mypy** | Type checking |
| **bandit** | Security scanning |
| **pip-audit** | Dependency vulnerability scanning |
| **pre-commit** | Local enforcement hooks |

### Key Rules

- **Ruff lint + format** on all Python files before commit
- **Type hints** on all public function signatures
- **Docstrings** on all public classes and functions
- **Correlation IDs** propagated through all async operations
- **No secrets in code** — use environment variables and Fernet encryption at rest
- **Small diffs** — prefer focused, evidence-backed changes

### Architecture Guardrails

See [thestudioarc/22-architecture-guardrails.md](thestudioarc/22-architecture-guardrails.md):

- Intent is the definition of correctness
- Verification and QA gates fail closed
- Agents communicate through artifacts and signals, not free-form chat
- Prefer small diffs and clear evidence

## Pull Request Workflow

1. Create a feature branch from `master`
2. Make focused changes with clear commit messages
3. Run `ruff check --fix .` and `ruff format .`
4. Run `pytest` and ensure all tests pass
5. Open a PR using the [PR template](.github/PULL_REQUEST_TEMPLATE.md)
6. Ensure CI checks pass

### Commit Message Format

Follow the project convention:

```
Epic N Sprint M: Brief description of changes

# or for smaller changes:
feat(module): Description
fix(module): Description
docs: Description
```

### PR Requirements

- All CI checks pass (lint, type check, tests, security scan)
- No decrease in test coverage
- API changes reflected in `docs/API_REFERENCE.md`
- Architecture-impacting changes discussed in an epic first

## Reporting Issues

When reporting issues, please include:

- A clear and descriptive title
- Steps to reproduce the problem
- Expected behavior vs actual behavior
- Your environment (OS, Python version, etc.)

Please use the provided [issue templates](.github/ISSUE_TEMPLATE/) when applicable.

## Quality Pipeline

This project uses TappsMCP for automated quality enforcement. After editing Python files:

1. Run `tapps_quick_check(file_path)` per file
2. Run `tapps_validate_changed()` before declaring work complete
3. Run `tapps_checklist(task_type)` as final verification

## Project Personas

| Persona | Role | When to Use |
|---------|------|-------------|
| **Saga** | Epic Creator | Creating/editing epics |
| **Helm** | Planner & Dev Manager | Sprint planning, backlog ordering |
| **Meridian** | VP Success (Reviewer) | Reviewing epics and plans before commit |

See [thestudioarc/personas/TEAM.md](thestudioarc/personas/TEAM.md) for full details.
