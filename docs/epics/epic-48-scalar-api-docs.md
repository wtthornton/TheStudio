# Epic 48: API Documentation Upgrade -- Replace Swagger UI with Scalar

> **Status:** DRAFT -- Pending Meridian Review
> **Epic Owner:** Primary Developer
> **Duration:** 1 week (1 slice, 5 stories)
> **Created:** 2026-03-23
> **Priority:** P2 -- Default Swagger UI is functional but provides poor developer experience
> **Depends on:** Epic 34 (React SPA) COMPLETE for the embedded tab. Scalar FastAPI integration at `/docs` is standalone with zero dependencies.
> **Capacity:** Solo developer, 30 hours/week

---

## 1. Title

**API Documentation Upgrade -- Replace Default Swagger UI with Scalar for Interactive API Exploration, "Try It" Console, and Better Visual Design**

---

## 2. Narrative

FastAPI ships with Swagger UI at `/docs` and ReDoc at `/redoc`. Both are functional but bare: no interactive "Try It" console with real responses, no example payloads, no grouping by domain, and the visual design is dated.

Scalar (MIT, 14.4k stars) is a drop-in replacement that provides:
- Beautiful three-column API reference layout
- Interactive "Try It" console that sends real requests to your API
- First-class FastAPI integration (one-line setup)
- React component (`@scalar/api-reference`) for embedding in the SPA
- Dark mode (matches TheStudio's aesthetic)
- Search across all endpoints
- Code snippet generation (curl, Python, JavaScript, etc.)

This epic replaces `/docs` with Scalar and embeds the API reference in the React SPA as a new "API" tab. The FastAPI OpenAPI spec at `/openapi.json` is the source of truth -- no manual API documentation required.

The "Try It" console is particularly valuable for TheStudio because it lets users test webhook payloads, admin API calls, and health endpoints without leaving the browser. Combined with the help panel (Epic 45), this gives users a complete self-service experience.

---

## 3. References

| Type | Reference | Relevance |
|------|-----------|-----------|
| Library | Scalar (MIT, 14.4k stars) | FastAPI integration + React component |
| Source | `src/app.py` | FastAPI app with current Swagger UI |
| Source | `frontend/src/App.tsx` | Tab navigation for embedding API reference |
| Docs | Scalar FastAPI integration docs | Integration guide |

---

## 4. Acceptance Criteria

### AC1: `/docs` Serves Scalar Instead of Swagger UI

Navigating to `/docs` renders the Scalar API reference instead of the default Swagger UI. The reference loads from the FastAPI-generated OpenAPI spec at `/openapi.json`. All endpoints are browseable with descriptions, parameters, and response schemas.

**Testable:** Visit `/docs`. Scalar UI renders with TheStudio's endpoints grouped by tag. Search for "healthz". Result appears. Three-column layout with endpoint list, detail, and code snippets.

### AC2: "Try It" Console Sends Real Requests

The Scalar "Try It" feature sends actual HTTP requests to the running TheStudio instance. Users can test:
- `GET /healthz` (no auth)
- `GET /admin/health` (with auth header)
- `POST /admin/repos` (with JSON body)
- `POST /webhook/github` (with HMAC signature)

**Testable:** Open `/docs`. Navigate to `GET /healthz`. Click "Try It". Response `{"status":"ok"}` appears in the console.

### AC3: API Reference Embedded in React SPA

A new "API" tab in the React SPA renders the Scalar API reference via `@scalar/api-reference` React component. The component loads the OpenAPI spec from the same host. Styling matches the dark theme.

**Testable:** Click "API" tab in the React SPA dashboard. Scalar reference renders with full endpoint list. "Try It" works from within the SPA.

### AC4: API Endpoints Are Grouped and Described

FastAPI endpoint tags are reviewed and updated to provide clear grouping: Health, Admin, Webhooks, Repos, Workflows, Pipeline, Settings. Each tag has a description. Endpoints without tags are assigned to appropriate groups.

**Testable:** Open Scalar reference. Sidebar shows grouped endpoint categories. Each group has a description header.

---

## 5. Constraints & Non-Goals

- ReDoc at `/redoc` is left as-is (removed or kept -- low priority).
- No custom API documentation beyond what the OpenAPI spec provides. If descriptions are missing from FastAPI route decorators, they are added as part of this epic.
- No authentication pre-fill in the "Try It" console (users enter credentials manually).
- No offline/static export of the API documentation.

---

## 6. Stakeholders & Roles

| Role | Who | Responsibility |
|------|-----|----------------|
| Primary Developer | Solo | Implementation |

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Endpoint description coverage | > 90% of endpoints have `summary` set | `python -c "import json; spec=json.load(open('/openapi.json')); paths=[p for p in spec['paths'].values() for m in p.values() if 'summary' not in m]; print(len(paths))"` = 0 or near 0 |
| Scalar renders at /docs | `/docs` returns 200 with Scalar markup | `curl -s /docs \| grep -c 'scalar'` > 0 |
| API tab renders in SPA | ApiReference component mounts and shows endpoints | Vitest: component render assertion |

---

## 8. Context & Assumptions

- Scalar's FastAPI integration uses `get_scalar_api_reference()` which returns an HTML response mounted at a configurable path.
- `@scalar/api-reference` React component is available via npm.
- The OpenAPI spec is auto-generated by FastAPI from route decorators and Pydantic models.
- Scalar's dark theme matches TheStudio's bg-gray-950 aesthetic.

---

## 9. Story Map

### Slice 1: Backend Integration (3 stories, ~4h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 48.1 | Install Scalar FastAPI integration | S | `pip install scalar-fastapi`. Replace Swagger UI mount in `src/app.py` with Scalar. Verify `/docs` renders Scalar. |
| 48.2a | Add tags and descriptions to core routes | S | Add `tags=[]`, `summary=""`, `description=""` to routes in: `src/app.py` (health), `src/ingress/webhook_handler.py` (webhooks), `src/admin/router.py` (admin top-level). ~3 files, ~15 routes. |
| 48.2b | Add tags and descriptions to admin sub-routers | S | Add tags/descriptions to: `src/admin/repos_router.py`, `src/admin/workflow_router.py`, `src/admin/settings_router.py`. ~3 files, ~20 routes. |

### Slice 2: React SPA Embedding (3 stories, ~3h)

| Story | Title | Size | Description |
|-------|-------|------|-------------|
| 48.3 | Install @scalar/api-reference React component | S | `npm install @scalar/api-reference`. Create `frontend/src/components/ApiReference.tsx` wrapping the Scalar component with dark theme config. |
| 48.4 | Add API tab to React SPA | S | Add "API" tab to App.tsx tab navigation. Render `ApiReference` component pointing at `/openapi.json`. |
| 48.5 | Verify "Try It" and add tests | S | Test "Try It" against healthz, admin/health, admin/repos. Add unit test for ApiReference component mount. Verify Scalar renders in both `/docs` and SPA tab. |

---

## 10. Meridian Review Status

**Status:** PENDING
