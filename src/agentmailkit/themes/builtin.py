"""Deterministic HTML email themes.

This is the layer that makes "beautiful" and "stable" the same decision.

The model writes words. It never writes markup. A render plugin takes the model's
markdown and produces the finished email, so the layout, palette, spacing and
structure are byte-identical every single run and only the content moves. Ask a
model for HTML and you get a different email every day; some days it forgets the
styles entirely. This removes that whole class of drift.

Everything is inline-styled because that is the only thing email clients render
reliably. No <style> block, no external fonts, no images to fetch.

Supported markdown, deliberately a small subset:

    # Title            page title (usually redundant with the subject)
    ## Section         starts a new card
    ### Subheading     heading inside the current card
    - item             bullet list
    > quote            pull quote
    ---                divider
    **bold**  *em*  `code`  [text](url)
    @stats: Label=Value, Label=Value      a row of KPI tiles

Themes register under `render`; select per job with `"render": "warm"`.
"""
from __future__ import annotations

import html
import re

from ..plugins import render

# Palette lifted from a real, long-running daily brief. Override per job via
# options.theme, or globally via config.extra.theme.
WARM = {
    "ground": "#fafaf8",
    "card": "#ffffff",
    "ink": "#2a2a2a",
    "muted": "#999999",
    "accent": "#d4a574",
    "accent_soft": "#e8c9a0",
    "rule": "#ece9e2",
    "font": "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif",
    "mono": "'SF Mono','Fira Code',ui-monospace,monospace",
}

SLATE = {
    **WARM,
    "ground": "#f5f7fa",
    "ink": "#1f2933",
    "accent": "#4a7c9e",
    "accent_soft": "#a3c4d9",
    "rule": "#e3e8ee",
}

INK = {
    **WARM,
    "ground": "#14161a",
    "card": "#1c1f26",
    "ink": "#e8e6e1",
    "muted": "#8a8f98",
    "accent": "#d4a574",
    "rule": "#2a2f38",
}

PALETTES = {"warm": WARM, "slate": SLATE, "ink": INK}

# House style enforced by the engine, not requested from the model.
# A prompt saying "never use em dashes" is a suggestion the model will eventually
# ignore; a substitution at render time is a guarantee. Same principle as the theme
# owning markup: anything that must be true every single run belongs in code.
HOUSE_STYLE = {
    "—": " - ",     # em dash
    "–": "-",       # en dash
    " ": " ",       # non-breaking space
}

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_EM = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_CODE = re.compile(r"`([^`]+)`")
_BARE_URL = re.compile(r"(?<![\"'=(])\bhttps?://[^\s<>)\]]+")


def _inline(text: str, p: dict) -> str:
    """Escape, then re-introduce only the inline markup we allow."""
    t = html.escape(text, quote=False)
    t = _CODE.sub(
        lambda m: f'<code style="font-family:{p["mono"]};font-size:13px;'
                  f'background:rgba(0,0,0,.05);padding:1px 5px;border-radius:4px;">{m.group(1)}</code>', t)
    t = _LINK.sub(
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}" '
                  f'style="color:{p["ink"]};text-decoration:none;border-bottom:1px solid {p["accent"]};">'
                  f'{m.group(1)}</a>', t)
    # Bare URLs become links too, so sources that emit plain links still look right.
    t = _BARE_URL.sub(
        lambda m: f'<a href="{m.group(0)}" style="color:{p["muted"]};text-decoration:none;'
                  f'border-bottom:1px solid {p["rule"]};word-break:break-all;">{m.group(0)}</a>', t)
    t = _BOLD.sub(lambda m: f'<strong style="font-weight:650;">{m.group(1)}</strong>', t)
    t = _EM.sub(lambda m: f"<em>{m.group(1)}</em>", t)
    return t


def _stat_tiles(spec: str, p: dict) -> str:
    """'@stats: Sparks=4, Threads=3' -> a row of KPI tiles."""
    pairs = []
    for chunk in spec.split(","):
        label, _, value = chunk.partition("=")
        if value.strip():
            pairs.append((label.strip(), value.strip()))
    if not pairs:
        return ""
    width = max(1, int(100 / len(pairs)))
    cells = []
    for label, value in pairs:
        cells.append(
            f'<td width="{width}%" style="background:{p["card"]};border-left:3px solid {p["accent"]};'
            f'border-radius:8px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,.08);">'
            f'<div style="font-size:24px;font-weight:700;font-family:{p["mono"]};color:{p["ink"]};">'
            f'{html.escape(value)}</div>'
            f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;'
            f'color:{p["muted"]};margin-top:2px;">{html.escape(label)}</div></td>')
    spacer = '<td width="8"></td>'
    return ('<div style="padding:16px 24px 0 24px;">'
            '<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;"><tr>'
            + spacer.join(cells) + '</tr></table></div>')


def _flush_list(items, p):
    if not items:
        return ""
    lis = "".join(
        f'<li style="margin:0 0 7px 0;font-size:14px;line-height:1.55;color:{p["ink"]};">{i}</li>'
        for i in items)
    return f'<ul style="margin:8px 0 0 0;padding-left:20px;">{lis}</ul>'


