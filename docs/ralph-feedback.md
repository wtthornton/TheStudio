# Feedback for Ralph (ralph-claude-code)

**Date:** 2026-03-21  
**Ralph version tested:** 1.2.0  
**Environment:** Windows 10/11 with WSL  
**Project:** TheStudio

---

## Summary

Ralph works well when run through WSL. This feedback captures friction points and suggestions to improve the experience for Windows users and version discovery.

---

## 1. Windows: Native Invocation Triggers "Open With" Dialog

**What happens:** Invoking `ralph` (e.g. `ralph --version`) from native Windows shells (PowerShell, CMD, or via an agent/IDE that spawns Windows processes) does not execute Ralph. Instead, Windows shows a dialog: *"Select an app to open 'ralph'"* (Notepad, VS Code, etc.).

**Root cause:** The `ralph` binary/script has no extension. Windows treats it as a file to open rather than a command to run.

**Workaround:** Run Ralph through WSL:
```powershell
wsl ralph --version
wsl ralph --live
```

**Suggestions:**
- Add a **Windows** section to the README and setup docs explaining that `ralph` must be run via WSL on Windows.
- Consider shipping a `ralph.cmd` / `ralph.ps1` that invokes `wsl ralph "$@"` so users can run `ralph` from Windows without remembering `wsl`.
- In docs, explicitly show: `wsl ralph <command>` as the Windows invocation pattern.

---

## 2. Version Discovery

**Observation:** `ralph --version` works and returns `ralph 1.2.0` (via WSL). It would be useful to know if that is the latest.

**Current state:**
- GitHub repo has no Releases or tags.
- `package.json` shows `1.0.0`, which is inconsistent with the installed `1.2.0`.
- Third-party sources sometimes mention other versions (e.g. v0.11.5), causing confusion.

**Suggestions:**
- Add GitHub Releases for each version so users can see the latest and changelog.
- Align `package.json` (or equivalent) version with the actual CLI version.
- Document the canonical version source (e.g. “check `ralph --version`; latest is published in Releases”).

---

## 3. Documentation Gaps

**`ralph-setup.md` (project-specific):** Step 7 says “Run Ralph (from WSL)” but does not:
- Explicitly state that native Windows invocation will fail.
- Show the `wsl ralph` prefix for Windows users.

**Suggestion:** Add a short “Windows users” note, e.g.:

> **Windows:** Ralph runs in WSL. Use `wsl ralph --live` (and `wsl ralph <command>` for other subcommands) from PowerShell or CMD.

---

## 4. What Works Well

- `ralph --version` is clear and useful.
- Project-level config (`.ralphrc`, `.ralph/`) is straightforward.
- WSL-based workflow is stable once the `wsl` prefix is understood.

---

## Checklist for Submitting

If submitting this as a GitHub issue to [frankbria/ralph-claude-code](https://github.com/frankbria/ralph-claude-code):

- [ ] Consider splitting into separate issues (Windows support, version/releases, docs).
- [ ] Add `ralph-feedback` or similar label if available.
- [ ] Optionally include screenshots of the “Open with” dialog for context.
