"""Built-in source plugins - the local-data seam.

Each is fn(ctx, arg) -> str returning a text block injected into the prompt as
`{source_name}` (or into `{sources}`). THIS is the layer the cloud assistants
cannot replicate: it reads your machine directly. All paths resolve against
`config.root`, never outside it unless the arg is absolute.
"""
from __future__ import annotations

import glob as _glob
import os
import subprocess
from pathlib import Path
from ..plugins import source


def _resolve(ctx, arg: str) -> Path:
    p = Path(arg).expanduser()
    return p if p.is_absolute() else Path(ctx.config.root) / p


@source("file")
def file_source(ctx, arg: str) -> str:
    """Inline the contents of a file. arg = path (relative to root or absolute)."""
    path = _resolve(ctx, arg)
    if not path.is_file():
        return f"(no file at {arg})"
    return path.read_text(encoding="utf-8", errors="replace")


@source("glob")
def glob_source(ctx, arg: str) -> str:
    """List files matching a glob, newest first, with sizes. arg = glob pattern."""
    base = Path(ctx.config.root)
    matches = sorted(base.glob(arg), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    if not matches:
        return f"(no matches for {arg})"
    return "\n".join(f"- {p.relative_to(base)} ({p.stat().st_size}b)" for p in matches[:50])


@source("recent")
def recent_source(ctx, arg: str) -> str:
    """Headers + first lines of files modified in the last N days.
    arg = 'DIR' or 'DIR:DAYS' (default 7 days, 12 lines each)."""
    spec, _, days = arg.partition(":")
    days = int(days) if days else 7
    base = _resolve(ctx, spec)
    import time
    cutoff = time.time() - days * 86400
    out = []
    for p in sorted(base.rglob("*.md")) if base.is_dir() else []:
        if p.stat().st_mtime < cutoff:
            continue
        head = "".join(p.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)[:12])
        out.append(f"### {p.name}\n{head}")
    return "\n\n".join(out) or f"(nothing in {spec} newer than {days}d)"


@source("shell")
def shell_source(ctx, arg: str) -> str:
    """Run a shell command from `config.root`, return stdout. arg = command.
    Powerful and local - the escape hatch for any source not yet a plugin."""
    out = subprocess.run(arg, shell=True, cwd=str(ctx.config.root),
                         capture_output=True, text=True, timeout=120)
    return (out.stdout or out.stderr).strip()
