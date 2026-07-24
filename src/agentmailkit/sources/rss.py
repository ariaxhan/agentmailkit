"""RSS and Atom sources, including deliberately multi-perspective news.

`rss` is the workhorse: almost everything interesting publishes a feed, so this one
plugin unlocks archaeology, science, security advisories, a niche blog, a subreddit,
a release feed, a court docket. If you can find a feed for it, you can put it in an email.

`news` is the same machinery with an opinion: it takes LABELLED feeds and keeps the
labels in the output, so the prompt can ask the model to contrast how different
outlets framed the same event rather than flattening them into one neutral mush.
That contrast is the interesting part, and it is only possible because the labels
survive all the way into the prompt.

Both are deterministic (real titles, real links, real timestamps) and fail open.
"""
from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from ..plugins import source

UA = "agentmailkit/0.1 (+https://github.com/ariaxhan/agentmailkit)"
TIMEOUT = 15
DEFAULT_ITEMS = 6
MAX_ITEMS = 30
ATOM = "{http://www.w3.org/2005/Atom}"
TAG_RE = re.compile(r"<[^>]+>")


def _strip(text, limit=180):
    if not text:
        return ""
    t = TAG_RE.sub(" ", str(text))
    t = (t.replace("&nbsp;", " ").replace("&amp;", "&")
          .replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'")
          .replace("&quot;", '"').replace(chr(0x2014), ", ").replace(chr(0x2013), "-"))
    t = " ".join(t.split())
    return (t[:limit].rstrip() + "...") if len(t) > limit else t


def _ago(raw):
    if not raw:
        return ""
    dt = None
    for parse in (lambda s: parsedate_to_datetime(s),
                  lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))):
        try:
            dt = parse(raw)
            break
        except Exception:
            continue
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    days = (datetime.now(timezone.utc) - dt).days
    return "today" if days <= 0 else ("1d ago" if days == 1 else f"{days}d ago")


def _fetch_feed(url: str, want: int):
    """Return ([(title, link, when, summary)], error_or_None).

    Fail-open, but never silently: the caller reports the actual reason. A feed that
    quietly returns nothing is indistinguishable from a feed that is genuinely empty,
    and that ambiguity hides breakage for weeks.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
    except Exception as e:
        return [], f"fetch failed: {type(e).__name__}"

    head = raw[:200].lstrip()[:20].lower()
    if head.startswith(b"<!doctype html") or head.startswith(b"<html"):
        return [], "served HTML, not a feed (wrong URL, or the site has no RSS)"
    try:
        root = ET.fromstring(raw)
    except Exception as e:
        return [], f"not parseable XML: {type(e).__name__}"

    out = []
    items = root.findall(".//item")                   # RSS 2.0
    if items:
        for it in items[:want]:
            out.append((
                _strip(it.findtext("title"), 160),
                (it.findtext("link") or "").strip(),
                _ago(it.findtext("pubDate")),
                _strip(it.findtext("description"), 180),
            ))
        return out, None
    for e in root.findall(f".//{ATOM}entry")[:want]:  # Atom
        link = ""
        for ln in e.findall(f"{ATOM}link"):
            if ln.get("rel", "alternate") == "alternate":
                link = ln.get("href", "")
                break
        out.append((
            _strip(e.findtext(f"{ATOM}title"), 160),
            link or (e.findtext(f"{ATOM}id") or "").strip(),
            _ago(e.findtext(f"{ATOM}updated") or e.findtext(f"{ATOM}published")),
            _strip(e.findtext(f"{ATOM}summary") or e.findtext(f"{ATOM}content"), 180),
        ))
    return out, (None if out else "no items found in feed")


def _split_count(arg: str, default=DEFAULT_ITEMS):
    raw = (arg or "").strip()
    head, sep, tail = raw.rpartition("#")
    if sep and tail.strip().isdigit():
        return head.strip(), max(1, min(int(tail.strip()), MAX_ITEMS))
    return raw, default


def _render(label, rows, err=None):
    if err:
        return [f"- (feed unavailable for {label}: {err})"]
    if not rows:
        return [f"- (no recent items: {label})"]
    lines = []
    for title, link, when, summary in rows:
        meta = f" - {when}" if when else ""
        lines.append(f"- **{title}**{meta}\n  {summary}\n  {link}" if summary
                     else f"- **{title}**{meta}\n  {link}")
    return lines


@source("rss")
def rss_source(ctx, arg: str) -> str:
    """arg = one or more feed URLs separated by '|', optional '#N' items per feed.

        rss:https://www.archaeology.org/feed
        rss:https://hnrss.org/frontpage|https://lobste.rs/rss#5

    Not every site has a feed. If one does not, this says so explicitly rather than
    returning a convincing silence.
    """
    spec, want = _split_count(arg)
    urls = [u.strip() for u in spec.split("|") if u.strip()]
    if not urls:
        return "(rss: no feed URL given)"
    out = []
    for url in urls:
        rows, err = _fetch_feed(url, want)
        host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        out.append(f"### {host}")
        out += _render(host, rows, err)
        out.append("")
    return "## FEEDS (live; titles and links are real, cite them verbatim)\n\n" + "\n".join(out).rstrip() + "\n"


@source("news")
def news_source(ctx, arg: str) -> str:
    """Labelled feeds, labels preserved, so the model can contrast framings.

        news:Reuters=https://feeds.reuters.com/reuters/topNews|AP=https://feeds.apnews.com/rss/apf-topnews#5

    The labels are the whole point. Ask the prompt to note where outlets agree on
    facts but diverge on emphasis; that comparison is impossible if you merge feeds.
    """
    spec, want = _split_count(arg)
    parts = [p.strip() for p in spec.split("|") if p.strip()]
    if not parts:
        return "(news: no feeds given; use Label=URL|Label=URL)"
    out = []
    for part in parts:
        label, sep, url = part.partition("=")
        if not sep:
            url, label = part, re.sub(r"^https?://(www\.)?", "", part).split("/")[0]
        rows, err = _fetch_feed(url.strip(), want)
        out.append(f"### {label.strip()}")
        out += _render(label.strip(), rows, err)
        out.append("")
    return ("## NEWS BY OUTLET (live; each section is one outlet's own framing of today)\n"
            "Compare across sections: where they agree on facts and where the emphasis diverges.\n\n"
            + "\n".join(out).rstrip() + "\n")
