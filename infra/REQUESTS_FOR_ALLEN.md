# Requests for Allen (from Dev C — Data & Infra)

Date: 2026-10-16
Branch: `devc/data-infra`

Per team contract and ownership boundaries, Dev C touches **only** `/data` and `/infra`. Any adjustments or synchronizations needed outside those directories are tracked here.

---

### 1. Python Test Dependency (`pytest`) in `pyproject.toml`
- **Current state**: `pyproject.toml` contains runtime dependencies (`fastapi`, `uvicorn`, `falkordb`, `httpx`), but not `pytest`.
- **Request**: Please add `pytest` to `pyproject.toml` under a dev dependency group (e.g., `[dependency-groups] dev = ["pytest>=8.0"]`).
- **Dev C non-blocking workaround**: In our test scripts and local environments, we use `uv pip install pytest` into `.venv` or run with `uv run --with pytest pytest ...` so we don't modify your `pyproject.toml` or `uv.lock`.

---

### 2. Live `/health` and `/api/health` Route Wiring
- **Current state**: `api/main.py` has a stubbed `@app.get("/api/health")` returning hardcoded zeros and `"falkor": "down"`. CONTRACT.md §9 specifies `GET /health` returning `{"ok": bool, "graph": str, "nodes": int, "edges": int, "falkor": "up"|"down"}` with HTTP 503 if FalkorDB is down.
- **Delivery**: We have prepared a drop-in health router in `/infra/app_patch/health.py` that handles both `/health` (CONTRACT §9 root route) and `/api/health` (frontend proxy route).
- **Request**: Please include `app.include_router(health_router)` in `api/main.py`.

---

### 3. SPA Catch-All vs `GET /conflicts/{id}` Routing Analysis & Recommended Fix
- **Investigation of `/web` API calls**:
  - `web/src/lib/api.ts` makes all HTTP requests with a `/api/` prefix (e.g., `/api/health`, `/api/conflicts`, `/api/conflicts/${id}`, `/api/stats`, `/api/conflicts/${id}/resolve`).
  - `web/vite.config.ts` proxies `/api` requests to `http://localhost:8000` during development without URL rewrites.
  - `web/src/App.tsx` manages view state locally via `useState(selectedConflict)`, but deep linking or client-side routing on `/conflicts` or `/conflicts/{id}` requires SPA fallback support.
- **Does a root SPA catch-all shadow `GET /conflicts/{id}`?**:
  - In `api/main.py`, API endpoints are currently mounted as `@app.get("/api/conflicts/{conflict_id}")` (prefixed with `/api/`).
  - CONTRACT.md §9 specifies the authoritative HTTP API as `GET /conflicts/{id}` (without an `/api/` prefix).
  - **Yes, shadowing risk exists**: If FastAPI defines an un-prefixed route `GET /conflicts/{id}` or if an SPA catch-all (`@app.get("/{full_path:path}")` or `StaticFiles(..., html=True)` mounted at `/`) is registered *before* the API routes, the catch-all will intercept requests to `GET /conflicts/{id}` and return `index.html` (HTTP 200) instead of the JSON API response. Furthermore, if a client requests a nonexistent API route (e.g. `GET /api/conflicts/nonexistent`), a naive catch-all will erroneously return `index.html` with HTTP 200 rather than a 404 JSON error.
- **The Smallest Proposed Fix**:
  1. Define and mount all API routers (both `/api/...` and top-level aliases like `/conflicts/{id}`) **before** registering the static file or SPA fallback handlers.
  2. Register the SPA fallback route **last**, with an explicit check that blocks only paths starting with `"api/"` plus the exact paths `"health"`, `"stats"`, `"docs"`, and `"openapi.json"`. It does **not** block `"conflicts"` prefixes, allowing the SPA to handle browser navigation for `/conflicts` and `/conflicts/{id}`:
     ```python
     BLOCKED_EXACT = {"health", "stats", "docs", "openapi.json"}

     @app.get("/{full_path:path}")
     async def spa_fallback(full_path: str):
         norm = full_path.strip("/")
         if norm.startswith("api/") or norm == "api" or norm in BLOCKED_EXACT:
             raise HTTPException(status_code=404, detail="Not Found")
         index_file = WEB_DIST / "index.html"
         if index_file.exists():
             return FileResponse(index_file)
         raise HTTPException(status_code=404, detail="Frontend index.html not found")
     ```
  3. We deliver ready-to-paste helpers in `/infra/app_patch/static_mount.py`.

---

### 4. Question: CONTRACT.md §2 Stack Table (Graphiti vs Surveyor)
- **Question for Allen**: CONTRACT.md §2 currently lists `Extraction | Graphiti onto FalkorDB`. However, `SESSION-NOTES.md` notes that extraction is now implemented directly in `agent/surveyor.py` without Graphiti or vector embeddings. Should CONTRACT.md §2 be updated in the next version to reflect this architectural decision for judges?

---

### 5. Corpus & Ground Truth Ingest Interface
- **Current state**: The Northwind generator (`data.generate`) outputs:
  - Markdown documents under `data/out/corpus/docs/`
  - Markdown ADRs under `data/out/corpus/adr/`
  - JSONL tickets under `data/out/corpus/tickets.jsonl`
  - JSONL chat messages under `data/out/corpus/messages.jsonl`
  - Full unified JSON corpus under `data/out/corpus.json` (matching `fixtures/mini-corpus.json` schema)
  - Structural graph seed script & loader (`data.seed`) loading `faultline:northwind`
  - `data/out/ground_truth.json` containing the 14 planted contradictions (5 direct, 5 superseded, 4 undocumented) with exact evidence sentences and calculated blast radii.
- **Usage**: In your Surveyor ingest pipeline, feel free to consume `data/out/corpus.json` or individual files from `data/out/corpus/`.

---

### 6. Environment Variables (`FALKOR_PASSWORD` and `REINGEST_TOKEN`) in root `.env.example`
- **Current state**: The root `.env.example` contains `FALKOR_URL`, `GEMINI_API_KEY`, `GROQ_API_KEY`, and model overrides.
- **Infra additions**: In `infra/.env.example`, we added:
  - `FALKOR_PASSWORD=`: required for secured FalkorDB instances (used in local compose and private Railway deployments).
  - `REINGEST_TOKEN=`: required for token-gated `POST /reingest` endpoint (CONTRACT §9).
- **Request**: When convenient, please copy or merge these two keys into the root `.env.example`.
