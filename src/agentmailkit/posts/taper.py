"""Taper - computational poetry as an optional companion to a digest.

The Taper form originates with https://taper.badquar.to, a journal of tiny
computational literature where each piece must fit in a couple of kilobytes. The
constraint is the medium: one file, no external assets, meaning carried by form and
algorithm rather than prose. All credit for the form belongs there; this plugin only
generates pieces in its spirit.

Where the email says what happened, the taper piece is an abstract response to it.
Same run, same material, a second and stranger output.

This is deliberately a POST plugin, not a delivery backend: it runs only after the
email is safely sent, and it fails open. A weird generative piece must never be the
reason a digest does not arrive.

Enable it on a job:

    "post": ["taper"],
    "options": { "taper": { "out_dir": "pieces", "model": "claude_cli:sonnet", "max_bytes": 4096 } }

Every option is optional; by default it writes to <out_dir>/pieces using the job's
own model. Output: <out>/<date>-<job id>.html containing a single <section> element,
which is what makes pieces trivially embeddable in a static index page.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..plugins import post, get as _get_plugin

# The spirit, not a checklist. Kept in the code so a user gets good pieces with
# zero configuration, and can override it entirely via options.taper.prompt.
TAPER_BRIEF = """Generate a Taper piece: computational poetry.

CORE ESSENCE (spirit, not a checklist):
- Computational poetry: meaning through form, algorithm and interaction. The medium is part of the message.
- Constraint as creative force: one file, no external assets. One idea, maximum impact, minimum means.
- Abstract and experiential. NOT an article, NOT a summary, NOT literal content. A poem in code.
- Generative or interactive: the piece responds (click, hover, mousemove, time) or generates.
  The interaction should feel like discovering a secret.
- Self-contained: inline style and script only, no external resources, no images, no fonts to fetch.

VARY YOUR STYLE. Palette, typography and technique should differ run to run:
dark or light or gradient, serif or mono or display. Taper is not one look.

HARD RULES:
1. Output EXACTLY ONE <section> element and nothing else. No markdown fence, no commentary.
2. The opening tag must be: <section data-date='{date}' data-type='{slug}'>
3. Scope every CSS selector under a unique class so the piece cannot leak styles into a host page.
4. Stay under {max_bytes} bytes total.
5. No external requests of any kind.

THEMATIC SEED - today's material. Respond to its mood and shape. Do NOT restate it:
---
{seed}
---
"""

SECTION_RE = re.compile(r"<section\b.*?</section>", re.S | re.I)


@post("taper")
def taper(ctx, body: str) -> None:
    opts = (ctx.job.options or {}).get("taper", {}) or {}
    max_bytes = int(opts.get("max_bytes", 4096))
    slug = opts.get("slug", ctx.job.id)

    out_dir = Path(opts.get("out_dir") or (Path(ctx.config.out_dir) / "pieces")).expanduser()
    if not out_dir.is_absolute():
        out_dir = Path(ctx.config.root) / out_dir

    # Seed the piece with the digest itself, trimmed: it is inspiration, not input data.
    seed = (body or "").strip()
    seed = re.sub(r"<[^>]+>", " ", seed)          # strip any HTML so the model reads prose
    seed = " ".join(seed.split())[:1500]

    prompt_tmpl = opts.get("prompt") or TAPER_BRIEF
    prompt = (prompt_tmpl
              .replace("{date}", ctx.date)
              .replace("{slug}", slug)
              .replace("{max_bytes}", str(max_bytes))
              .replace("{seed}", seed))

    model_ref = opts.get("model") or ctx.job.model or ctx.config.default_model
    model_name = model_ref.partition(":")[0]

    try:
        raw = _get_plugin("model", model_name)(ctx, prompt) or ""
    except Exception as e:                          # fail open: the email already shipped
        print(f"[taper] generation failed, skipping piece: {e}")
        return

    match = SECTION_RE.search(raw)
    if not match:
        print("[taper] model did not return a <section> element, skipping piece")
        return
    piece = match.group(0)

    if len(piece.encode("utf-8")) > max_bytes:
        print(f"[taper] piece is {len(piece.encode('utf-8'))}b, over the {max_bytes}b budget; writing anyway")

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{ctx.date}-{slug}.html"
    path.write_text(piece, encoding="utf-8")
    print(f"[taper] wrote {path} ({len(piece.encode('utf-8'))}b)")
