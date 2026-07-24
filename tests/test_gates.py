"""Gates are the last thing between a bad body and an inbox. Each one is checked directly."""
from __future__ import annotations

import pytest

from agentmailkit.plugins import GateFailure, get
from agentmailkit.spec import Context, Job


def _ctx(gates):
    job = Job(id="g", prompt="p", gates=gates)
    return Context(job=job, config=None, date="2026-07-24", day="Friday")


def test_nonempty_rejects_blank():
    with pytest.raises(GateFailure):
        get("gate", "nonempty")(_ctx(["nonempty"]), "   \n  ")


def test_nonempty_passes_real_body():
    get("gate", "nonempty")(_ctx(["nonempty"]), "a real body")


def test_min_length_reads_its_arg_from_the_job():
    ctx = _ctx(["min_length:100"])
    with pytest.raises(GateFailure):
        get("gate", "min_length")(ctx, "too short")
    get("gate", "min_length")(ctx, "x" * 100)


@pytest.mark.parametrize("marker", ["{date}", "{sources}", "lorem ipsum", "TODO:"])
def test_no_placeholder_catches_unrendered_markers(marker):
    with pytest.raises(GateFailure):
        get("gate", "no_placeholder")(_ctx(["no_placeholder"]), f"body with {marker} leaked in")


def test_no_placeholder_passes_clean_body():
    get("gate", "no_placeholder")(_ctx(["no_placeholder"]), "a clean rendered digest, no markers")
