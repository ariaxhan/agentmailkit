"""Hugging Face Hub source - trending and brand-new models + datasets.

Deterministic by design: hits the public Hub JSON API directly (no auth, no LLM)
and returns a markdown block of exact model ids, download counts, likes, trending
scores and dates. Routing those numbers through an LLM web-fetch would invite
hallucinated figures; this way the digest carries real values it can cite verbatim.

Usage in a job:  "hf=hf:full"   (modes: full | pulse | brief)
    full   richest: trending + brand-new models AND datasets
    pulse  compact: trending models only
    brief  one line: the single top trending model

Fail-open by contract: any network or parse error returns a short notice instead
of raising, so a flaky Hub API can never break a scheduled run.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone

from ..plugins import source

API = "https://huggingface.co/api"
UA = "agentmailkit/0.1 (+https://github.com/ariaxhan/agentmailkit)"
TIMEOUT = 12

# The raw newest-created feed is noise: the freshest repos are empty test/spam
# pushes with zero traction. So "brand new" is drawn from the TRENDING pool and
# filtered to recent items, surfacing fresh drops already climbing the charts.
FRESH_MAX_DAYS = 14
TRENDING_POOL = 50


def _fetch(path):
    try:
        req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": UA, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return []


def _human(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "?"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n / 1000:.0f}k"
    return str(n)


def _age_days(iso):
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except (ValueError, TypeError):
        return None


def _ago(iso):
    d = _age_days(iso)
    if d is None:
        return ""
    return "today" if d <= 0 else ("1d ago" if d == 1 else f"{d}d ago")


def _clean(text, limit=110):
    if not text:
        return ""
    t = " ".join(str(text).split())
    for ch in ("#", "*", "`", ">", "|"):
        t = t.replace(ch, "")
    t = t.replace(chr(0x2014), ", ").replace(chr(0x2013), "-")
    t = " ".join(t.split())
    return (t[:limit].rstrip() + "...") if len(t) > limit else t


def _model_line(m):
    mid = m.get("id") or m.get("modelId", "?")
    bits = [f"{_human(m.get('downloads', 0))} downloads", f"{m.get('likes', 0)} likes"]
    if m.get("trendingScore"):
        bits.append(f"trending {m['trendingScore']}")
    if _ago(m.get("createdAt")):
        bits.append(_ago(m.get("createdAt")))
    return f"- **{mid}** ({m.get('pipeline_tag') or '-'}) - {', '.join(bits)} - https://huggingface.co/{mid}"


def _dataset_line(d):
    did = d.get("id", "?")
    bits = [f"{_human(d.get('downloads', 0))} downloads", f"{d.get('likes', 0)} likes"]
    if d.get("trendingScore"):
        bits.append(f"trending {d['trendingScore']}")
    if _ago(d.get("createdAt")):
        bits.append(_ago(d.get("createdAt")))
    head = f"- **{did}** - {', '.join(bits)} - https://huggingface.co/datasets/{did}"
    desc = _clean(d.get("description", ""))
    return f"{head}\n  {desc}" if desc else head


def _trending(kind, want):
    return _fetch(f"{kind}?sort=trendingScore&direction=-1&limit={want}") or []


def _fresh(kind, want, exclude):
    pool = _fetch(f"{kind}?sort=trendingScore&direction=-1&limit={TRENDING_POOL}") or []
    keep = []
    for r in pool:
        if r.get("id") in exclude:
            continue
        days = _age_days(r.get("createdAt"))
        if days is None or days > FRESH_MAX_DAYS:
            continue
        keep.append((days, r))
    keep.sort(key=lambda t: t[0])
    return [r for _, r in keep[:want]]


def _generic(spec: str) -> str:
    """Any Hub slice you care about, expressed as the Hub's own query string.

        models?author=meta-llama&limit=5
        models?filter=text-to-video&sort=downloads&direction=-1&limit=8
        datasets?search=clinical&sort=likes&limit=10
        models?search=gguf&sort=lastModified&limit=6

    Whatever the Hub API accepts, this accepts. No curated category list to outgrow.
    """
    kind, _, qs = spec.partition("?")
    kind = (kind.strip() or "models").lower()
    if kind not in ("models", "datasets"):
        return f"(hf: unknown collection {kind!r}; use 'models' or 'datasets')"
    params = qs.strip()
    if "limit=" not in params:
        params += ("&" if params else "") + "limit=8"
    if "sort=" not in params:
        params += "&sort=trendingScore&direction=-1"
    rows = _fetch(f"{kind}?{params}")
    if not rows:
        return f"(no Hugging Face results for {spec})"
    fmt = _model_line if kind == "models" else _dataset_line
    head = (f"## HUGGING FACE - {kind} ({params}) "
            f"(live from the Hub API; these numbers are real, cite them verbatim)\n")
    return head + "\n".join(fmt(r) for r in rows) + "\n"


@source("hf")
def hf_source(ctx, arg: str) -> str:
    """arg = a preset (full | pulse | brief) OR any Hub query string.

    Presets are convenience, not a ceiling: pass 'models?...' or 'datasets?...' to
    target exactly the slice of the Hub you care about.
    """
    mode = (arg or "full").strip()
    if mode.lower().startswith(("models", "datasets")):
        return _generic(mode)
    mode = mode.lower()
    header = "(live from the Hugging Face Hub API; these numbers are real, cite them verbatim)"

    if mode == "brief":
        t = _trending("models", 1)
        if not t:
            return "(Hugging Face Hub unavailable)"
        m = t[0]
        mid = m.get("id", "?")
        return (f"## HUGGING FACE - TOP TRENDING MODEL {header}\n"
                f"- **{mid}** ({m.get('pipeline_tag') or 'model'}) - "
                f"{_human(m.get('downloads', 0))} downloads, {m.get('likes', 0)} likes - "
                f"https://huggingface.co/{mid}\n")

    if mode == "pulse":
        t = _trending("models", 6)
        if not t:
            return "(Hugging Face Hub unavailable)"
        return "\n".join([f"## HUGGING FACE - TRENDING MODELS {header}\n"] + [_model_line(m) for m in t])

    # full
    tm = _trending("models", 8)
    nm = _fresh("models", 5, {m.get("id") for m in tm})
    td = _trending("datasets", 5)
    nd = _fresh("datasets", 4, {d.get("id") for d in td})
    if not (tm or td):
        return "(Hugging Face Hub unavailable)"

    out = [f"## HUGGING FACE - MODELS & DATASETS {header}\n"]
    for title, rows, fmt in (
        ("### Trending models", tm, _model_line),
        ("### Brand-new models (recent, already gaining traction)", nm, _model_line),
        ("### Trending datasets", td, _dataset_line),
        ("### Brand-new datasets", nd, _dataset_line),
    ):
        if rows:
            out.append(title)
            out += [fmt(r) for r in rows]
            out.append("")
    return "\n".join(out).rstrip() + "\n"
