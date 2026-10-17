"""Workspace audit (CONTRACT §9b): read sources -> Surveyor -> graph -> funnel -> Adjudicator.

One background thread per run. Progress is written to the AuditRun node in faultline:_registry
as it happens, so GET /api/audits/{run_id} shows the funnel collapsing live and a finished run
reads back the same after a restart.

Only folder sources are read. Git sources are stored but cloning is not implemented; they are
listed as skipped in the READING SOURCES detail, never read and never reported as read.
"""

from __future__ import annotations

import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from agent import gitsource, surveyor
from agent.adjudicator import FLOOR, Stats, adjudicate
from graph import registry
from graph.connection import get_graph
from graph.prefilter import prefilter
from graph.queries import rows, shared_entity_pairs

STAGES = [
    ("READING SOURCES", "documents"),
    ("EXTRACTING CLAIMS", "claims"),
    ("BUILDING GRAPH", "possible pairs"),
    ("COLLAPSING CANDIDATES", "candidate pairs"),
    ("JUDGING PAIRS", "pairs judged"),
]
SUFFIXES = {".md", ".markdown", ".txt"}
_running: dict[str, str] = {}  # workspace_id -> run_id
_lock = threading.Lock()


class AuditError(Exception):
    pass


# ------------------------------------------------------------------ folders
def folder_files(folder: Path) -> list[Path]:
    """Readable documents under folder. Symlinks are never followed (a cloned repository could
    point one at a server file) and nothing under .git is read."""
    root = folder.resolve()
    out = []
    for p in folder.rglob("*"):
        if p.suffix.lower() not in SUFFIXES or p.is_symlink() or ".git" in p.relative_to(folder).parts:
            continue
        # Resolving catches a file reached through a symlinked directory that leaves the folder.
        if p.is_file() and p.resolve().is_relative_to(root):
            out.append(p)
    return sorted(out)


def readable(s: dict) -> bool:
    return s["kind"] in ("folder", "git") and s["status"] == "ready"


def _kind(rel: str) -> str:
    low = rel.lower()
    for k in ("runbook", "readme", "spec"):
        if k in low:
            return k
    return "wiki"


def read_folder(folder: Path, taken: set[str]) -> list[dict]:
    """Every readable file becomes a Document (CONTRACT §9b). Ids are file stems when unique."""
    docs = []
    for f in folder_files(folder):
        rel = f.relative_to(folder).as_posix()
        text = f.read_text(encoding="utf-8", errors="replace")
        doc_id = f.stem if f.stem not in taken else "doc-" + re.sub(r"[^a-z0-9]+", "-", rel.lower()).strip("-")
        taken.add(doc_id)
        heading = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), None)
        docs.append({"id": doc_id, "title": heading or f.stem, "path": rel, "kind": _kind(rel),
                     "updated_at": int(f.stat().st_mtime), "text": text})
    return docs


# ------------------------------------------------------------------ run state
class Run:
    def __init__(self, workspace_id: str):
        now = int(time.time())
        self.lock = threading.Lock()
        self.last_save = 0.0
        self.data = {
            "run_id": "run-" + uuid.uuid4().hex[:12], "workspace_id": workspace_id, "status": "running",
            "stage": None, "current": None, "error": None, "summary": None, "started_at": now, "ended_at": None,
            "stages": [{"name": n, "state": "pending", "count": None, "unit": u, "detail": None,
                        "started_at": None, "ended_at": None} for n, u in STAGES],
        }

    def stage(self, i: int) -> dict:
        return self.data["stages"][i]

    def begin(self, i: int) -> None:
        with self.lock:
            s = self.stage(i)
            s.update(state="active", started_at=int(time.time()), count=0)
            self.data["stage"] = s["name"]
        self.save(force=True)

    def end(self, i: int, count: int | None = None, detail: str | None = None) -> None:
        with self.lock:
            s = self.stage(i)
            s.update(state="done", ended_at=int(time.time()))
            if count is not None:
                s["count"] = count
            if detail is not None:
                s["detail"] = detail
        self.save(force=True)

    def progress(self, i: int, count: int, current: str | None = None, detail: str | None = None) -> None:
        with self.lock:
            self.stage(i)["count"] = count
            if detail is not None:
                self.stage(i)["detail"] = detail
            if current is not None:
                self.data["current"] = current
        self.save()

    def save(self, force: bool = False) -> None:
        # At most a few writes a second: the screen polls once a second.
        now = time.monotonic()
        if not force and now - self.last_save < 0.25:
            return
        self.last_save = now
        with self.lock:
            snapshot = {**self.data, "stages": [dict(s) for s in self.data["stages"]]}
        registry.save_run(snapshot)


# ------------------------------------------------------------------ start
def start(workspace_id: str) -> str:
    sources = registry.list_sources(workspace_id)
    if not any(readable(s) for s in sources):
        raise AuditError("No readable source. Add a Git repository or a folder first.")
    with _lock:
        if workspace_id in _running:
            raise AuditError(f"An audit is already running for this workspace: {_running[workspace_id]}")
        run = Run(workspace_id)
        _running[workspace_id] = run.data["run_id"]
    run.save(force=True)
    threading.Thread(target=_work, args=(run, sources), daemon=True).start()
    return run.data["run_id"]


