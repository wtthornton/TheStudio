# MCP Setup (TheStudio) — Local tapps-mcp & Context7

**Purpose:** Local MCP setup for TheStudio: **tapps-mcp** (code quality) and **Context7** (documentation lookups). Config is project-local in `.cursor/mcp.json`.

---

## 1. Servers configured

| Server       | Type   | Role                          |
|-------------|--------|-------------------------------|
| **tapps-mcp** | Local  | Code quality / TAPPS pipeline |
| **Context7**  | Local (npx) | Up-to-date docs for LLMs   |
| **docs-mcp**  | Local  | Project docs (TappMCP)        |
| **Playwright** | Local (npx) | Browser automation / acceptance testing |

All run on your machine (tapps-mcp and docs-mcp via local exe, Context7 via `npx`). docs-mcp uses `DOCS_MCP_PROJECT_ROOT=${workspaceFolder}` (Cursor resolves this to the workspace path).

---

## 2. Context7 API key (required for Context7)

The key is **not** stored in the project. Cursor reads it from your OS environment as `CONTEXT7_API_KEY`.

### Get the key from Context7 (same as HomeIQ)

If you already use Context7 in HomeIQ and have `CONTEXT7_API_KEY` set in your Windows user environment, you don’t need to do anything else for TheStudio.

Otherwise:

1. Open **[context7.com/dashboard](https://context7.com/dashboard)** (same source as HomeIQ).
2. Create an API key (e.g. name: "Cursor" or "TheStudio").
3. Copy the key (format: `ctx7sk-...`). It is shown only once.

### Set it on Windows (persistent, recommended)

**PowerShell (current user):**

```powershell
[System.Environment]::SetEnvironmentVariable("CONTEXT7_API_KEY", "ctx7sk-xxxx-your-key-here", "User")
```

Then **fully quit and reopen Cursor** so it sees the variable.

**Alternative:**  
**Settings → System → About → Advanced system settings → Environment Variables → User variables → New**  
Name: `CONTEXT7_API_KEY`, Value: your key.

### Temporary (current session only)

```powershell
$env:CONTEXT7_API_KEY = "ctx7sk-xxxx-your-key-here"
```

Start Cursor from this same PowerShell window.

---

## 3. Enable in Cursor

1. Open **Cursor → Settings → Tools & MCP**.
2. Confirm **tapps-mcp**, **Context7**, and **docs-mcp** appear under **Installed MCP Servers** (from `.cursor/mcp.json`).
3. Turn each **ON** (green) as needed.
4. If you changed `CONTEXT7_API_KEY`, fully quit and reopen Cursor.

---

## 4. Paths (local setup)

- **tapps-mcp:** `C:\Users\tappt\.local\bin\tapps-mcp.exe` with `TAPPS_MCP_PROJECT_ROOT=c:\cursor\TheStudio`.
- **Context7:** Runs via `npx -y @upstash/context7-mcp`; no path config needed.
- **docs-mcp:** `C:\cursor\TappMCP\dist\docsmcp.exe` with `DOCS_MCP_PROJECT_ROOT=${workspaceFolder}` (workspace root).

---

## 5. Security

- No API key is stored in the repo; only `${env:CONTEXT7_API_KEY}` is used in `mcp.json`.
- Keep your Context7 key only in your environment or a secure secret store.

---

**Note:** **docs-mcp** is your local TappMCP docs server (`C:\cursor\TappMCP\dist\docsmcp.exe`). In HomeIQ, documentation lookups are done with **Context7**; here you have both (docs-mcp local, Context7 cloud). No need to add a separate “docs-mcp” server there. Both docs-mcp (local) and Context7 (cloud) are configured; enable the one(s) you need in Settings → Tools & MCP.
