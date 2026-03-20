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
- Run `ruff check . && mypy src/` before committing

### Frontend
- React 19, TypeScript strict mode, Zustand 5, Tailwind CSS v4
- No `any` types in committed code
- Run `npm run typecheck && npm run lint` before committing

## Feature Completion Checklist

Before marking ANY task as complete, verify:

- [ ] Implementation matches the acceptance criteria in fix_plan.md
- [ ] Tests pass: `pytest` (backend) and/or `cd frontend && npm test` (frontend)
- [ ] Lint passes: `ruff check .` (backend) and/or `npm run lint` (frontend)
- [ ] Type check passes: `mypy src/` (backend) and/or `npm run typecheck` (frontend)
- [ ] Changes committed with descriptive message
- [ ] fix_plan.md updated: `- [ ]` → `- [x]`

## Key Learnings
- Update this section when you learn new build optimizations
- Document any gotchas or special setup requirements
