"""Git sources (CONTRACT §9b v8): clone a repository so a workspace audit can read its documents.

Built for a public server, so every step is bounded:
  - only https:// URLs on allowed hosts (FAULTLINE_GIT_HOSTS), no credentials inside the URL
  - shallow clone of the latest commit, no tags, LFS objects not fetched
  - symlinks checked out as plain files (core.symlinks=false); the reader never follows one either
  - a time limit (FAULTLINE_GIT_TIMEOUT_S) and a size cap on disk (FAULTLINE_GIT_MAX_MB)
  - nothing in the repository is executed; only .md, .markdown and .txt files are read later
The token, when given, reaches git through GIT_CONFIG_* environment variables for that one
process: never on the command line (visible in process lists), never stored, never logged.
"""

from __future__ import annotations

import base64
import os
import stat
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_HOSTS = "github.com,gitlab.com,bitbucket.org"
# The username each host expects alongside a token in HTTP basic auth.
TOKEN_USER = {"github.com": "x-access-token", "gitlab.com": "oauth2", "bitbucket.org": "x-token-auth"}


class GitError(Exception):
    """A clone that did not happen, with a message fit to show the user."""


def clone_root() -> Path:
    return Path(os.environ.get("FAULTLINE_CLONE_DIR", ROOT / "data" / "clones"))


def checkout_path(workspace_id: str, source_id: str) -> Path:
    return clone_root() / workspace_id / source_id


def allowed_hosts() -> set[str]:
    return {h.strip().lower() for h in os.environ.get("FAULTLINE_GIT_HOSTS", DEFAULT_HOSTS).split(",") if h.strip()}


def validate_url(url: str) -> str:
    """Normalised URL, or GitError saying what is wrong with it."""
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise GitError("Use an https:// repository URL, e.g. https://github.com/owner/repo.")
    if parsed.username or parsed.password or "@" in parsed.netloc:
        raise GitError("Put the token in the token field, not in the URL.")
    host = (parsed.hostname or "").lower()
    if host not in allowed_hosts():
        raise GitError(f"{host or 'That host'} is not allowed on this server. Allowed: {', '.join(sorted(allowed_hosts()))}.")
    if not re.fullmatch(r"/[\w.-]+/[\w./-]+?(\.git)?/?", parsed.path or ""):
        raise GitError("That does not look like a repository URL. Use https://host/owner/repo.")
    if parsed.query or parsed.fragment:
        raise GitError("Remove the ? or # part of the URL.")
    return f"https://{host}{parsed.path.rstrip('/')}"


def _env(url: str, token: str | None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1", GCM_INTERACTIVE="never")
    config = [("core.symlinks", "false"), ("credential.helper", ""), ("protocol.allow", "never"),
              ("protocol.https.allow", "always")]
    if token:
        host = (urlparse(url).hostname or "").lower()
        basic = base64.b64encode(f"{TOKEN_USER.get(host, 'x-access-token')}:{token}".encode()).decode()
        config.append(("http.extraHeader", f"Authorization: Basic {basic}"))
    env["GIT_CONFIG_COUNT"] = str(len(config))
    for i, (k, v) in enumerate(config):
        env[f"GIT_CONFIG_KEY_{i}"], env[f"GIT_CONFIG_VALUE_{i}"] = k, v
    return env


def _rmtree(path: Path) -> None:
    def unlock(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    if path.exists():
        shutil.rmtree(path, onerror=unlock)


def _size_mb(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file() and not f.is_symlink()) / 1e6


def _clean(message: str, token: str | None) -> str:
    out = " ".join(message.split())[-400:]
    return out.replace(token, "***") if token else out


def _explain(stderr: str, token: str | None) -> str:
    """git's failure in plain words first, then git's own line for whoever needs it."""
    raw = _clean(stderr, token)
    low = raw.lower()
    if any(k in low for k in ("could not read username", "authentication failed", "repository not found",
                              "terminal prompts disabled", "returned error: 403", "returned error: 401")):
        head = ("The host refused the token: it may be wrong, expired, or without read access to this repository."
                if token else
                "The repository does not exist, or it is private. Check the URL; for a private repository add a "
                "token with read access.")
    elif "could not resolve host" in low or "unable to access" in low:
        head = "The server could not reach the host. Try again in a minute."
    else:
        head = "git could not clone it."
    return f"{head} (git: {raw})" if raw else head


def clone(url: str, dest: Path, token: str | None = None) -> None:
    """Shallow-clone url into dest (replacing it only on success). url must already be validated,
    except in tests, which clone local file:// repositories through this same function."""
    timeout = float(os.environ.get("FAULTLINE_GIT_TIMEOUT_S", "120"))
    max_mb = float(os.environ.get("FAULTLINE_GIT_MAX_MB", "200"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".clone-", dir=dest.parent))
    env = _env(url, token)
    if url.startswith("file://"):
        env["GIT_CONFIG_VALUE_2"] = "always"  # protocol.allow: tests only ever pass local paths here
    try:
        subprocess.run(["git", "clone", "--depth", "1", "--no-tags", "--single-branch", "--quiet", url, str(tmp / "repo")],
                       env=env, capture_output=True, text=True, timeout=timeout, check=True, stdin=subprocess.DEVNULL)
        repo = tmp / "repo"
        _rmtree(repo / ".git")  # history is not needed to read documents
        size = _size_mb(repo)
        if size > max_mb:
            raise GitError(f"The repository is {size:.0f} MB on disk; this server reads at most {max_mb:.0f} MB.")
        _rmtree(dest)
        repo.rename(dest)
    except subprocess.TimeoutExpired as e:
        raise GitError(f"Cloning took longer than {timeout:.0f} s and was stopped. Try a smaller repository.") from e
    except subprocess.CalledProcessError as e:
        raise GitError(_explain(e.stderr or e.stdout or "", token)) from e
    except FileNotFoundError as e:
        raise GitError("git is not installed on this server.") from e
    finally:
        try:
            _rmtree(tmp)
        except OSError:
            pass


def remove(workspace_id: str, source_id: str) -> None:
    try:
        _rmtree(checkout_path(workspace_id, source_id))
    except OSError:
        pass
