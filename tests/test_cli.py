"""CLI smoke tests: the commands a new user runs first must exit clean and print sense."""
from __future__ import annotations

import json
import os

from agentmailkit import cli


def _run(argv, cfg, monkeypatch):
    # Route config discovery to the test config regardless of cwd.
    monkeypatch.setattr("agentmailkit.config.load", lambda start=None: cfg)
    return cli.main(argv)


def test_plugins_lists_builtins(capsys, tmp_cfg, monkeypatch):
    assert _run(["plugins"], tmp_cfg, monkeypatch) == 0
    out = capsys.readouterr().out
    for kind in ("source", "model", "gate", "delivery", "render", "post"):
        assert kind in out
    assert "echo" in out and "warm" in out and "taper" in out


def test_list_with_no_local_jobs_shows_the_bundled_set(capsys, tmp_cfg, monkeypatch):
    """An empty working directory is the new-user case, and it must not look broken."""
    assert _run(["list"], tmp_cfg, monkeypatch) == 0
    captured = capsys.readouterr()
    assert "morning-brief" in captured.out
    # The user is told these are examples and how to make them theirs.
    assert "agentmailkit init" in captured.err


def test_list_reports_empty_only_when_nothing_ships(capsys, tmp_cfg, monkeypatch):
    """The old dead-end message is still correct when there is genuinely nothing to show."""
    monkeypatch.setattr("agentmailkit.cli.bundled_jobs_dir", lambda: None)
    assert _run(["list"], tmp_cfg, monkeypatch) == 0
    assert "no jobs found" in capsys.readouterr().out


def test_run_unknown_job_errors(tmp_cfg, monkeypatch):
    assert _run(["run", "does-not-exist"], tmp_cfg, monkeypatch) == 2


def test_quickstart_with_nothing_available_is_clean(capsys, tmp_cfg, monkeypatch):
    monkeypatch.setattr("agentmailkit.cli.bundled_jobs_dir", lambda: None)
    assert _run(["quickstart"], tmp_cfg, monkeypatch) == 0
    assert "nothing to render" in capsys.readouterr().out


def test_quickstart_renders_and_reports_not_sent(capsys, tmp_cfg, monkeypatch, tmp_path):
    # Drop one local job into the config's jobs dir so quickstart has something to render.
    (tmp_cfg.jobs_dir / "prompts").mkdir(parents=True, exist_ok=True)
    (tmp_cfg.jobs_dir / "probe.json").write_text(json.dumps({
        "id": "probe", "prompt": "Digest {date}\n\n{readme}", "model": "echo",
        "sources": ["readme=file:README.md"], "gates": ["nonempty"],
        "render": "warm", "delivery": "stdout", "subject": "Probe {date}",
    }), encoding="utf-8")
    assert _run(["quickstart", "--out", str(tmp_path / "gal")], tmp_cfg, monkeypatch) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["sent"] is False
    assert len(receipt["rendered"]) == 1
    assert os.path.isfile(receipt["index"])
