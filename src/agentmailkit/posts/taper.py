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

from ..plugins import get as _get_plugin
from ..plugins import post

# The spirit, not a checklist. Kept in the code so a user gets good pieces with
# zero configuration, and can override it entirely via options.taper.prompt.
TAPER_BRIEF = """Generate a Taper piece: computational poetry, in the tradition of the
Taper journal (taper.badquar.to), which publishes tiny computational literary works.

WHAT A TAPER PIECE ACTUALLY IS. Study these characteristics of the real form:

- **Language is usually the material.** Most pieces are built from a small curated
  vocabulary: a set of nouns, a list of exclamations, the lines of a poem. The words
  carry the meaning; the code arranges, reveals or destroys them. You are writing a
  poem whose typesetting is an algorithm, not decorating a data visualisation.
- **It unfolds over time.** Pieces reveal themselves. Words arrive one at a time on a
  timer, lines vanish one by one in a shuffled order, a form animates frame by frame.
  A static composition that just sits there is not a Taper piece.
- **The reader is part of it.** The piece answers to the hand: it responds to hover,
  movement or click. Time alone is a film; a Taper piece is something you can touch.
- **Committed palette.** Either a saturated LIGHT ground (warm sand, ochre, hot blue,
  acid yellow) with dark earth-toned text, or true black with pure white and one hot
  accent. Muddy grey text on near-black is the single most common failure. If you
  cannot read it instantly at a glance, it has failed.
- **Type is the material too.** Sizes vary dramatically inside one piece, from a huge
  opening line down to near-footnote. Default serif is common and good. Vary this run
  to run: serif, monospace, something enormous. Taper is not one look.
- **The whole field is the canvas.** Elements land across the entire viewport, often
  absolutely positioned at randomised percentages, not stacked politely in the middle.
- **A closing gesture.** When the sequence exhausts itself, something resolves: a final
  line, a last word, a state that says it is over.
- **Tiny and dense.** The real pieces are around two kilobytes of actual work. Terse
  code is part of the craft.

Do NOT produce: a grid of faint dots, a dashboard, a chart, a progress meter, or an
abstract shimmer with a caption underneath. Those are generative-art cliches, not
computational literature.

HARD RULES:
1. Output EXACTLY ONE <section> element and nothing else. No markdown fence, no commentary.
2. The opening tag must be: <section data-date='{date}' data-type='{slug}'>
3. Scope every CSS selector under a unique class so the piece cannot leak styles into a host page.
4. Your outermost element inside the section sets min-height:100vh and its own background.
5. Stay under {max_bytes} bytes total.
6. No external requests of any kind.
7. INTERACTION IS MANDATORY. The piece must respond to the reader, not only to a timer.
   Wire a real listener and make its effect obvious. Pick one and commit to it:
     - mousemove: words follow, scatter, warm, sharpen or fall away near the cursor
     - click or tap: plants a word, reveals the next line, breaks or repairs something
     - hover on a word: exposes a hidden layer, a number, a second reading
   It must feel like discovering a secret, and it must be discoverable without
   instructions. A piece that ignores the mouse entirely has failed this rule.

THEMATIC SEED - today's material. Mine it for a VOCABULARY: the proper nouns, numbers,
verbs and odd specifics worth setting in type. Then build the piece from those words.
Respond to its mood; do NOT restate or summarise it:
---
{seed}
---
"""

SECTION_RE = re.compile(r"<section\b.*?</section>", re.S | re.I)

# Interaction is a hard rule, so it is checked rather than hoped for. A piece that
# ignores the mouse is a film, not a Taper piece; when that happens we ask once more.
INTERACTION_RE = re.compile(
    r"addEventListener\s*\(\s*['\"](?:click|mousemove|mouseover|mouseenter|pointer\w+|touch\w+)"
    r"|on(?:click|mousemove|mouseover|mouseenter|pointerdown|touchstart)\s*="
    r"|:hover",
    re.I)


def _generate(ctx, prompt, model_name):
    raw = _get_plugin("model", model_name)(ctx, prompt) or ""
    match = SECTION_RE.search(raw)
    return match.group(0) if match else None


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
        piece = _generate(ctx, prompt, model_name)
        if piece and not INTERACTION_RE.search(piece):
            # Rule 7 is not optional. Ask once more before settling.
            print("[taper] piece had no interaction hook, regenerating once")
            retry = _generate(
                ctx, prompt + "\n\nYour previous attempt had NO interaction. Wire a real "
                              "mousemove, click or hover listener with an obvious effect.",
                model_name)
            if retry and INTERACTION_RE.search(retry):
                piece = retry
            elif retry:
                piece = retry
                print("[taper] still no interaction hook; writing anyway")
    except Exception as e:                          # fail open: the email already shipped
        print(f"[taper] generation failed, skipping piece: {e}")
        return

    if not piece:
        print("[taper] model did not return a <section> element, skipping piece")
        return

    if len(piece.encode("utf-8")) > max_bytes:
        print(f"[taper] piece is {len(piece.encode('utf-8'))}b, over the {max_bytes}b budget; writing anyway")

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{ctx.date}-{slug}.html"
    path.write_text(piece, encoding="utf-8")
    print(f"[taper] wrote {path} ({len(piece.encode('utf-8'))}b)")