def _markdown_to_blocks(text: str, p: dict):
    """Return (stat_tiles_html, [card_html, ...]). A '## ' heading opens a new card."""
    tiles = ""
    cards = []
    body = []          # html fragments for the current card
    title = None
    bullets = []
    para = []

    def flush_para():
        if para:
            body.append(f'<p style="margin:0 0 11px 0;font-size:14px;line-height:1.6;'
                        f'color:{p["ink"]};">{_inline(" ".join(para), p)}</p>')
            para.clear()

    def flush_bullets():
        if bullets:
            body.append(_flush_list([_inline(b, p) for b in bullets], p))
            bullets.clear()

    def close_card():
        flush_para(); flush_bullets()
        if title or body:
            head = (f'<h2 style="margin:0 0 12px 0;font-size:13px;font-weight:700;'
                    f'text-transform:uppercase;letter-spacing:.6px;color:{p["ink"]};">'
                    f'{_inline(title, p)}</h2>') if title else ""
            cards.append(
                f'<div style="background:{p["card"]};border-radius:8px;'
                f'box-shadow:0 1px 3px rgba(0,0,0,.08);padding:20px;margin-bottom:14px;">'
                f'{head}{"".join(body)}</div>')
        body.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.lower().startswith("@stats:"):
            flush_para(); flush_bullets()
            tiles = _stat_tiles(stripped.split(":", 1)[1], p)
            continue
        if not stripped:
            flush_para(); flush_bullets()
            continue
        if stripped.startswith("## "):
            close_card()
            title = stripped[3:].strip()
            continue
        if stripped.startswith("# "):
            continue                                   # page title comes from the subject
        if stripped.startswith("### "):
            flush_para(); flush_bullets()
            body.append(f'<h3 style="margin:14px 0 6px 0;font-size:13px;font-weight:700;'
                        f'color:{p["ink"]};">{_inline(stripped[4:], p)}</h3>')
            continue
        if stripped in ("---", "***", "___"):
            flush_para(); flush_bullets()
            body.append(f'<hr style="border:0;border-top:1px solid {p["rule"]};margin:14px 0;">')
            continue
        if stripped.startswith("> "):
            flush_para(); flush_bullets()
            body.append(f'<blockquote style="margin:10px 0;padding:2px 0 2px 14px;'
                        f'border-left:3px solid {p["accent"]};color:{p["ink"]};font-size:14px;'
                        f'line-height:1.55;font-style:italic;">{_inline(stripped[2:], p)}</blockquote>')
            continue
        if stripped.startswith(("- ", "* ")):
            flush_para()
            bullets.append(stripped[2:])
            continue
        flush_bullets()
        para.append(stripped)

    close_card()
    return tiles, cards


def _shell(title: str, subtitle: str, tiles: str, cards, footer: str, p: dict) -> str:
    return (
        f'<div style="max-width:600px;margin:0 auto;background:{p["ground"]};'
        f'font-family:{p["font"]};color:{p["ink"]};padding-bottom:8px;">'
        f'<div style="height:3px;background:linear-gradient(90deg,{p["accent"]},{p["accent_soft"]});'
        f'border-radius:2px;"></div>'
        f'<div style="padding:24px 24px 0 24px;">'
        f'<h1 style="margin:0;font-size:22px;font-weight:700;letter-spacing:-.3px;'
        f'color:{p["ink"]};">{html.escape(title)}</h1>'
        f'<p style="margin:4px 0 0 0;font-size:13px;color:{p["muted"]};">{html.escape(subtitle)}</p>'
        f'</div>{tiles}'
        f'<div style="padding:16px 24px 0 24px;">{"".join(cards)}</div>'
        f'<div style="padding:4px 24px 20px 24px;font-size:11px;color:{p["muted"]};">{footer}</div>'
        f'</div>')


def _palette(ctx, name):
    base = dict(PALETTES.get(name, WARM))
    base.update((getattr(ctx.config, "extra", {}) or {}).get("theme", {}))
    base.update((ctx.job.options or {}).get("theme", {}))
    return base


def _themed(name):
    def _fn(ctx, body: str) -> str:
        p = _palette(ctx, name)
        opts = (ctx.job.options or {}).get("render", {})
        title = ctx.render(opts.get("title") or ctx.job.subject or ctx.job.id)
        subtitle = ctx.render(opts.get("subtitle") or "{day}, {date}")
        footer = opts.get("footer", "Generated by agentmailkit, locally.")
        text = body or ""
        for bad, good in {**HOUSE_STYLE, **opts.get("house_style", {})}.items():
            text = text.replace(bad, good)
        text = re.sub(r"  +", " ", text)
        tiles, cards = _markdown_to_blocks(text, p)
        if not cards:
            cards = [f'<div style="background:{p["card"]};border-radius:8px;padding:20px;'
                     f'box-shadow:0 1px 3px rgba(0,0,0,.08);font-size:14px;">(no content)</div>']
        return _shell(title, subtitle, tiles, cards, footer, p)
    return _fn


for _name in PALETTES:
    render(_name)(_themed(_name))


@render("plain")
def plain(ctx, body: str) -> str:
    """Pass the model's output through untouched."""
    return body
