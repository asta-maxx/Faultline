"""Funnel stage 3 (CONTRACT §6): deterministic prefilter, pure Python, no model call.

A collapsed pair goes on to the LLM only if the two claims share a predicate AND
(their objects differ OR their polarities are opposite). Everything else is dropped
here for free.

Objects are compared after normalising case and whitespace only. "30 days" vs
"thirty days" still counts as differing: a false positive costs one cached LLM call,
a false negative hides a real contradiction, so the comparison stays deliberately dumb.
"""

from __future__ import annotations

from typing import Any


def norm(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def is_likely_contradiction(a_pred: str | None, a_obj: str | None, a_pol: str | None,
                            b_pred: str | None, b_obj: str | None, b_pol: str | None) -> bool:
    if not a_pred or norm(a_pred) != norm(b_pred):
        return False
    return norm(a_obj) != norm(b_obj) or a_pol != b_pol


def prefilter(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """pairs: rows from queries.candidate_collapse (§7.1 returns predicate, object and polarity)."""
    return [p for p in pairs
            if is_likely_contradiction(p["a_pred"], p["a_obj"], p["a_pol"],
                                       p["b_pred"], p["b_obj"], p["b_pol"])]
