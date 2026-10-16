"""Deterministic message filter for Northwind corpus.

Filters chat messages by identifying whether they contain:
1. A decision phrase: 'decided', 'agreed', 'we will', 'going forward', 'switching to', 'changed to'
2. A number followed by a unit of measurement (time, temperature, rate, storage, currency, percentage, or count).
"""

from __future__ import annotations

import re
from typing import Any

DECISION_PHRASES = (
    r"\bdecided\b",
    r"\bagreed\b",
    r"\bwe will\b",
    r"\bgoing forward\b",
    r"\bswitching to\b",
    r"\bchanged to\b",
)

# Common units of measurement (time, temperature, data, currency, percentage, frequency/retries)
MEASUREMENT_UNITS = (
    r"seconds?",
    r"secs?",
    r"minutes?",
    r"mins?",
    r"hours?",
    r"hrs?",
    r"days?",
    r"weeks?",
    r"months?",
    r"years?",
    r"ms",
    r"degrees?(?:\s*[cf])?",
    r"deg(?:\s*[cf])?",
    r"percent",
    r"%",
    r"usd",
    r"dollars?",
    r"bytes?",
    r"kb",
    r"mb",
    r"gb",
    r"tb",
    r"attempts?",
    r"retries",
    r"retry",
    r"times?",
)

# Item / document count nouns (e.g. declarations, records, items, orders, skus, batches)
COUNT_UNITS = (
    r"declarations?",
    r"records?",
    r"orders?",
    r"items?",
    r"skus?",
    r"batches?",
    r"loads?",
)

DECISION_PATTERN = re.compile("|".join(DECISION_PHRASES), re.IGNORECASE)

NUM_MEASUREMENT_PATTERN = re.compile(
    r"\b(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\s*[-]?\s*(?:"
    + "|".join(MEASUREMENT_UNITS)
    + r")\b",
    re.IGNORECASE,
)

NUM_BROAD_PATTERN = re.compile(
    r"\b(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred)\s*[-]?\s*(?:"
    + "|".join(MEASUREMENT_UNITS + COUNT_UNITS)
    + r")\b",
    re.IGNORECASE,
)


def matches_decision_phrase(text: str) -> bool:
    """Returns True if message text contains an explicit operational decision phrase."""
    return bool(DECISION_PATTERN.search(text))


def matches_number_and_unit(text: str, include_count_nouns: bool = False) -> bool:
    """Returns True if message text contains a number plus a unit of measurement.
    If include_count_nouns is True, also matches count nouns like '450 declarations'.
    """
    pattern = NUM_BROAD_PATTERN if include_count_nouns else NUM_MEASUREMENT_PATTERN
    return bool(pattern.search(text))


def is_informative_message(text: str, include_count_nouns: bool = False) -> bool:
    """Deterministic filter: returns True if message has a decision phrase or number+unit."""
    return matches_decision_phrase(text) or matches_number_and_unit(text, include_count_nouns=include_count_nouns)


def filter_messages(messages: list[dict[str, Any]], include_count_nouns: bool = False) -> list[dict[str, Any]]:
    """Filters a list of message dicts deterministically."""
    return [m for m in messages if is_informative_message(m.get("text", ""), include_count_nouns=include_count_nouns)]


if __name__ == "__main__":
    import json
    from pathlib import Path

    corpus_file = Path(__file__).resolve().parent.parent / "data" / "out" / "corpus.json"
    if corpus_file.exists():
        corpus = json.loads(corpus_file.read_text(encoding="utf-8"))
        all_msgs = corpus.get("messages", [])
        c_strict = len(filter_messages(all_msgs, include_count_nouns=False))
        c_broad = len(filter_messages(all_msgs, include_count_nouns=True))
        print(f"Total messages: {len(all_msgs)}")
        print(f"Matching strict units (time, temp, etc.): {c_strict}")
        print(f"Matching broad (including count nouns like declarations): {c_broad}")
