"""Quickstart gallery - render a sample email set the moment the tool is installed.

The promise of the README is "five minutes, ending with a real email". Before anyone
wires a live source or a real inbox, they should be able to *see* what agentmailkit
produces from their own machine, with zero API keys and zero risk of sending anything.

`build_gallery` runs each configured job through the real pipeline with two invariants
enforced in code, not by convention:

1. **It can never send.** Delivery is forced to the `file` backend for every job, so a
   quickstart writes HTML to disk and nothing leaves the machine - the same "anything
   that must be true every run belongs in code" rule the taper interaction check uses.
2. **It is deterministic and offline by default.** The model is forced to `echo` unless
   overridden, so the gallery renders from the user's real local data (their files, their
   git log) without a key and without a network round-trip. Network sources fail open, so
   a job that reaches the web still renders - it just shows the source's own unavailable
   note when offline.

The output is a directory of rendered `.html` emails plus an `index.html` that links
them, one card per job, labelled with its theme. That page is the "here is what you get"
a new user sees first.
"""
from __future__ import annotations

import dataclasses
import html
from pathlib import Path
from typing import Any, Dict, List, Optional

from .runner import run as run_job
from .spec import Job

# A quickstart is a preview. These are stripped from every job so the gallery is a pure,
# repeatable render: no send, no dedup swallowing "already seen" items, no post-hook
# generation (taper) firing during what is meant to be a look-at-what-you-get demo.
_PREVIEW_DELIVERY = "file"


def _preview_job(job: Job, model: Optional[str]) -> Job:
    """A copy of the job safe to render for a preview: file delivery, no dedup, no posts."""
    return dataclasses.replace(
        job,
        delivery=_PREVIEW_DELIVERY,
        model=model or "echo",
        dedup=None,
        post=[],
    )


def build_gallery(cfg: Any, jobs: Dict[str, Job], out_dir: Optional[Path] = None,
                  model: Optional[str] = None) -> Dict[str, Any]:
    """Render every job to HTML and write a linking index. Never sends. Returns a receipt."""
    out_dir = Path(out_dir).expanduser() if out_dir else Path(cfg.out_dir) / "quickstart"
    out_dir = out_dir if out_dir.is_absolute() else Path(cfg.root) / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    # Point delivery + file writes at the gallery directory for this render only.
    preview_cfg = dataclasses.replace(cfg, out_dir=out_dir)

    cards: List[Dict[str, Any]] = []
    for job in jobs.values():
        pj = _preview_job(job, model)
        try:
            receipt = run_job(pj, preview_cfg, dry_run=False)
        except Exception as exc:                       # a broken job must not kill the gallery
            cards.append({"job": job.id, "error": f"{type(exc).__name__}: {exc}"})
            continue
        delivery = receipt.get("delivery", {})
        # Belt-and-braces: the pipeline should have used file delivery; prove it did.
        if delivery.get("backend") != _PREVIEW_DELIVERY:
            cards.append({"job": job.id, "error": f"unexpected delivery {delivery.get('backend')!r}"})
            continue
        path = delivery.get("result", {}).get("path", "")
        cards.append({
            "job": job.id,
            "theme": job.render or "(none)",
            "subject": delivery.get("subject", job.id),
            "path": path,
            "file": Path(path).name if path else "",
            "chars": receipt.get("rendered", {}).get("chars") or receipt.get("body_chars", 0),
        })

    index_path = out_dir / "index.html"
    index_path.write_text(_render_index(cards), encoding="utf-8")
    return {
        "quickstart": True,
        "out_dir": str(out_dir),
        "index": str(index_path),
        "model": model or "echo",
        "rendered": [c for c in cards if "error" not in c],
        "errors": [c for c in cards if "error" in c],
        "sent": False,
    }


def _render_index(cards: List[Dict[str, Any]]) -> str:
    """A self-contained warm gallery page. No external assets, no scripts, no emoji."""
    rows: List[str] = []
    for c in cards:
        if "error" in c:
            rows.append(
                f'    <li class="card err"><div class="jid">{html.escape(c["job"])}</div>'
                f'<div class="meta">could not render: {html.escape(c["error"])}</div></li>')
            continue
        rows.append(
            '    <li class="card">'
            f'<a href="{html.escape(c["file"])}"><div class="jid">{html.escape(c["job"])}</div>'
            f'<div class="subj">{html.escape(str(c["subject"]))}</div>'
            f'<div class="meta">theme {html.escape(c["theme"])} &middot; {c["chars"]} chars</div></a>'
            '</li>')
    ok = sum(1 for c in cards if "error" not in c)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>agentmailkit - quickstart gallery</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin: 0; background: #fafaf8; color: #23201b;
    font-family: Georgia, "Times New Roman", serif; line-height: 1.5; }}
  header {{ border-top: 6px solid #d4a574; padding: 40px 24px 8px; max-width: 760px; margin: 0 auto; }}
  h1 {{ font-size: 1.9rem; margin: 0 0 6px; letter-spacing: -0.01em; }}
  header p {{ margin: 0; color: #6b6459; font-size: 0.98rem; }}
  ul {{ list-style: none; padding: 8px 24px 56px; margin: 0 auto; max-width: 760px;
    display: grid; gap: 14px; }}
  .card {{ background: #fff; border: 1px solid #ece6dc; border-radius: 10px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03); }}
  .card a {{ display: block; padding: 18px 20px; text-decoration: none; color: inherit; }}
  .card a:hover {{ background: #fffdf9; }}
  .jid {{ font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 0.82rem;
    color: #b07d3f; letter-spacing: 0.02em; }}
  .subj {{ font-size: 1.12rem; margin: 3px 0 4px; }}
  .meta {{ font-size: 0.82rem; color: #8a8378; }}
  .err {{ padding: 18px 20px; color: #8a4b3f; }}
  .err .jid {{ color: #8a4b3f; }}
</style></head>
<body>
  <header>
    <h1>Quickstart gallery</h1>
    <p>{ok} sample email{'s' if ok != 1 else ''}, rendered locally from your own data. Nothing was sent.</p>
  </header>
  <ul>
{chr(10).join(rows)}
  </ul>
</body></html>
"""
