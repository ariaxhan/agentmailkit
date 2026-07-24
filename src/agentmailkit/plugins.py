"""Plugin registry - the extension seam.

Four plugin kinds, one uniform pattern each. Register with a decorator, resolve by
name at run time. Built-ins live in the sibling packages (models/, sources/,
delivery/, gates/); third parties register the same way via the
``agentmailkit.plugins`` entry-point group, so a new backend never touches the core.

Interfaces
----------
source   fn(ctx, arg) -> str        # returns a text block injected into the prompt
model    fn(ctx, prompt) -> str     # returns generated body (respects ctx.dry_run)
gate     fn(ctx, body) -> None      # raise GateFailure to reject; return to pass
delivery fn(ctx, subject, body)     # sends; returns a small dict receipt
post     fn(ctx, body) -> None      # side effect after successful delivery
"""
from __future__ import annotations

from typing import Callable, Dict

_REGISTRIES: Dict[str, Dict[str, Callable]] = {
    "source": {}, "model": {}, "gate": {}, "delivery": {}, "post": {}, "render": {},
}


class GateFailure(Exception):
    """Raised by a gate plugin to reject a generated body before delivery."""


def _register(kind: str):
    def deco(name: str):
        def inner(fn: Callable) -> Callable:
            _REGISTRIES[kind][name] = fn
            return fn
        return inner
    return deco


source = _register("source")
model = _register("model")
gate = _register("gate")
delivery = _register("delivery")
post = _register("post")
render = _register("render")


def get(kind: str, name: str) -> Callable:
    try:
        return _REGISTRIES[kind][name]
    except KeyError:
        avail = ", ".join(sorted(_REGISTRIES[kind])) or "(none)"
        raise KeyError(f"no {kind} plugin named {name!r}; registered: {avail}")


def split_ref(ref: str):
    """'name:arg' -> ('name', 'arg'); 'name' -> ('name', '')."""
    name, _, arg = ref.partition(":")
    return name, arg


_LOADED = False


def load_builtins() -> None:
    """Import built-in plugin modules so their decorators run. Idempotent."""
    global _LOADED
    if _LOADED:
        return
    from .models import builtin as _m       # noqa: F401
    from .sources import builtin as _s      # noqa: F401
    from .delivery import builtin as _d     # noqa: F401
    from .gates import builtin as _g        # noqa: F401
    # Optional/incremental built-ins: present -> registered, absent -> skipped.
    # This is the same drop-in contract third-party plugins use, applied to our own.
    for mod in ("sources.hf", "sources.arxiv", "sources.rss", "sources.history",
                "sources.weather", "posts.taper", "themes.builtin"):
        try:
            __import__(f"{__package__}.{mod}")
        except ImportError:
            pass
    # Third-party plugins via entry points (optional; ignored if importlib.metadata absent).
    try:
        from importlib.metadata import entry_points
        eps = entry_points()
        group = eps.select(group="agentmailkit.plugins") if hasattr(eps, "select") else eps.get("agentmailkit.plugins", [])
        for ep in group:
            ep.load()
    except Exception:
        pass
    _LOADED = True


def registered(kind: str):
    return sorted(_REGISTRIES[kind])
