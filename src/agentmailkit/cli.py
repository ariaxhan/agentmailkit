"""agentmailkit CLI.

    agentmailkit list                     # show configured jobs
    agentmailkit run <job> [--dry-run]    # run one job (dry-run = build+preview, never send)
    agentmailkit plugins                  # show registered plugins
    agentmailkit schedule <backend>       # emit scheduler config (launchd|cron|systemd|github|cloudflare)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, config as _config, plugins
from .spec import load_jobs
from .runner import run as run_job


def _jobs(cfg):
    return load_jobs(cfg.jobs_dir)


def cmd_list(args, cfg):
    jobs = _jobs(cfg)
    if not jobs:
        print(f"(no jobs found in {cfg.jobs_dir})")
        return 0
    for j in jobs.values():
        flag = "" if j.status == "active" else f" [{j.status}]"
        print(f"{j.id:24s} {j.schedule or '(no schedule)':16s} -> {j.delivery}{flag}")
    return 0


def cmd_run(args, cfg):
    jobs = _jobs(cfg)
    job = jobs.get(args.job)
    if not job:
        print(f"ERROR: no job {args.job!r}; have: {', '.join(jobs) or '(none)'}", file=sys.stderr)
        return 2
    receipt = run_job(job, cfg, dry_run=args.dry_run)
    print(json.dumps(receipt, indent=2, default=str))
    return 0


def cmd_plugins(args, cfg):
    plugins.load_builtins()
    for kind in ("source", "model", "gate", "delivery", "post"):
        print(f"{kind:9s}: {', '.join(plugins.registered(kind)) or '(none)'}")
    return 0


def cmd_schedule(args, cfg):
    plugins.load_builtins()
    from .schedulers import builtin as sched
    text = sched.emit(args.backend, _jobs(cfg).values(), cfg)
    print(text)
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="agentmailkit", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"agentmailkit {__version__}")
    p.add_argument("-C", "--config", help="path to agentmailkit.json (else auto-discovered)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list configured jobs")
    r = sub.add_parser("run", help="run one job")
    r.add_argument("job")
    r.add_argument("--dry-run", action="store_true", help="build + preview; never send")
    sub.add_parser("plugins", help="list registered plugins")
    s = sub.add_parser("schedule", help="emit scheduler config")
    s.add_argument("backend", choices=["launchd", "cron", "systemd", "github", "cloudflare"])
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    start = Path(args.config).parent if args.config else None
    if args.config:
        import os
        os.environ["AGENTMAILKIT_CONFIG"] = args.config
    cfg = _config.load(start)
    handler = {"list": cmd_list, "run": cmd_run, "plugins": cmd_plugins, "schedule": cmd_schedule}[args.cmd]
    return handler(args, cfg)


if __name__ == "__main__":
    raise SystemExit(main())
