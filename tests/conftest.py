"""Shared fixtures. Every test runs fully offline: the `echo` model and local sources
only, so the suite is deterministic and never touches the network or an inbox."""
from __future__ import annotations

from pathlib import Path

import pytest

from agentmailkit import plugins
from agentmailkit.config import Config
from agentmailkit.spec import Job


@pytest.fixture(autouse=True)
def _builtins():
    plugins.load_builtins()


@pytest.fixture
def tmp_cfg(tmp_path: Path) -> Config:
    """A config rooted in a throwaway dir, with a README the file source can read."""
    (tmp_path / "README.md").write_text("# sample\n\nreal local content for the digest.\n",
                                        encoding="utf-8")
    (tmp_path / "jobs").mkdir()
    return Config(root=tmp_path, jobs_dir=tmp_path / "jobs",
                  default_to="nobody@example.com", default_model="echo")


@pytest.fixture
def local_job() -> Job:
    """A job that reads only local data - no network, deterministic, safe to run for real."""
    return Job(
        id="probe",
        prompt="Digest for {date}.\n\n## Readme\n{readme}\n",
        model="echo",
        sources=["readme=file:README.md"],
        gates=["nonempty", "min_length:20"],
        render="warm",
        delivery="file",
        subject="Probe - {date}",
    )
