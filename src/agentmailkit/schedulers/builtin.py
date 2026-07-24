"""Scheduler adapters - the portability seam.

One `emit(backend, jobs, cfg)` turns each job's cron `schedule` into config for the
host you actually run on: macOS launchd, Linux cron/systemd, a GitHub Actions
workflow, or a Cloudflare Worker cron trigger. Same jobs, any host - this is what
frees agentmailkit from being "a pile of launchd plists."
"""
from __future__ import annotations

from typing import Iterable


def _cron_parts(expr: str):
    parts = (expr or "0 7 * * *").split()
    while len(parts) < 5:
        parts.append("*")
    return parts[:5]  # min hour dom mon dow


def emit(backend: str, jobs: Iterable, cfg) -> str:
    jobs = [j for j in jobs if getattr(j, "status", "active") == "active" and j.schedule]
    return _EMITTERS[backend](jobs, cfg)


def _launchd(jobs, cfg):
    out = []
    for j in jobs:
        m, h, *_ = _cron_parts(j.schedule)
        out.append(f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- save as ~/Library/LaunchAgents/com.agentmailkit.{j.id}.plist -->
<plist version="1.0"><dict>
  <key>Label</key><string>com.agentmailkit.{j.id}</string>
  <key>ProgramArguments</key><array>
    <string>agentmailkit</string><string>run</string><string>{j.id}</string>
  </array>
  <key>StartCalendarInterval</key><dict>
    <key>Hour</key><integer>{h if h != '*' else 0}</integer>
    <key>Minute</key><integer>{m if m != '*' else 0}</integer>
  </dict>
</dict></plist>""")
    return "\n\n".join(out)


def _cron(jobs, cfg):
    lines = ["# agentmailkit - add to `crontab -e`"]
    for j in jobs:
        lines.append(f"{j.schedule}  agentmailkit run {j.id}")
    return "\n".join(lines)


def _systemd(jobs, cfg):
    out = []
    for j in jobs:
        m, h, *_ = _cron_parts(j.schedule)
        oncal = f"*-*-* {h if h!='*' else '*'}:{m if m!='*' else '00'}:00"
        out.append(f"""# {j.id}.timer + {j.id}.service (~/.config/systemd/user/)
[Unit]
Description=agentmailkit {j.id}
[Timer]
OnCalendar={oncal}
[Install]
WantedBy=timers.target
# --- {j.id}.service ---
[Service]
Type=oneshot
ExecStart=agentmailkit run {j.id}""")
    return "\n\n".join(out)


def _github(jobs, cfg):
    crons = "\n".join(f"    - cron: '{j.schedule}'   # {j.id}" for j in jobs)
    steps = "\n".join(
        f"      - run: agentmailkit run {j.id}" for j in jobs)
    return f""".github/workflows/agentmailkit.yml
name: agentmailkit
on:
  schedule:
{crons}
  workflow_dispatch:
jobs:
  digest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install agentmailkit[all]
{steps}"""


def _cloudflare(jobs, cfg):
    crons = "\n".join(f'  "{j.schedule}",   # {j.id}' for j in jobs)
    return f"""# wrangler.toml - Cloudflare Worker cron (laptop-closed uptime).
# The Worker invokes agentmailkit over HTTP or via a Python Worker; jobs read
# data you sync to R2/KV instead of local disk (the cloud tradeoff).
name = "agentmailkit"
[triggers]
crons = [
{crons}
]"""


_EMITTERS = {
    "launchd": _launchd, "cron": _cron, "systemd": _systemd,
    "github": _github, "cloudflare": _cloudflare,
}
