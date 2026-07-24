"""Built-in gates. `gate(name)` registers fn(ctx, body) -> None; raise GateFailure to reject.

Gates run after generation, before delivery - the place to stop a bad/empty/hallucinated
digest from ever reaching the inbox. Reference in a job as `"min_length:400"`.
"""
from __future__ import annotations

from ..plugins import GateFailure, gate


@gate("nonempty")
def nonempty(ctx, body: str) -> None:
    if not body or not body.strip():
        raise GateFailure("generated body is empty")


@gate("min_length")
def min_length(ctx, body: str) -> None:
    """arg = minimum character count (default 200)."""
    n = 200
    for ref in ctx.job.gates:
        if ref.startswith("min_length:"):
            n = int(ref.split(":", 1)[1])
    if len(body.strip()) < n:
        raise GateFailure(f"body {len(body.strip())} chars < required {n}")


@gate("no_placeholder")
def no_placeholder(ctx, body: str) -> None:
    """Catch unrendered template markers ({date}, TODO, lorem) leaking into a send."""
    lowered = body.lower()
    for marker in ("{date}", "{sources}", "lorem ipsum", "todo:"):
        if marker in lowered:
            raise GateFailure(f"unrendered/placeholder marker present: {marker!r}")
