# Teammate Extraction Guide — Faultline Slices

To distribute the Northwind extraction across Groq free-tier limits, run your assigned slice (`data/runs/slice_N.json`, where `N` is 1, 2, 3 or 4). `data/runs/build_slices.py` cut the not-yet-cached sources of `day2.json` into these four slices of roughly equal size.

---

## Step-by-Step Instructions

1. **Pull the latest `main`**:
   ```bash
   git fetch
   git checkout main
   git pull origin main
   ```

2. **Set up the virtual environment**:
   ```bash
   uv sync
   ```
   This installs the project and its `dev` dependency group (`pytest`). There is no `[dev]` extra, so `pip install -e ".[dev]"` does not apply.

3. **Configure your API keys**:
   Copy `.env.example` to `.env` and add your **OWN** `GROQ_API_KEY`:
   ```bash
   cp .env.example .env
   ```
   Edit `.env`:
   ```text
   GROQ_API_KEY=gsk_your_own_key_here
   ```

4. **Verify / generate deterministic corpus**:
   ```bash
   uv run python -m data.generate --seed 42 --out data/out
   ```

5. **Run your assigned slice**:
   Replace `N` with your assigned slice number (`1`, `2`, `3` or `4`):
   ```bash
   uv run python -m agent.surveyor data/runs/slice_N.json --tenant scratch_N --workers 4
   ```

6. **Resume on Rate Limits**:
   If Groq returns HTTP 429 (rate limit), wait for the reset window and re-run the exact same command. It automatically resumes from `./cache`:
   ```bash
   uv run python -m agent.surveyor data/runs/slice_N.json --tenant scratch_N --workers 4
   ```

7. **Zip and return the cache folder**:
   Once your slice finishes, zip your `./cache` folder and return it:
   ```bash
   # On Linux/macOS:
   zip -r cache_slice_N.zip cache/

   # On Windows (PowerShell):
   Compress-Archive -Path cache\* -DestinationPath cache_slice_N.zip
   ```
   Send `cache_slice_N.zip` back or place it into `data/incoming/`.

8. **Merging (for whoever collects the zips)**:
   ```bash
   uv run python -m data.runs.merge_cache data/incoming/cache_slice_N.zip
   ```
   With no argument it merges every zip in `data/incoming/`. It writes into `cache/` at the repo root and rejects path traversal, absolute paths, symlinks, non-JSON and oversized entries.
