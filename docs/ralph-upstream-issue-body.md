## Summary

TheStudio maintains a **vendored** copy of the Ralph Python SDK and compared it to the **bash CLI** (v2.2.0+). The CLI received production fixes that are **not yet reflected in the Python SDK** (SDK still reported as 2.0.2 in our evaluation). We are implementing P0 items in our vendor tree regardless; this issue tracks **upstream parity** so all SDK consumers benefit.

**Reference (external consumer):** TheStudio evaluation with prioritized requests:  
https://github.com/wtthornton/TheStudio/blob/master/docs/ralph-sdk-upgrade-evaluation.md  
(If the link 404s, path is `docs/ralph-sdk-upgrade-evaluation.md` on the TheStudio repo.)

## P0 — Requested SDK enhancements

1. **Stall detection** — Port CLI semantics: fast-trip (consecutive fast failures), deferred-test stall (analogous to `CB_MAX_DEFERRED_TESTS`), consecutive timeouts. Configurable thresholds on `circuit_breaker` (or equivalent).

2. **Progressive context** — Trim large `fix_plan.md`-style inputs to current section + next N unchecked items + token estimate (CLI has `lib/context_management.sh`).

3. **Structured `files_changed`** — Expose reliable `files_changed: list[str]` on `TaskResult` from tool use / `git diff`, not freeform output parsing.

## P1 (same doc)

Task decomposition hints, cost tracking, dynamic model routing, completion-indicator decay, documented `cancel()` semantics, etc. — see evaluation §1.3+ and §2.

## Non-goals

Replacing TheStudio-specific integration; this is **SDK + API** surface only.

Thank you for considering — happy to split into separate issues if you prefer.
