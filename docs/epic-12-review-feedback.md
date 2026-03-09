# Epic 12 Review — Meridian Checklist + docs-mcp Feedback

> Reviewer: Claude Opus 4.6 | Date: 2026-03-09
> Epic: Admin Settings & Configuration UI (Epic 12)
> Generator: docs-mcp `docs_generate_epic` + `docs_generate_story` (comprehensive style, auto_populate=true)

---

## Meridian Epic Checklist (Saga Review)

| # | Check | Verdict | Notes |
|---|-------|---------|-------|
| 1 | **One measurable success metric** | **GAP** | No success metrics section at all. What does "done" look like quantitatively? e.g., "100% of settings configurable via UI without SSH/redeploy" or "MTTR for API key rotation < 2 minutes" |
| 2 | **Top three risks with mitigations** | **GAP** | Risks are listed but probability/impact are placeholder `Low/Medium/High` and mitigations say "Define mitigation strategy" — these are empty shells |
| 3 | **Non-goals in writing** | **PASS** | Four clear non-goals listed |
| 4 | **External dependencies** | **GAP** | Lists Epic 4 and Epic 11 as dependencies but doesn't confirm their status (complete? in progress?). No mention of whether the `cryptography` Fernet key setup is already production-ready |
| 5 | **Link to goal/OKR** | **GAP** | No link to any OKR, roadmap item, or strategic goal. Why this epic now? |
| 6 | **Testable acceptance criteria** | **PASS** | 12 clear, testable ACs — well written |
| 7 | **AI-ready** | **PARTIAL** | Good detail in stories, but epic-level story stubs lost all the task detail (generic "Implement X / Write unit tests / Update documentation" instead of the rich tasks from the full story docs) |

**Meridian verdict: 2 PASS, 1 PARTIAL, 4 GAP — needs revision before commit.**

---

## docs-mcp Generator Quality Feedback

### What's Good

1. **Consistent structure** — All 9 documents follow the same template with clear sections. The `docsmcp:start/end` markers enable safe re-generation.
2. **Story-level detail is strong** — Stories 12.1 and 12.2 are particularly well-written with specific file paths, named test cases, and concrete tasks.
3. **INVEST checklist** — Nice addition for story quality validation.
4. **Dependencies are tracked** — Each story correctly references its upstream dependency.
5. **Comprehensive style adds real value** — Test cases, technical notes, and files sections make stories implementable.

### What's Missing or Broken

#### Epic-Level Issues

1. **Story stubs in the epic are hollow** — The epic's story section has generic tasks ("Implement X", "Write unit tests", "Update documentation") that don't reflect the detailed tasks from the full story documents. The epic should either cross-reference the story files or inline a meaningful summary. As-is, someone reading just the epic gets a watered-down view.

2. **Risk assessment is a template, not a plan** — Probability and impact are literally `Low/Medium/High` (all three options listed, none selected). Mitigations say "Define mitigation strategy". This is worse than no risk section because it looks complete at a glance but contains zero information.

3. **Security Expert recommendations are empty** — Both epic and all 8 stories show `"Security Expert (30%): No specific knowledge found..."` or `(56%): Based on domain knowledge (2 source(s)..."` followed by nothing. This is a security-sensitive epic (API key storage, encryption, secret rotation). The expert integration should either produce actionable advice or be omitted rather than showing empty placeholders.

4. **Performance targets are placeholder** — All values are `< N ms` and `> N req/s`. Should either be filled with reasonable defaults or omitted.

5. **Files Affected table says `*see tasks*` for every row** — This defeats the purpose of the table. It should aggregate the actual file paths from the stories.

6. **No success metrics section** — Critical gap per Saga's eight-part epic structure (item 7: Success metrics).

7. **No stakeholders section** — Missing per Saga's structure (item 6: Stakeholders & roles).

8. **No link to OKR or roadmap** — Missing per Saga's structure (item 3: References).

