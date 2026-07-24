"""The deterministic pipeline: sources -> prompt -> gate -> render -> deliver.

These lock the baseline the tool promises: a dry-run never sends, a real local run
writes a file and only a file, and the source material actually reaches the prompt.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from agentmailkit.plugins import GateFailure
from agentmailkit.runner import run as run_job


def test_dry_run_never_sends(tmp_cfg, local_job):
    receipt = run_job(local_job, tmp_cfg, dry_run=True)
    assert receipt["dry_run"] is True
    assert receipt["delivery"]["sent"] is False
    assert receipt["delivery"]["reason"] == "dry-run"
    # No file may be written on a dry-run.
    assert not list(Path(tmp_cfg.out_dir).glob("*")) if Path(tmp_cfg.out_dir).exists() else True


def test_source_content_reaches_prompt(tmp_cfg, local_job):
    receipt = run_job(local_job, tmp_cfg, dry_run=True)
    src = next(s for s in receipt["steps"] if s.get("alias") == "readme")
    assert src["chars"] > 0
    # echo returns the assembled prompt as the body, so the real file content is in it.
    assert receipt["body_chars"] >= src["chars"]


def test_gates_pass_for_good_body(tmp_cfg, local_job):
    receipt = run_job(local_job, tmp_cfg, dry_run=True)
    gates = [s for s in receipt["steps"] if "gate" in s]
    assert gates and all(g["passed"] for g in gates)


def test_min_length_gate_rejects_short_body(tmp_cfg, local_job):
    job = dataclasses.replace(local_job, prompt="hi", sources=[], gates=["min_length:500"])
    with pytest.raises(GateFailure):
        run_job(job, tmp_cfg, dry_run=True)


def test_real_local_run_writes_a_file_and_only_a_file(tmp_cfg, local_job):
    receipt = run_job(local_job, tmp_cfg, dry_run=False)
    assert receipt["delivery"]["backend"] == "file"
    assert receipt["delivery"]["sent"] is True
    path = Path(receipt["delivery"]["result"]["path"])
    assert path.is_file()
    assert path.read_text(encoding="utf-8").strip()  # rendered HTML landed


def test_theme_renders_html(tmp_cfg, local_job):
    receipt = run_job(local_job, tmp_cfg, dry_run=True)
    assert receipt["rendered"]["theme"] == "warm"
    assert receipt["rendered"]["chars"] > receipt["body_chars"]  # markup was added
