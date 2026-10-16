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
   - `FALKORDB_PASSWORD` (Optional authentication string).

---

## 3. App Service Configuration (Public)

### Service Settings
1. **Service Type**: Deploy from GitHub Repo (`devc/data-infra` or `main`).
2. **Build Settings**:
   - **Dockerfile Path**: `infra/Dockerfile`
   - **Build Context**: `/` (repository root)
3. **Networking**:
   - Generate a Public Domain (e.g. `faultline-production.up.railway.app`).
   - Target Port: `8000` (or Railway dynamic `$PORT`).
4. **Volume Mount**:
   - Mount a volume at Mount Path: `/cache` (for agent LLM and prefilter response cache).
5. **Environment Variable Names (Names Only — No Plaintext Secrets)**:
   - `FALKOR_URL`
   - `FALKORDB_PASSWORD`
   - `GEMINI_API_KEY`
   - `PORT`

### Private-Network `FALKOR_URL` Format
In the App service settings, set `FALKOR_URL` to reference the private FalkorDB service over Railway private mesh:
```text
redis://${FALKORDB_PASSWORD:+:$FALKORDB_PASSWORD@}falkordb.railway.internal:6379
```
Or without password:
```text
redis://falkordb.railway.internal:6379
```

---

## 4. How to Load `dump.rdb` into the Persistent Volume

To pre-load the structural knowledge graph into Railway without running live ingestion during deploy:

### Option A: Using Railway CLI (Recommended)
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

### Option B: Remote One-Time Ingestion
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
