# Ralph Agent Configuration — TheStudio

## Build Instructions

### Backend (Python)
```bash
pip install -e ".[dev]"
```

### Frontend (React/TypeScript)
```bash
cd frontend && npm install
```

## Test Instructions

> **EPIC-BOUNDARY ONLY:** Do NOT run tests mid-epic. Only run at epic boundaries
> (last `- [ ]` in a `##` section of fix_plan.md) or before EXIT_SIGNAL: true.
> Mid-epic: set `TESTS_STATUS: DEFERRED` and move on.

### Backend
```bash
pytest
pytest tests/unit/test_something.py -v
```

### Frontend
```bash
cd frontend && npm test
cd frontend && npm run test -- --run  # single run, no watch
```

## Lint & Format

> **EPIC-BOUNDARY ONLY:** Same rule — defer lint/type checks to epic boundaries.

### Backend
```bash
ruff check .
ruff format .
mypy src/
```

### Frontend
```bash
cd frontend && npm run typecheck
cd frontend && npm run lint
```

## Build (Frontend)
```bash
cd frontend && npm run build
```

## Development Server

### Backend
```bash
uvicorn src.app:app --reload
```

### Frontend
```bash
cd frontend && npm run dev
```

## Code Quality Requirements

### Backend
- Python 3.12+, FastAPI, Pydantic, async SQLAlchemy
- Structured logging with correlation_id
- Type annotations on public interfaces
- **QA runs at epic boundaries only — not after every task**

### Frontend
- React 19, TypeScript strict mode, Zustand 5, Tailwind CSS v4
- No `any` types in committed code
- **QA runs at epic boundaries only — not after every task**

## Feature Completion Checklist (EPIC BOUNDARY ONLY)

This checklist applies ONLY at epic boundaries (last task in a `##` section) or before EXIT_SIGNAL: true. Mid-epic tasks just need implementation + commit.

**Mid-epic task:**
- [ ] Implementation matches the acceptance criteria in fix_plan.md
- [ ] Changes committed with descriptive message
- [ ] fix_plan.md updated: `- [ ]` → `- [x]`

**Epic boundary (last task in section):**
- [ ] All above, plus:
- [ ] Tests pass: `pytest` (backend) and/or `cd frontend && npm test` (frontend)
- [ ] Lint passes: `ruff check .` (backend) and/or `npm run lint` (frontend)
- [ ] Type check passes: `mypy src/` (backend) and/or `npm run typecheck` (frontend)

## Key Learnings
- Update this section when you learn new build optimizations
- Document any gotchas or special setup requirements
