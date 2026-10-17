"""Unit tests for data/message_filter.py."""

from __future__ import annotations

import json
from pathlib import Path

from data.message_filter import (
    filter_messages,
    is_informative_message,
    matches_decision_phrase,
    matches_number_and_unit,
)


def test_decision_phrases():
    assert matches_decision_phrase("Team decided to switch retry limit.")
    assert matches_decision_phrase("We agreed on 15m intervals.")
    assert matches_decision_phrase("Going forward, all loads require seal checks.")
    assert matches_decision_phrase("We will deploy hotfix tonight.")
    assert matches_decision_phrase("Switching to new provider tomorrow.")
    assert matches_decision_phrase("Rule changed to mandatory approval.")
    assert not matches_decision_phrase("Routine operational sync completed.")


def test_number_and_unit():
    assert matches_number_and_unit("Snapshot completed in 14 seconds")
    assert matches_number_and_unit("Timeout duration is 4 seconds")
    assert matches_number_and_unit("Filing lead time is 48 hours")
    assert matches_number_and_unit("Retention extended to 72 hours")
    assert matches_number_and_unit("Allowed variance is 0.5 degrees C")
    assert not matches_number_and_unit("Investigation completed on read endpoints.")


def test_filter_on_corpus():
    corpus_p = Path(__file__).resolve().parent.parent / "data" / "out" / "corpus.json"
    if corpus_p.exists():
        corpus = json.loads(corpus_p.read_text(encoding="utf-8"))
        msgs = corpus.get("messages", [])
        strict_filtered = filter_messages(msgs, include_count_nouns=False)
        assert len(strict_filtered) == 221
