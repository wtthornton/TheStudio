# Bug: Cursor hooks open .sh file in editor on Windows instead of executing

## Summary

On Windows, when TappsMCP Cursor hooks are enabled, invoking an MCP tool triggers the **beforeMCPExecution** hook. Instead of the hook script running, the `.sh` file opens in the editor (e.g. VS Code/Cursor), and a window appears showing the script source (e.g. `tapps-before-mcp.sh`). The hook does not execute.

## Environment

- **OS:** Windows (e.g. win32 10.0.26200)
- **Shell:** PowerShell
- **IDE:** Cursor (with TappsMCP)
- **TappsMCP:** Generates Cursor hooks under `.cursor/hooks/` as Bash scripts (`.sh`)

## Steps to reproduce

1. Bootstrap TappsMCP in a project on Windows (e.g. `tapps_init` or upgrade that creates Cursor hooks).
2. Ensure `.cursor/hooks.json` references the generated hooks, e.g.:
   ```json
   {
     "version": 1,
     "hooks": {
       "beforeMCPExecution": [
         { "command": ".cursor/hooks/tapps-before-mcp.sh" }
       ],
       "afterFileEdit": [
         { "command": ".cursor/hooks/tapps-after-edit.sh" }
       ]
     }
   }
   ```
3. In Cursor, trigger any MCP tool call (e.g. use a TappsMCP tool).
4. Observe: a new editor tab/window opens showing the content of `tapps-before-mcp.sh` (or the other hook script). The script is not executed; it is opened as a file.

## Expected behavior

The hook script should be **executed** (e.g. by Bash or a Windows-compatible runner), so that it can log the tool invocation and optionally remind to call `tapps_session_start()`. No editor window should open for the script file.

## Actual behavior

The hook “command” is interpreted on Windows in a way that does not run the script. The OS or IDE appears to treat the `.sh` path as “open with default application,” so the script opens in the editor instead of being run.

## Root cause (likely)

- TappsMCP generates **Bash-only** hook scripts (`.sh`) for Cursor.
- Cursor’s `hooks.json` uses a bare path (e.g. `.cursor/hooks/tapps-before-mcp.sh`) with no explicit interpreter.
- On Windows, the default association for `.sh` is often “open in editor” (or similar), and there is no system-wide `bash` in PATH unless the user has Git Bash/WSL/etc. So the “command” does not result in execution of the script.

## Suggested fix (for TappsMCP project)

- **Option A:** Generate **Windows-native hook scripts** (e.g. PowerShell `.ps1`) when the host or project is detected as Windows, and set `hooks.json` to invoke them (e.g. `powershell -NoProfile -ExecutionPolicy Bypass -File .cursor/hooks/tapps-before-mcp.ps1`).
- **Option B:** Document that on Windows, Cursor hooks require Bash (e.g. Git Bash) and that the command must be explicit, e.g. `bash .cursor/hooks/tapps-before-mcp.sh`, and have the generator emit that form when Windows is detected.
- **Option C:** In the Cursor hook generator, emit a single cross-platform entrypoint that detects OS and delegates to `.sh` or `.ps1` (or document that users on Windows should disable hooks or add their own `.ps1` wrappers).

## Files involved

- `.cursor/hooks.json` — Cursor hook configuration (generated/updated by TappsMCP).
- `.cursor/hooks/tapps-before-mcp.sh` — Before MCP execution hook (Bash).
- `.cursor/hooks/tapps-after-edit.sh` — After file edit hook (Bash).

## Workaround (user)

Until the bug is fixed, users on Windows can:

- Disable the hooks by removing or clearing the `hooks` entries in `.cursor/hooks.json`, or
- Add Bash to PATH (e.g. Git Bash) and change the command to `bash .cursor/hooks/tapps-before-mcp.sh` (and similarly for the other hook) if Cursor runs hooks in a shell that has `bash` in PATH.

---

*Report generated for passing to the TappsMCP project.*
