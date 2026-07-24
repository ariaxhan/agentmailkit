"""The seen-ledger: why a digest never repeats itself.

This is the piece that separates a scheduled digest from a scheduled annoyance.
Sources return whatever is currently trending or recently published, so on
consecutive days they return substantially the same items. Without a memory of what
already went out, day two is mostly a reprint of day one and the reader stops opening it.

The contract, and every clause is load-bearing:

1. **Filter before the prompt, not after.** Already-sent items are removed from the
   source material the model ever sees. You cannot ask a model to "not repeat
   yesterday" reliably, and paying to summarize items you will discard is waste.
2. **Record only after a successful send.** If delivery fails, nothing is marked
   seen, so the next run can still surface those items. Recording at generation
   time would silently burn a day of content on a failed send.
3. **Deterministic keys.** An item is identified by its normalized URL. No fuzzy
   similarity, no embeddings, no model judgement: the same item is the same item.
4. **A window, not forever.** Items age out (default 30 days) so a genuinely
   recurring thing can legitimately reappear later.

Storage is one JSONL file. Append-only, human-readable, greppable, trivially
inspected or hand-edited when something goes wrong.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Dict, Iterable, List, Set

URL_RE = re.compile(r"https?://[^\s<>)\"'\]]+")
DEFAULT_WINDOW_DAYS = 30


def normalize_url(url: str) -> str:
    """Strip the noise that makes the same link look like two links."""
    u = url.strip().rstrip(".,);:'\"")
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = re.sub(r"[?&](utm_[^=]+|ref|source|fbclid|gclid)=[^&]*", "", u)
    # arxiv.org/abs/2607.21595v2 -> .../2607.21595, so a revised paper is still the
    # same paper and does not resurface as "new" every time the authors update it.
    u = re.sub(r"(arxiv\.org/abs/\d+\.\d+)v\d+$", r"\1", u, flags=re.I)
    return u.rstrip("/?&#").lower()


class Ledger:
    """Append-only JSONL record of items already delivered, per job."""

    def __init__(self, path: Path, window_days: int = DEFAULT_WINDOW_DAYS):
        self.path = Path(path).expanduser()
        self.window_days = int(window_days)

    def seen(self, job_id: str) -> Set[str]:
        """Keys delivered for this job inside the window."""
        if not self.path.is_file():
            return set()
        cutoff = time.time() - self.window_days * 86400
        out: Set[str] = set()
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue                      # tolerate a torn write, never crash a run
                if rec.get("job") != job_id:
                    continue
                if float(rec.get("ts", 0)) < cutoff:
                    continue
                out.add(rec.get("key", ""))
        out.discard("")
        return out

    def record(self, job_id: str, keys: Iterable[str], date: str = "") -> int:
        keys = [k for k in dict.fromkeys(keys) if k]
        if not keys:
            return 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        with self.path.open("a", encoding="utf-8") as fh:
            for k in keys:
                fh.write(json.dumps({"job": job_id, "key": k, "ts": now, "date": date}) + "\n")
        return len(keys)


def _split_items(block: str) -> List[str]:
    """Split a markdown source block into headings and bullet items.

    A bullet item is a line starting with '- ' plus any following continuation lines
    (indented, or non-bullet non-heading non-blank). That matches how the hf, arxiv
    and rss sources emit multi-line entries.
    """
    segments: List[str] = []
    current: List[str] = []
    for line in block.splitlines():
        s = line.strip()
        starts_item = s.startswith("- ") or s.startswith("* ")
        is_heading = s.startswith("#")
        if starts_item or is_heading or not s:
            if current:
                segments.append("\n".join(current))
                current = []
            if is_heading or not s:
                segments.append(line)
                continue
        current.append(line)
    if current:
        segments.append("\n".join(current))
    return segments


def filter_block(block: str, seen: Set[str]) -> tuple:
    """Drop whole items whose first URL was already delivered.

    Returns (filtered_block, kept_keys, dropped_count). Segments without a URL
    (headings, prose, blank lines) always pass through untouched.
    """
    kept_lines: List[str] = []
    kept_keys: List[str] = []
    dropped = 0
    for seg in _split_items(block):
        m = URL_RE.search(seg)
        if not m:
            kept_lines.append(seg)
            continue
        key = normalize_url(m.group(0))
        if key in seen:
            dropped += 1
            continue
        kept_keys.append(key)
        kept_lines.append(seg)
    return "\n".join(kept_lines), kept_keys, dropped


def keys_in(text: str) -> List[str]:
    """Every normalized URL key present in a piece of text, in order, deduped."""
    return list(dict.fromkeys(normalize_url(u) for u in URL_RE.findall(text or "")))


def resolve(job, config) -> Dict:
    """Read a job's dedup setting. True, or a dict, or absent."""
    raw = getattr(job, "dedup", None)
    if not raw:
        return {}
    opts = {} if raw is True else dict(raw)
    path = opts.get("path") or "state/seen.jsonl"
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = Path(config.root) / p
    return {
        "path": p,
        "window_days": int(opts.get("window_days", DEFAULT_WINDOW_DAYS)),
        # "delivered": mark seen only what actually reached the reader (default, honest).
        # "presented": mark seen everything the model was shown, even if it omitted it.
        "record": opts.get("record", "delivered"),
    }
