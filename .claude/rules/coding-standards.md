---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
description: "Python coding standards for TheStudio"
---

# Coding Standards

- Type annotations on public interfaces; explicit return types
- Structured logging with correlation_id on all spans
- Explicit exceptions with context; no bare except
- Async only when needed; don't mix sync/async in same module
- Small, single-purpose functions; no global mutable state
- Ruff for lint + format (single tool surface)
- Tests in tests/unit/ mirror src/ structure; fixtures in conftest.py
- 84% coverage baseline — new code must maintain or improve

Reference: `thestudioarc/20-coding-standards.md`
