"""Proves the LLM disk cache hits on a repeat call.

    python -m agent.cache_proof                              # offline, echo provider
    python -m agent.cache_proof gemini:gemini-2.5-flash      # live, needs GEMINI_API_KEY
    python -m agent.cache_proof groq:openai/gpt-oss-120b     # live, needs GROQ_API_KEY

Run each twice in separate processes: the second must report cached=True and make no HTTP call.
"""

import os
import sys
import time

from agent import llm

os.environ["FAULTLINE_JUDGE_MODEL"] = sys.argv[1] if len(sys.argv) > 1 else "echo:echo-1"

t = time.perf_counter()
r = llm.generate("judge", "Reply with exactly one word: ok", "ping", temperature=0)
ms = (time.perf_counter() - t) * 1000
print(f"spec={r.spec} method={r.model} cached={r.cached} {ms:.0f}ms value={r.value.strip()[:60]!r}")
