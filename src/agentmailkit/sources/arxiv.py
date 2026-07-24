"""arXiv source - recent papers by category or free-text query.

Deterministic like `hf`: queries the public arXiv Atom API and returns real titles,
authors, dates and abs links, so the digest cites papers that actually exist. The
single most common failure mode for LLM research digests is inventing plausible
paper titles; this removes the opportunity.

Usage in a job:
    "papers=arxiv:cs.AI"        latest 8 in a category
    "papers=arxiv:cs.LG:5"      latest 5 in a category
    "papers=arxiv:q=retrieval augmented generation:5"   free-text search

Fail-open: network or parse trouble returns a short notice, never raises.
"""
from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from ..plugins import source

API = "http://export.arxiv.org/api/query"
UA = "agentmailkit/0.1 (+https://github.com/ariaxhan/agentmailkit)"
TIMEOUT = 15
ATOM = "{http://www.w3.org/2005/Atom}"
DEFAULT_COUNT = 8
MAX_COUNT = 25


# arXiv's own query field prefixes. If the user writes any of them, we pass the query
# through verbatim rather than second-guessing it. No curated category list to outgrow.
_FIELDS = ("cat:", "all:", "ti:", "au:", "abs:", "co:", "jr:", "rn:", "id:")


def _parse_arg(arg: str):
    """Accept anything arXiv accepts.

        cs.AI                       bare category, the common case
        cs.LG:5                     category + count
        q=diffusion policy:5        free-text search + count
        cat:cs.AI AND abs:agent#8   raw arXiv query syntax + count
        au:Hinton#5                 any field prefix works

    Returns (search_query, count). '#N' is the unambiguous count separator; a trailing
    ':N' is still honoured for the simple category case.
    """
    raw = (arg or "cs.AI").strip()
    count = DEFAULT_COUNT

    # '#N' wins: unambiguous even when the query itself is full of colons.
    head, sep, tail = raw.rpartition("#")
    if sep and tail.strip().isdigit():
        raw, count = head.strip(), max(1, min(int(tail.strip()), MAX_COUNT))
    else:
        head, sep, tail = raw.rpartition(":")
        if sep and tail.isdigit():
            raw, count = head.strip(), max(1, min(int(tail), MAX_COUNT))

    low = raw.lower()
    if low.startswith("q="):
        return f"all:{raw[2:].strip()}", count
    if any(f in low for f in _FIELDS) or " and " in low or " or " in low:
        return raw, count                      # raw arXiv syntax, verbatim
    return f"cat:{raw}", count                 # bare category shorthand


def _clean(text, limit=200):
    if not text:
        return ""
    t = " ".join(str(text).split())
    t = t.replace(chr(0x2014), ", ").replace(chr(0x2013), "-")
    return (t[:limit].rstrip() + "...") if len(t) > limit else t


def _ago(iso):
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        d = (datetime.now(timezone.utc) - dt).days
        return "today" if d <= 0 else ("1d ago" if d == 1 else f"{d}d ago")
    except (ValueError, TypeError):
        return ""


@source("arxiv")
def arxiv_source(ctx, arg: str) -> str:
    search, count = _parse_arg(arg)
    params = urllib.parse.urlencode({
        "search_query": search,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "start": 0,
        "max_results": count,
    })
    try:
        req = urllib.request.Request(f"{API}?{params}", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            root = ET.fromstring(r.read().decode("utf-8"))
    except Exception:
        return f"(arXiv unavailable for {search})"

    entries = root.findall(f"{ATOM}entry")
    if not entries:
        return f"(no arXiv results for {search})"

    out = [f"## ARXIV - {search} (live from the arXiv API; titles and links are real, cite them verbatim)\n"]
    for e in entries:
        title = _clean((e.findtext(f"{ATOM}title") or "").replace("\n", " "), 160)
        link = (e.findtext(f"{ATOM}id") or "").strip()
        published = e.findtext(f"{ATOM}published") or ""
        authors = [a.findtext(f"{ATOM}name") or "" for a in e.findall(f"{ATOM}author")]
        who = ", ".join(a for a in authors[:3] if a)
        if len(authors) > 3:
            who += f" +{len(authors) - 3}"
        summary = _clean(e.findtext(f"{ATOM}summary") or "", 200)
        meta = " - ".join(x for x in (who, _ago(published)) if x)
        out.append(f"- **{title}**\n  {meta}\n  {summary}\n  {link}")
    return "\n".join(out) + "\n"
