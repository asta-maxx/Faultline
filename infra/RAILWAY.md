# Railway Deployment Runbook — Faultline

This document specifies the production deployment architecture for the **Faultline** service on [Railway](https://railway.app).

---

## 1. Service Topology (Two Services Only)

```
[ Internet ]
     │
     ▼ (Public HTTPS)
┌────────────────────────────────────────────────────────┐
│ App Service (Public)                                  │
│ - Dockerfile: infra/Dockerfile                         │
│ - FastAPI (api.main:app) + React Vite SPA (/web/dist)   │
│ - Port: 8000 (mapped to $PORT)                         │
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
4. **Environment Variable Names**:
   - `FALKOR_PASSWORD` (Optional authentication password).

---

## 3. App Service Configuration (Public)

### Service Settings
1. **Service Type**: Deploy from GitHub Repo (`devc/deploy-all` or `main`).
2. **Build Settings**:
   - **RAILWAY_DOCKERFILE_PATH**: `infra/Dockerfile`
   - **Build Context**: `/` (repository root)
3. **Networking**:
   - Generate a Public Domain (e.g. `faultline-production.up.railway.app`).
   - Target Port: `8000` (mapped to Railway dynamic `$PORT`).
   - Healthcheck Path: `/health`
4. **Volume Mount**:
   - Mount a volume at Mount Path: `/cache` (for LLM disk cache).
5. **Environment Variable Names (Names Only — No Plaintext Secrets)**:
   - `FALKOR_URL`
   - `FALKOR_PASSWORD`
   - `REINGEST_TOKEN`
   - `GROQ_API_KEY`
   - `GEMINI_API_KEY`
   - `PORT`
   - `RAILWAY_DOCKERFILE_PATH`
   - `FAULTLINE_SOURCE_ROOT` — set to `/app/data/out/corpus` on Railway.
     This is the directory that `api/workspaces.py` (on the `allen/live-pipeline`
     branch) uses to sandbox folder-based source locations. The Dockerfile
     generates the corpus at build time into `/app/data/out/`.

### Build Notes
- **Corpus generation**: The Dockerfile runs `python -m data.generate --seed 42 --out data/out`
  at build time (~0.4 s, stdlib only) because `data/out/` is gitignored. The corpus
  SHA256 is `0d44f7dbaa0441e4318ceed79c9e6e899ae36f2e6809b2af546fda2f7dedce9c`.
  No `.dockerignore` is needed since none exists and `data/out/` is created inside
  the image during build (not copied from host).
- **Static file serving**: `infra/app_patch/static_mount.py` serves root-level
  dist files (e.g. `/faultline.svg`) directly and falls back to `index.html` for
  SPA routes. Path traversal is blocked via `Path.resolve()` + `is_relative_to()`.

### Private-Network `FALKOR_URL` Format
In the App service settings, set `FALKOR_URL` to reference the private FalkorDB service over Railway private network:
```text
redis://${FALKOR_PASSWORD:+:$FALKOR_PASSWORD@}falkordb.railway.internal:6379
```
Or without password:
```text
redis://falkordb.railway.internal:6379
```

---

## 4. How to Load `dump.rdb` into the Persistent Volume

To pre-load the structural knowledge graph into Railway without running live ingestion during deploy:

### Option A: Local Docker Compose Restore Rehearsal (Verified)
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
5. Confirm counts via `GET /health` (`nodes: 2826, edges: 823, falkor: "up"`).

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

### Option C: Remote One-Time Ingestion
If volume upload is not permitted by your permissions tier:
1. Run `data/seed.py` from a machine connected to the private network via Railway CLI:
   ```bash
   railway run -s app python -m data.seed --reset --tenant northwind
   ```

---

## 5. Verification: Checking `/health` and Graph Counts

After both services are up, verify graph health using `curl`:

```bash
curl -f https://<your-app-domain>.up.railway.app/health
```

### Expected Response
```json
{
  "ok": true,
  "graph": "faultline:northwind",
  "nodes": 2826,
  "edges": 823,
  "falkor": "up"
}
```

- **HTTP Status Code**: `200 OK` (if FalkorDB is down or unseeded, it returns `503 Service Unavailable`).
- **Nodes Expected**: `2826` (60 Person + 14 System + 40 Decision + 312 Document + 400 Ticket + 2000 Message).
- **Edges Expected**: `823` (14 OWNS + 352 AUTHORED + 26 SUPERSEDES + 323 GOVERNS + 108 CITES).

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
   - Verify `/health` returns `nodes: 2826` and `falkor: "up"`.
