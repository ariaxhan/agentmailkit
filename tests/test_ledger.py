"""The seen-ledger: the dedup contract that stops day two being a reprint of day one."""
from __future__ import annotations

from agentmailkit import ledger


def test_arxiv_version_collapses_to_one_key():
    a = ledger.normalize_url("https://arxiv.org/abs/2607.21595v1")
    b = ledger.normalize_url("https://arxiv.org/abs/2607.21595v2")
    assert a == b  # a revised paper is the same paper, never resurfaces as new


def test_normalize_strips_tracking_and_scheme():
    k = ledger.normalize_url("https://www.Example.com/post/?utm_source=x&ref=y")
    assert k == "example.com/post"


def test_filter_block_drops_seen_items_only():
    block = ("- First https://example.com/a\n"
             "- Second https://example.com/b\n"
             "## a heading with no url\n"
             "- Third https://example.com/c\n")
    seen = {ledger.normalize_url("https://example.com/b")}
    filtered, kept, dropped = ledger.filter_block(block, seen)
    assert dropped == 1
    assert "example.com/a" in kept and "example.com/c" in kept
    assert "https://example.com/b" not in filtered
    assert "a heading with no url" in filtered  # non-url segments always pass through


def test_record_then_seen_roundtrips(tmp_path):
    book = ledger.Ledger(tmp_path / "seen.jsonl", window_days=30)
    n = book.record("job1", ["example.com/a", "example.com/b"], "2026-07-24")
    assert n == 2
    seen = book.seen("job1")
    assert seen == {"example.com/a", "example.com/b"}
    assert book.seen("other-job") == set()  # keyed per job


def test_record_is_deduped():
    assert ledger.keys_in("see https://x.com/1 and https://x.com/1 again") == ["x.com/1"]
