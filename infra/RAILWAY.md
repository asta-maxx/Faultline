# Railway Deployment Runbook — Faultline

This document specifies the production deployment architecture for the **Faultline** service on [Railway](https://railway.app). It has not been deployed yet: there is no public URL. The restore steps in section 4 were rehearsed locally (`infra/RUN_LOG.md`).

---

## 1. Service Topology (Two Services Only)

```
[ Internet ]
     │
     ▼ (Public HTTPS)
┌────────────────────────────────────────────────────────┐
│ App Service (Public)                                   │
│ - Dockerfile: infra/Dockerfile                         │
│ - FastAPI (api.main:app) + React Vite SPA (/web/dist)  │
│ - MCP tools at /mcp/                                   │
│ - Listens on $PORT (Railway sets it; default 8000)     │
│ - Volume: /cache (LLM response cache)                  │
└────────────────────────────────────────────────────────┘
     │
     ▼ (Railway Private Network: *.railway.internal)
┌────────────────────────────────────────────────────────┐
│ FalkorDB Service (Private)                             │
│ - Image: falkordb/falkordb:latest                      │
│ - Port: 6379 (Private only, no public domain)          │
│ - Persistent Volume: /var/lib/falkordb/data            │
└────────────────────────────────────────────────────────┘
```

---

## 2. FalkorDB Service Configuration (Private)

### Documentation & Persistence Reference
- **FalkorDB Configuration Reference**: [https://docs.falkordb.com/configuration.html](https://docs.falkordb.com/configuration.html)
- **Container Working Directory**: `/var/lib/falkordb/data`
- **Default Database File**: `dump.rdb`
- **Snapshot Persistence Flags**: `save 60 1` or triggered via `BGSAVE`

### Service Settings
1. **Service Type**: Deploy from Docker Image (`falkordb/falkordb:latest`).
2. **Networking**:
   - Do **NOT** generate a public domain for this service.
   - Enable **Private Networking**. Note the private service name (e.g., `falkordb`).
3. **Volume Mount**:
   - Mount a Railway Volume at Mount Path: `/var/lib/falkordb/data`.
   - Recommended volume size: 5 GB+.
4. **Password (optional)**:
   - Setting a `FALKOR_PASSWORD` variable on this service does nothing by itself: the image does not read it. To require a password, also set a custom start command that passes it, as `infra/docker-compose.yml` does:
     ```text
     sh -c 'exec /var/lib/falkordb/bin/run.sh --requirepass "$FALKOR_PASSWORD"'
     ```
   - Set the same `FALKOR_PASSWORD` on the app service.

---

## 3. App Service Configuration (Public)

### Service Settings
1. **Service Type**: Deploy from GitHub Repo, branch `main`.
2. **Build Settings**:
   - **RAILWAY_DOCKERFILE_PATH**: `infra/Dockerfile`
   - **Build Context**: `/` (repository root)
3. **Networking**:
   - Generate a Public Domain (e.g. `faultline-production.up.railway.app`).
   - The container listens on `$PORT`, which Railway injects (the image defaults it to `8000`). No port mapping is needed.
   - Healthcheck Path: `/health`
4. **Volume Mount**:
   - Mount a volume at Mount Path: `/cache`. The image sets `FAULTLINE_CACHE_DIR=/cache`, so the LLM cache lands on the volume and survives redeploys.
5. **Environment Variable Names (Names Only — No Plaintext Secrets)**:
   - `FALKOR_URL` — see below.
   - `FALKOR_PASSWORD` — only if the FalkorDB service requires one (section 2).
   - `REINGEST_TOKEN` — enables `POST /api/reingest`; leave unset to keep it disabled (it then returns 503).
   - `GROQ_API_KEY`
   - `GEMINI_API_KEY`
   - `RAILWAY_DOCKERFILE_PATH`
   - `FAULTLINE_ALLOW_FOLDERS=0` — set it. The server cannot see a visitor's computer, so folder sources are refused with a message that says so; visitors add a Git repository instead (https on GitHub, GitLab or Bitbucket, cloned shallow; the image includes `git`). Clones live in `/app/data/clones` and are not kept across redeploys: an audit re-fetches public repositories, and a private one must be added again with its token.
   - `FAULTLINE_SOURCE_ROOT` — set it as well, for example to `/app/data/out/corpus`. Folder sources added through the UI must sit under this path. **If it is unset, any folder on the server is accepted**, which a public deploy should not allow. The Dockerfile generates the corpus at build time into `/app/data/out/`.
   - `PORT` is set by Railway; do not override it.
   - `FAULTLINE_CACHE_DIR` is already `/cache` in the image; set it only to move the cache.

### Build Notes
- **Corpus generation**: The Dockerfile runs `python -m data.generate --seed 42 --out data/out` at build time (~0.4 s, stdlib only) because `data/out/` is gitignored. The resulting `corpus.json` has SHA-256 `0d44f7dbaa0441e4318ceed79c9e6e899ae36f2e6809b2af546fda2f7dedce9c`.
- **Build context**: the root `.dockerignore` keeps `.env*` (except `.env.example`), `cache/`, `data/out/`, `*.rdb`, `web/node_modules`, `web/dist` and other local state out of the build context. The image regenerates `data/out/` itself.
- **Static file serving**: `infra/app_patch/static_mount.py` serves root-level dist files (e.g. `/faultline.svg`) directly and falls back to `index.html` for SPA routes. Path traversal is blocked via `Path.resolve()` + `is_relative_to()`.

### Private-Network `FALKOR_URL` Format
In the App service settings, set `FALKOR_URL` to the plain private address of the FalkorDB service:
```text
redis://falkordb.railway.internal:6379
```
Do not put the password in the URL. When `FALKOR_PASSWORD` is set and the URL carries no credentials, the app adds it itself (`graph/connection.py`).

---

## 4. How to Load `dump.rdb` into the Persistent Volume

Rule 4: extraction never runs on the demo path. The demo graph ships as an RDB dump of `faultline:northwind` with its claims and conflicts. Restoring it is all the deploy needs: **do not run `data.seed` afterwards**, which would only add the structure again (`--merge`) or wipe the claims (`--reset`).

`infra/scripts/dump_graph.sh` calls `redis-cli` without `-a`, so it only works against a FalkorDB without a password. Export the dump before setting one, or add `-a "$FALKOR_PASSWORD"` to its `redis-cli` calls.

### Option A: Local Docker Compose Restore Rehearsal
1. Export the graph snapshot using `dump_graph.sh`:
   ```bash
   bash infra/scripts/dump_graph.sh data
   ```
2. Reset stack and volumes:
   ```bash
   docker compose -f infra/docker-compose.yml down -v
   ```
3. Create fresh volume and copy `dump.rdb` into `/data/dump.rdb`:
   ```bash
   docker volume create faultline_falkor_data
   docker run --rm -v faultline_falkor_data:/data -v ${PWD}/data:/backup alpine cp /backup/dump.rdb /data/dump.rdb
   ```
4. Start compose stack:
   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```
5. Confirm counts via `GET /health` (section 5).

### Option B: Using Railway CLI (Production Deployment)
1. Export the local graph snapshot using the dump script:
   ```bash
   bash infra/scripts/dump_graph.sh data/
   ```
2. Upload the dump directly into the FalkorDB service volume:
   ```bash
   railway volume upload --service falkordb data/dump.rdb /var/lib/falkordb/data/dump.rdb
   ```
3. Restart the `falkordb` service to load the RDB into memory:
   ```bash
   railway service restart --service falkordb
   ```

### Option C: Structure-Only Seed (Fallback)
`railway run` runs the command **on your machine** with the service's variables injected. Your machine cannot resolve `*.railway.internal`, so `railway run -s app python -m data.seed ...` cannot reach the private FalkorDB service. To seed from outside, you would need a temporary public TCP proxy on the FalkorDB service and a `FALKOR_URL` pointing at it.

Even then, `data.seed` loads only the structural graph (2,826 nodes, 823 edges): no claims, no conflicts, and an empty queue. Prefer Option B.

---

## 5. Verification: Checking `/health` and Graph Counts

After both services are up, verify graph health using `curl`:

```bash
curl -f https://<your-app-domain>.up.railway.app/health
```

### Expected Response (demo RDB restored)
```json
{
  "ok": true,
  "graph": "faultline:northwind",
  "nodes": 3264,
  "edges": 1567,
  "falkor": "up"
}
```

- **Nodes**: `3264` = 2,826 structural (60 Person + 14 System + 40 Decision + 312 Document + 400 Ticket + 2000 Message) + 339 Claim + 79 Entity + 20 Conflict.
- **Edges**: `1567` = 823 structural (14 OWNS + 352 AUTHORED + 26 SUPERSEDES + 323 GOVERNS + 108 CITES) + 339 ASSERTS + 339 ABOUT + 26 CONTRADICTS + 40 INVOLVES.
- **Structure-only seed** (Option C): `nodes: 2826`, `edges: 823`, and the conflict queue is empty.
- **HTTP status**: `200 OK` whenever FalkorDB answers, including an empty or unseeded graph (`nodes: 0`, `edges: 0`). Only an unreachable FalkorDB returns `503 Service Unavailable` with `"falkor": "down"`.

---

## 6. Rollback Procedure

If a bad deployment or database corruption occurs:

1. **Application Rollback**:
   - In the Railway Dashboard under the **App** service, select **Deployments**.
   - Find the last known healthy deployment commit hash and click **Redeploy**.
2. **Database Rollback**:
   - If corrupted, stop the FalkorDB container.
   - Restore the baseline `dump.rdb` from backup storage:
     ```bash
     railway volume upload --service falkordb backup/dump.rdb /var/lib/falkordb/data/dump.rdb
     ```
   - Restart the FalkorDB service.
   - Verify `/health` returns `nodes: 3264`, `edges: 1567` and `falkor: "up"`.