def _work(run: Run, sources: list[dict]) -> None:
    ws = run.data["workspace_id"]
    try:
        _pipeline(run, sources)
        with run.lock:
            run.data.update(status="done", stage=None, current=None, ended_at=int(time.time()))
    except Exception as e:  # the run reports what broke; nothing claims success
        with run.lock:
            for s in run.data["stages"]:
                if s["state"] == "active":
                    s["state"] = "failed"
            run.data.update(status="failed", error=f"{type(e).__name__}: {e}", ended_at=int(time.time()))
    finally:
        run.save(force=True)
        with _lock:
            _running.pop(ws, None)


def _pipeline(run: Run, sources: list[dict]) -> None:
    ws = run.data["workspace_id"]

    # 1. Read every source: folders in place, git repositories from a fresh clone of the latest
    # commit, or from the copy cloned when the source was added if that fails (a private
    # repository's token is never kept).
    run.begin(0)
    docs: list[dict] = []
    owner: dict[str, str] = {}  # document id -> source id
    taken: set[str] = set()
    notes: list[str] = []
    skipped = [s for s in sources if not readable(s)]
    if skipped:
        notes.append(f"{len(skipped)} source(s) not read")
    for s in sources:
        if not readable(s):
            continue
        if s["kind"] == "git":
            folder = gitsource.checkout_path(ws, s["id"])
            run.progress(0, len(docs), current=f"fetching {s['location']}")
            try:
                gitsource.clone(s["location"], folder)
            except gitsource.GitError:
                if folder.is_dir():
                    notes.append(f"{s['location']}: read the copy cloned when it was added")
                else:
                    registry.update_source(s["id"], status="missing",
                                           message="The clone is gone and the repository could not be fetched again. "
                                                   "Remove it and add it again (with a token if it is private).")
                    notes.append(f"{s['location']}: not read")
                    continue
        else:
            folder = Path(s["location"])
        if not folder.is_dir():
            registry.update_source(s["id"], status="missing", message=f"Folder not found at audit time: {folder}")
            continue
        for d in read_folder(folder, taken):
            docs.append(d)
            owner[d["id"]] = s["id"]
            label = s["location"].rsplit("/", 1)[-1] if s["kind"] == "git" else folder.name
            run.progress(0, len(docs), current=f'{label}/{d["path"]}')
    if not docs:
        raise AuditError("The sources contain no .md, .markdown or .txt files.")
    run.end(0, len(docs), detail="; ".join(notes) or None)

    # 2. Extract claims, one cached call per document.
    run.begin(1)
    srcs = surveyor.load_sources({"documents": docs})
    rep = surveyor.Report()
    claims: list[dict] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(surveyor.extract_source, s, rep): s for s in srcs}
        for f in as_completed(futures):
            claims.extend(f.result())
            run.progress(1, len(claims), current=futures[f]["props"]["path"])
    failed = len(rep.failed_sources)
    run.end(1, len(claims), detail=f"{failed} document(s) failed and will be retried next run" if failed else None)

    # 3. Resolve entities, harmonise predicates, write the workspace graph.
    run.begin(2)
    run.progress(2, 0, current="resolving entities")
    surveyor.assign_claim_ids(claims)
    entities, _, _ = surveyor.resolve_entities(claims, rep)
    surveyor.consolidate(claims, entities, rep)
    run.progress(2, 0, current="harmonising predicates")
    surveyor.harmonise_all(claims, rep)
    surveyor.load_graph(ws, srcs, claims, entities)
    n = len(claims)
    run.end(2, n * (n - 1) // 2, detail=f"{len(entities)} entities")

    # 4. Collapse candidates on shared Entity nodes, then the deterministic prefilter.
    run.begin(3)
    g = get_graph(ws)
    s2 = shared_entity_pairs(g, FLOOR)
    s3 = prefilter(s2)
    run.end(3, len(s2), detail=f"{len(s3)} after prefilter")

    # 5. Judge, one cached call per disagreement.
    run.begin(4)

    def on_event(st: Stats, label: str) -> None:
        run.progress(4, st.judged_live + st.judged_cached, current=label,
                     detail=f"{st.conflicts_written} contradiction(s)")

    st = adjudicate(ws, workers=2, on_event=on_event)
    judged = st.judged_live + st.judged_cached
    contradictions = rows(g, "MATCH (k:Conflict {status: 'open'}) RETURN count(k) AS n")[0]["n"]
    run.end(4, judged, detail=f"{contradictions} contradiction(s)"
            + (f", {len(st.failures)} judgement(s) failed" if st.failures else ""))

    per_source: dict[str, int] = {}
    for c in claims:
        sid = owner.get(c["source_id"])
        if sid:
            per_source[sid] = per_source.get(sid, 0) + 1
    now = int(time.time())
    for s in sources:
        if s["id"] in set(owner.values()):
            registry.update_source(s["id"], claims=per_source.get(s["id"], 0), last_read_at=now,
                                   docs=sum(1 for v in owner.values() if v == s["id"]))
    with run.lock:
        run.data["summary"] = {"documents": len(docs), "claims": len(claims), "pairs_compared": len(s2),
                               "judged": judged, "contradictions": contradictions}
