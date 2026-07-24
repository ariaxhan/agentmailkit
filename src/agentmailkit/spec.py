"""Job + run-context data model.

A *job* is a fully declarative description of one scheduled email. It carries no
code: every type-specific behaviour is named (a source plugin, a gate, a delivery
backend) and resolved at run time. Adding a new email = add one JSON block + a
prompt file. That is the whole point of agentmailkit.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Job:
    id: str
    prompt: str                              # filename under <jobs_dir>/prompts/ or inline text
    model: str = "echo"                      # "backend:model", e.g. "claude_cli:sonnet"
    schedule: str = ""                       # cron expression (scheduler-agnostic)
    sources: List[str] = field(default_factory=list)   # source-plugin refs, "name" or "name:arg"
    gates: List[str] = field(default_factory=list)     # gate-plugin refs
    delivery: str = "stdout"                 # delivery-backend ref
    subject: str = ""                        # may contain {date}/{day}/{id} placeholders
    to: str = ""                             # recipient; falls back to config.default_to
    post: List[str] = field(default_factory=list)      # post-hook refs (commit, learn, ...)
    options: Dict[str, Any] = field(default_factory=dict)  # free-form per-job knobs
    status: str = "active"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Job":
        known = {f: d[f] for f in cls.__dataclass_fields__ if f in d}
        return cls(**known)


@dataclass
class Context:
    """Everything a plugin might need, assembled once per run."""
    job: Job
    config: Any                              # agentmailkit.config.Config
    date: str
    day: str
    dry_run: bool = False
    blocks: Dict[str, str] = field(default_factory=dict)   # source name -> rendered text

    @classmethod
    def build(cls, job: Job, config: Any, dry_run: bool = False, now: Optional[_dt.date] = None) -> "Context":
        now = now or _dt.date.today()
        return cls(job=job, config=config, date=now.isoformat(),
                   day=now.strftime("%A"), dry_run=dry_run)

    def render(self, text: str) -> str:
        """Expand {date}/{day}/{id} placeholders in subjects, filenames, prompts."""
        return (text or "").replace("{date}", self.date).replace("{day}", self.day).replace("{id}", self.job.id)


def load_jobs(jobs_dir: Path) -> Dict[str, Job]:
    """Load every <jobs_dir>/*.json job spec. A file may hold one job object or a list."""
    jobs: Dict[str, Job] = {}
    jobs_dir = Path(jobs_dir)
    if not jobs_dir.is_dir():
        return jobs
    for path in sorted(jobs_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw if isinstance(raw, list) else [raw]
        for item in items:
            job = Job.from_dict(item)
            jobs[job.id] = job
    return jobs
