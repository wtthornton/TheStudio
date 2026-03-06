---
name: docs-epic-story
description: >-
  Generate epics and stories using DocsMCP. Creates structured epics with
  8-part format (Saga) and stories with AC, tasks, test cases. Use when
  creating or updating epics and stories in docs/epics/.
mcp_tools:
  - docs_generate_epic
  - docs_generate_story
---

Generate an epic or stories using DocsMCP and the Saga persona:

## Epic generation

1. Call `docs_generate_epic` with: title, number, goal, motivation, status, priority, estimated_loe, style (comprehensive), auto_populate (true), output_path
2. The epic follows the 8-part Saga structure: title, narrative, references, AC, constraints/non-goals, stakeholders, success metrics, context/assumptions
3. After generation, submit to Meridian review (persona-meridian rule)

## Story generation

1. Call `docs_generate_story` for each story with: epic_number, story_number, role, style (comprehensive), auto_populate (true), output_path
2. Each story includes: user story (As a / I want / So that), tasks with file paths, AC (checkbox), test cases, technical notes, dependencies, INVEST check
3. Stories go to `docs/epics/stories/story-{epic}.{story}-{title}.md`

## Supporting artifacts

After epic + stories are created, generate supporting docs:
- `docs_generate_prd` — Product Requirements Document
- `docs_generate_adr` — Architecture Decision Records
- `docs_generate_diagram` — Module map and dependency diagrams
