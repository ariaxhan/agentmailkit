"""Locating the example jobs agentmailkit ships with.

A fresh `pip install agentmailkit` creates no `jobs/` directory, so with nothing else in
place the README's own first command (`agentmailkit run morning-brief --dry-run`) and
`agentmailkit quickstart` both do nothing at all: the tool looks in `./jobs`, finds an
empty room, and says so. That is the worst possible first impression for a package whose
whole pitch is batteries-included defaults, so the five shipped jobs travel with the wheel.

The repo-root `jobs/` tree stays the single source of truth. The build copies it into the
wheel at `agentmailkit/_bundled/jobs` (see `[tool.hatch.build.targets.wheel.force-include]`
in pyproject.toml) rather than the repo carrying a second copy, so the two can never drift
apart: there is exactly one set of job files in git.

Resolution order, first hit wins:

1. the packaged copy, `agentmailkit/_bundled/jobs` - a normal installed wheel
2. the repo-root `jobs/`, walking up from this file - an editable install or a checkout

These are read-only fallbacks used only when the user has no jobs of their own. The moment
`./jobs` contains anything, the user's jobs win outright and the bundled set is ignored;
`agentmailkit init` copies them into the working directory to be edited.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

_PACKAGED = Path(__file__).resolve().parent / "_bundled" / "jobs"
# src/agentmailkit/bundled.py -> parents[2] is the repo root in a source checkout.
_CHECKOUT = Path(__file__).resolve().parents[2] / "jobs"


def _has_jobs(d: Path) -> bool:
    return d.is_dir() and any(d.glob("*.json"))


def bundled_jobs_dir() -> Optional[Path]:
    """The directory holding the shipped example jobs, or None if unavailable."""
    for candidate in (_PACKAGED, _CHECKOUT):
        if _has_jobs(candidate):
            return candidate
    return None
