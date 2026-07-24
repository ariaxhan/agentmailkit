"""This day in history, from Wikipedia's on-this-day feed.

The kind of thing no cloud scheduler would ever think to put in your inbox, which is
exactly why it belongs here. A digest made only of work is a chore; one that also tells
you the Globe Theatre burned down on this date in 1613 is something you open.

Public Wikimedia REST endpoint: no key, no auth, real events with real article links.
Deterministic and fail-open like every other source.
"""
from __future__ import annotations

import json
import random
import urllib.request

from ..plugins import source

API = "https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday"
UA = "agentmailkit/0.1 (+https://github.com/ariaxhan/agentmailkit)"
TIMEOUT = 12
KINDS = ("events", "selected", "births", "deaths", "holidays")
DEFAULT_COUNT = 4


def _fetch(kind, month, day):
    url = f"{API}/{kind}/{month:02d}/{day:02d}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return {}


@source("history")
def history_source(ctx, arg: str) -> str:
    """arg = kind[#count][@seed]. kind is events|selected|births|deaths|holidays.

        history:events#4        four notable events on today's date
        history:selected#3      Wikipedia's own curated picks
        history:deaths#2

    Picks are sampled deterministically per date, so two runs on the same day agree
    but consecutive days do not repeat the same entries.
    """
    raw = (arg or "events").strip()
    count = DEFAULT_COUNT
    head, sep, tail = raw.rpartition("#")
    if sep and tail.strip().isdigit():
        raw, count = head.strip(), max(1, min(int(tail.strip()), 10))
    kind = (raw or "events").lower()
    if kind not in KINDS:
        return f"(history: unknown kind {kind!r}; use one of {', '.join(KINDS)})"

    y, m, d = (int(x) for x in ctx.date.split("-"))
    data = _fetch(kind, m, d)
    items = data.get(kind) or []
    if not items:
        return f"(no on-this-day {kind} available)"

    # Seed on the date so the selection is stable within a day and varies across days.
    rng = random.Random(f"{ctx.date}:{kind}")
    picks = items if len(items) <= count else rng.sample(items, count)
    picks.sort(key=lambda it: it.get("year") or 0)

    out = [f"## THIS DAY IN HISTORY - {kind} for {m:02d}/{d:02d} "
           f"(live from Wikipedia; years and links are real)\n"]
    for it in picks:
        year = it.get("year")
        text = " ".join(str(it.get("text", "")).split())
        pages = it.get("pages") or []
        link = ""
        if pages:
            link = (pages[0].get("content_urls", {}).get("desktop", {}).get("page")
                    or pages[0].get("content_urls", {}).get("mobile", {}).get("page") or "")
        when = f"**{year}**: " if year else ""
        out.append(f"- {when}{text}" + (f"\n  {link}" if link else ""))
    return "\n".join(out) + "\n"
