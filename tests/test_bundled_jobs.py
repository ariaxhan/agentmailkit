"""The shipped example jobs must be reachable from a bare install.

This locks the failure found just before the first PyPI upload: the wheel carried only
`src/agentmailkit`, so `pip install agentmailkit` produced an install with zero jobs, and
both README first-commands (`agentmailkit run morning-brief --dry-run`, `quickstart`)
printed "no jobs found" and exited. Nothing in the suite noticed, because every existing
test ran from the repo checkout where `./jobs` happens to exist.
"""
from __future__ import annotations

import json
from pathlib import Path

from agentmailkit import config as _config
from agentmailkit.bundled import bundled_jobs_dir
from agentmailkit.cli import _jobs, main
from agentmailkit.spec import load_jobs

# The jobs the README and CLAUDE.md both promise are there.
DOCUMENTED = {"morning-brief", "research-digest", "curiosity", "repo-pulse", "daily-brief"}


def test_bundled_jobs_are_locatable():
    d = bundled_jobs_dir()
    assert d is not None, "no bundled jobs dir resolved"
    assert DOCUMENTED <= set(load_jobs(d)), "a documented example job is missing"


def test_every_bundled_job_has_its_prompt():
    """A job whose prompt file did not ship renders an empty email, which is worse than failing."""
    d = bundled_jobs_dir()
    for job in load_jobs(d).values():
        # Inline prompts carry their own text; only file refs need a shipped file.
        if job.prompt.endswith(".md"):
            assert (d / "prompts" / job.prompt).is_file(), f"{job.id}: missing {job.prompt}"


def test_empty_working_dir_falls_back_to_bundled(tmp_path, monkeypatch):
    """The new-user case: an empty directory must still see jobs."""
    monkeypatch.chdir(tmp_path)
    cfg = _config.Config(root=tmp_path, jobs_dir=tmp_path / "jobs")
    jobs, jcfg = _jobs(cfg)
    assert DOCUMENTED <= set(jobs)
    # Prompts must move with the jobs, otherwise every prompt resolves to nothing.
    assert jcfg.prompts_dir == jcfg.jobs_dir / "prompts"
    # The user's own root/out_dir must NOT be redirected into the package.
    assert Path(jcfg.root) == tmp_path


def test_user_jobs_win_over_bundled(tmp_path):
    """The fallback is a fallback: one local job and the bundled set disappears."""
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    (jobs_dir / "mine.json").write_text(
        json.dumps({"id": "mine", "prompt": "hello", "delivery": "stdout"}), encoding="utf-8")
    cfg = _config.Config(root=tmp_path, jobs_dir=jobs_dir)
    jobs, jcfg = _jobs(cfg)
    assert set(jobs) == {"mine"}
    assert jcfg.jobs_dir == jobs_dir


def test_init_copies_jobs_and_never_clobbers(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "--dest", str(tmp_path / "jobs")]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert DOCUMENTED <= set(load_jobs(Path(receipt["jobs_dir"])))

    # Re-running must be safe: edits survive, nothing is overwritten.
    edited = tmp_path / "jobs" / "morning-brief.json"
    edited.write_text(json.dumps({"id": "morning-brief", "prompt": "edited"}), encoding="utf-8")
    assert main(["init", "--dest", str(tmp_path / "jobs")]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["copied"] == [], "init overwrote files on a re-run"
    assert "morning-brief.json" in second["skipped"]
    assert json.loads(edited.read_text())["prompt"] == "edited"
