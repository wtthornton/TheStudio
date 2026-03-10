---
description: "TAPPS quality pipeline"
---

# TAPPS Quality Pipeline

Call `tapps_session_start()` as the first action in every session.
Call `tapps_lookup_docs(library, topic)` before using any external library API.
Call `tapps_quick_check(file_path)` after editing any Python file.
Call `tapps_validate_changed(file_paths="...")` before declaring work complete. Always pass explicit file_paths.
Call `tapps_checklist(task_type)` as the final verification step.
Call `tapps_consult_expert(question)` for domain-specific decisions.
Call `tapps_impact_analysis(file_path)` before refactoring or deleting files.

## 5-Stage Pipeline

1. **Discover** — `tapps_session_start()`, consider `tapps_memory(action="search")` for project context
2. **Research** — `tapps_lookup_docs()` for libraries, `tapps_consult_expert()` for decisions
3. **Develop** — `tapps_score_file(file_path, quick=True)` during edit-lint-fix loops
4. **Validate** — `tapps_quick_check()` per file OR `tapps_validate_changed()` for batch
5. **Verify** — `tapps_checklist(task_type)`, consider `tapps_memory(action="save")` for learnings

## Consequences of Skipping

| Skipped Tool | Consequence |
|---|---|
| `tapps_session_start` | No project context — tools give generic advice |
| `tapps_lookup_docs` | Hallucinated APIs — code may fail at runtime |
| `tapps_quick_check` | Quality issues may ship silently |
| `tapps_quality_gate` | No quality bar enforced |
| `tapps_security_scan` | Vulnerabilities may ship to production |
| `tapps_checklist` | No verification that process was followed |
| `tapps_consult_expert` | Decisions made without domain expertise |
| `tapps_impact_analysis` | Refactoring may break unknown dependents |

Record progress in `docs/TAPPS_HANDOFF.md` and `docs/TAPPS_RUNLOG.md`.