#### Story-Level Issues

9. **Test Cases are placeholders in 6 of 8 stories** — Stories 12.3 through 12.8 all have `"Test happy path... / Test edge cases... / Test error handling..."` instead of actual named test cases. Only 12.1 and 12.2 have real test case names. This is because explicit `test_cases` were provided for those two but not the others — docs-mcp should either generate reasonable test names from the acceptance criteria or leave the section empty rather than inserting generic placeholders.

10. **"Tech Stack: thestudio, Python >=3.12" repeated in every document** — This is noise. It appears in the Description section of every single story and the epic. Once in the epic is enough; stories should inherit it.

11. **"Project Structure: 3 packages, 114 modules, 641 public APIs" repeated everywhere** — Same issue. This auto-populated line adds no value to individual stories and creates clutter.

12. **Definition of Done is identical across all stories** — It's the same 6-item generic checklist copy-pasted. If it can't be story-specific, it should live once in the epic and stories should reference it.

13. **INVEST checklist is always unchecked** — It's a self-assessment that the generator could partially fill based on the story content (e.g., if it has test cases, "Testable" should be checked).

---

## Recommendations for docs-mcp Enhancements

| # | Enhancement | Impact |
|---|-------------|--------|
| 1 | **Populate risk assessment properly** — Force the caller to provide probability/impact per risk, or auto-classify based on keywords (e.g., "encryption" = Medium probability, High impact). Never emit the template placeholders. | High |
| 2 | **Generate test case names from acceptance criteria** — When `test_cases` is empty, derive names like `test_<AC_keyword>` from each acceptance criterion. The current "Test happy path..." placeholder is actively misleading. | High |
| 3 | **Aggregate files in epic from stories** — When stories include file lists, the epic's Files Affected table should pull actual file paths instead of `*see tasks*`. | Medium |
| 4 | **Don't repeat inherited context** — Tech stack and project structure lines should appear once in the epic, not in every story's description and technical notes. | Medium |
| 5 | **Epic story stubs should summarize the full story** — When full stories are generated alongside the epic, the epic's story section should include the story's actual tasks (or at least the first 3-4) rather than generic placeholders. | High |
| 6 | **Add a Success Metrics section to the epic template** — This is part of standard Saga structure and Meridian review. The comprehensive epic style should include it. | High |
| 7 | **Add a Stakeholders section to the epic template** — Same reasoning. Who owns this epic? Who reviews? | Medium |
| 8 | **Add an OKR/References section to the epic template** — Allow the caller to provide `okr` or `references` parameters and generate a section linking to strategic context. | Medium |
| 9 | **Handle empty expert recommendations gracefully** — Instead of showing "No specific knowledge found" with 30% confidence, either suppress the section or display "Expert review pending — manual security review required before implementation." | Medium |
| 10 | **Pre-check INVEST for stories** — If the story has test cases, check "Testable". If it has no dependencies, check "Independent". Partial automation of the checklist adds value. | Low |
| 11 | **Support a `--link-stories` flag on epic generation** — When stories are generated to files, the epic's story section should link to them with relative paths: `See [full story](stories/story-12.1-settings-data-model.md)`. | Medium |
| 12 | **Deduplicate Definition of Done** — Either make it epic-level only (stories inherit), or allow story-specific DoD that differs from the default. | Low |

---

## Bottom Line

The docs-mcp generator produces **solid structural scaffolding** — the section organization, marker system, and comprehensive style are genuinely useful. But the output has a **"looks complete but isn't" problem**: risk tables with no data, expert sections with no advice, test cases with placeholder text, and files tables that punt to sub-documents. For a security-sensitive epic like this one, those gaps create false confidence.

The highest-impact fixes are:

1. **Never emit empty placeholder content** — either generate real data or omit the section
2. **Add Success Metrics and Stakeholders to the epic template**
3. **Derive test case names from acceptance criteria when none are provided**
