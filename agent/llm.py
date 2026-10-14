"""Provider interface. Free tiers only (CONTRACT §2): Groq extracts, Gemini judges.

Models are chosen per role by env var, as "provider:model":

    FAULTLINE_EXTRACT_MODEL           default groq:openai/gpt-oss-120b
    FAULTLINE_EXTRACT_OVERFLOW_MODEL  default groq:openai/gpt-oss-20b   (Groq quotas are per model)
    FAULTLINE_JUDGE_MODEL             default gemini:gemini-3.5-flash
    FAULTLINE_EMBED_MODEL             default gemini:gemini-embedding-001

Defaults are pinned versions, never "*-latest" aliases: an alias can change the model
behind an unchanged cache key and behind CONTRADICTS.method.

Keys come from GEMINI_API_KEY / GROQ_API_KEY (CONTRACT §2), read from the environment or
from a .env file at the repo root (never committed). Every call goes through the
disk cache first; the cache is checked for every candidate model before any network call,
so a re-run never spends quota on something already answered by primary or overflow.
"""

from __future__ import annotations

import os
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

from agent import cache

ROLE_DEFAULTS = {
    "extract": "groq:openai/gpt-oss-120b",
    "extract_overflow": "groq:openai/gpt-oss-20b",
    "judge": "gemini:gemini-3.5-flash",
    "embed": "gemini:gemini-embedding-001",
}
ROLE_FALLBACK = {"extract": "extract_overflow"}


def _load_dotenv(path: Path = Path(__file__).resolve().parent.parent / ".env") -> None:
    """Minimal KEY=VALUE reader. Real environment variables always win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key and not key.startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


class ProviderError(Exception):
    """Non-retryable provider failure. The message carries the HTTP status and body."""


class Transient(ProviderError):
    """5xx or timeout: retried with exponential backoff."""


class RateLimited(ProviderError):
    """HTTP 429. Retried after the provider's own delay when short, otherwise overflow."""

    def __init__(self, msg: str, retry_after: float | None = None):
        super().__init__(msg)
        self.retry_after = retry_after


MAX_ATTEMPTS = 4
MAX_WAIT_S = 65.0  # per-minute windows are waited out; daily quotas (hours) go to overflow


class Provider(Protocol):
    def generate(self, model: str, prompt: str, content: str, params: dict[str, Any]) -> str: ...
    def embed(self, model: str, text: str) -> list[float]: ...


@dataclass
class Result:
    value: Any          # str for generate, list[float] for embed
    spec: str           # "provider:model" that produced it
    cached: bool

    @property
    def model(self) -> str:
        """Bare model name, e.g. "gemini-3.5-flash". This is what CONTRADICTS.method records."""
        return self.spec.split(":", 1)[1]


def _retry_after(resp: httpx.Response) -> float | None:
    if resp.headers.get("retry-after"):
        try:
            return float(resp.headers["retry-after"])
        except ValueError:
            pass
    m = re.search(r'"retryDelay":\s*"([\d.]+)s"', resp.text)  # Gemini RetryInfo
    return float(m.group(1)) if m else None


def _check(resp: httpx.Response) -> dict:
    if resp.is_success:
        return resp.json()
    msg = f"HTTP {resp.status_code}: {' '.join(resp.text.split())[:300]}"
    if resp.status_code == 429:
        raise RateLimited(msg, _retry_after(resp))
    if resp.status_code >= 500:
        raise Transient(msg)
    raise ProviderError(msg)


def _post(url: str, **kw) -> dict:
    try:
        return _check(httpx.post(url, timeout=kw.pop("timeout", 60), **kw))
    except httpx.TimeoutException as e:
        raise Transient(f"timeout: {type(e).__name__}") from e


def _key(var: str) -> str:
    v = os.environ.get(var)
    if not v:
        raise RuntimeError(f"{var} is not set")
    return v


class Gemini:
    BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def generate(self, model, prompt, content, params):
        body = {"systemInstruction": {"parts": [{"text": prompt}]},
                "contents": [{"role": "user", "parts": [{"text": content}]}],
                "generationConfig": params}
        data = _post(f"{self.BASE}/{model}:generateContent", json=body,
                     headers={"x-goog-api-key": _key("GEMINI_API_KEY")})
        cand = data["candidates"][0]
        parts = cand.get("content", {}).get("parts")
        if not parts:
            raise RuntimeError(f"gemini returned no text (finishReason={cand.get('finishReason')})")
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))

    def embed(self, model, text):
        data = _post(f"{self.BASE}/{model}:embedContent", json={"content": {"parts": [{"text": text}]}},
                     headers={"x-goog-api-key": _key("GEMINI_API_KEY")})
        return data["embedding"]["values"]


class Groq:
    URL = "https://api.groq.com/openai/v1/chat/completions"

    def generate(self, model, prompt, content, params):
        body = {"model": model, **params,
                "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": content}]}
        data = _post(self.URL, json=body, headers={"Authorization": f"Bearer {_key('GROQ_API_KEY')}"})
        return data["choices"][0]["message"]["content"]

    def embed(self, model, text):
        raise NotImplementedError("Groq is extraction overflow only; embeddings are Gemini")


class Echo:
    """Offline provider for tests and cache proofs. Never use for real extraction."""

    def __init__(self):
        self.calls = 0

    def generate(self, model, prompt, content, params):
        self.calls += 1
        return f"echo[{model}]: {content}"

    def embed(self, model, text):
        self.calls += 1
        return [float(len(text)), 0.0]


PROVIDERS: dict[str, Provider] = {"gemini": Gemini(), "groq": Groq(), "echo": Echo()}


def model_for(role: str) -> str:
    return os.environ.get(f"FAULTLINE_{role.upper()}_MODEL", ROLE_DEFAULTS[role])


def _candidates(role: str) -> list[str]:
    chain = [model_for(role)]
    if role in ROLE_FALLBACK:
        chain.append(model_for(ROLE_FALLBACK[role]))
    return chain


def _call(role: str, op: str, prompt: str, content: str, params: dict[str, Any]) -> Result:
    chain = _candidates(role)
    keys = {spec: cache.cache_key(spec, op, prompt, content, params) for spec in chain}
    for spec in chain:
        hit = cache.get(keys[spec])
        if hit is not None:
            return Result(hit, spec, cached=True)

    last: Exception | None = None
    for spec in chain:
        provider_name, model = spec.split(":", 1)
        provider = PROVIDERS[provider_name]
        for attempt in range(MAX_ATTEMPTS):
            try:
                value = (provider.generate(model, prompt, content, params) if op == "generate"
                         else provider.embed(model, content))
            except RateLimited as e:
                last = e
                if e.retry_after is None or e.retry_after > MAX_WAIT_S:
                    break  # long quota window: go to the overflow model instead of waiting
                time.sleep(e.retry_after + random.uniform(0.2, 1.0))
                continue
            except Transient as e:
                last = e
                time.sleep(min(2 ** attempt, 8) + random.uniform(0, 1))
                continue
            cache.put(keys[spec], value, {"model": spec, "op": op, "role": role})
            return Result(value, spec, cached=False)
    raise last or RuntimeError(f"no provider answered for role {role}")


def generate(role: str, prompt: str, content: str, **params: Any) -> Result:
    """role: "extract" or "judge". params go to the provider's generation config and into the cache key."""
    return _call(role, "generate", prompt, content, params)


def embed(text: str) -> Result:
    return _call("embed", "embed", "", text, {})
