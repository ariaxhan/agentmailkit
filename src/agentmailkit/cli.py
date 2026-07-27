"""agentmailkit CLI.

    agentmailkit init                     # copy the shipped example jobs into ./jobs to edit
    agentmailkit list                     # show configured jobs
    agentmailkit run <job> [--dry-run]    # run one job (dry-run = build+preview, never send)
    agentmailkit quickstart [--out DIR]   # render every job to a local HTML gallery; never sends
    agentmailkit plugins                  # show registered plugins
    agentmailkit schedule <backend>       # emit scheduler config (launchd|cron|systemd|github|cloudflare)
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import shutil
import sys
from pathlib import Path

from . import __version__, plugins
from . import config as _config
from .bundled import bundled_jobs_dir
from .runner import run as run_job
from .spec import load_jobs


def _jobs(cfg):
    """The user's jobs, falling back to the shipped examples when they have none.

    Returns `(jobs, cfg)`: the config comes back too because falling back has to move
    `prompts_dir` alongside `jobs_dir`, or every bundled job would resolve its prompt
    against the user's empty local tree and render an empty email. `root`/`out_dir` are
    deliberately left pointing at the user's directory, so a fallback run still reads
    their local data and writes output where they are standing.
    """
    jobs = load_jobs(cfg.jobs_dir)
    if jobs:
        return jobs, cfg
    fallback = bundled_jobs_dir()
    if not fallback:
        return {}, cfg
    return load_jobs(fallback), dataclasses.replace(
        cfg, jobs_dir=fallback, prompts_dir=fallback / "prompts")


_BUNDLED_NOTE = ("(showing the {n} example jobs agentmailkit ships with, because {d} is empty. "
                 "Run `agentmailkit init` to copy them here and edit them.)")


def cmd_init(args, cfg):
    """Copy the shipped example jobs into the working directory so they can be edited."""
    src = bundled_jobs_dir()
    if not src:
        print("ERROR: no bundled example jobs found in this install", file=sys.stderr)
        return 2
    dest = Path(args.dest).expanduser() if args.dest else Path(cfg.jobs_dir)
    dest.mkdir(parents=True, exist_ok=True)
    copied, skipped = [], []
    for path in sorted(src.rglob("*")):
        if path.is_dir():
            continue
        target = dest / path.relative_to(src)
        # Never clobber the user's own edits; init is safe to re-run.
        if target.exists():
            skipped.append(str(target.relative_to(dest)))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append(str(target.relative_to(dest)))
    print(json.dumps({"jobs_dir": str(dest), "copied": copied, "skipped": skipped}, indent=2))
    if copied:
        print(f"\nCopied {len(copied)} file(s) into {dest}. Next: "
              f"`agentmailkit run morning-brief --dry-run`", file=sys.stderr)
    if skipped:
        print(f"Left {len(skipped)} existing file(s) untouched.", file=sys.stderr)
    return 0


def cmd_list(args, cfg):
    jobs, jcfg = _jobs(cfg)
    if not jobs:
        print(f"(no jobs found in {cfg.jobs_dir})")
        return 0
    for j in jobs.values():
        flag = "" if j.status == "active" else f" [{j.status}]"
        print(f"{j.id:24s} {j.schedule or '(no schedule)':16s} -> {j.delivery}{flag}")
    if jcfg.jobs_dir != cfg.jobs_dir:
        print("\n" + _BUNDLED_NOTE.format(n=len(jobs), d=cfg.jobs_dir), file=sys.stderr)
    return 0


def cmd_run(args, cfg):
    jobs, cfg = _jobs(cfg)
    job = jobs.get(args.job)
    if not job:
        print(f"ERROR: no job {args.job!r}; have: {', '.join(jobs) or '(none)'}", file=sys.stderr)
        return 2
    receipt = run_job(job, cfg, dry_run=args.dry_run)
    print(json.dumps(receipt, indent=2, default=str))
    return 0


def cmd_quickstart(args, cfg):
    jobs, cfg = _jobs(cfg)
    if not jobs:
        print(f"(no jobs found in {cfg.jobs_dir}; nothing to render)")
        return 0
    from .quickstart import build_gallery
    out = Path(args.out) if args.out else None
    receipt = build_gallery(cfg, jobs, out_dir=out, model=args.model)
    print(json.dumps(receipt, indent=2, default=str))
    if receipt["rendered"]:
        print(f"\nOpen {receipt['index']} to see {len(receipt['rendered'])} sample emails. "
              f"Nothing was sent.", file=sys.stderr)
    return 0


def cmd_plugins(args, cfg):
    plugins.load_builtins()
    for kind in ("source", "model", "gate", "delivery", "render", "post"):
        print(f"{kind:9s}: {', '.join(plugins.registered(kind)) or '(none)'}")
    return 0


def cmd_schedule(args, cfg):
    plugins.load_builtins()
    from .schedulers import builtin as sched
    jobs, cfg = _jobs(cfg)
    text = sched.emit(args.backend, jobs.values(), cfg)
    print(text)
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="agentmailkit", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"agentmailkit {__version__}")
    p.add_argument("-C", "--config", help="path to agentmailkit.json (else auto-discovered)")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="copy the shipped example jobs into ./jobs to edit")
    i.add_argument("--dest", help="where to copy them (default: <jobs_dir>, normally ./jobs)")
    sub.add_parser("list", help="list configured jobs")
    r = sub.add_parser("run", help="run one job")
    r.add_argument("job")
    r.add_argument("--dry-run", action="store_true", help="build + preview; never send")
    q = sub.add_parser("quickstart", help="render every job to a local HTML gallery (never sends)")
    q.add_argument("--out", help="gallery output dir (default: <out_dir>/quickstart)")
    q.add_argument("--model", help="model backend to render with (default: echo, no keys/network)")
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
    handler = {"init": cmd_init, "list": cmd_list, "run": cmd_run, "quickstart": cmd_quickstart,
               "plugins": cmd_plugins, "schedule": cmd_schedule}[args.cmd]
    return handler(args, cfg)


if __name__ == "__main__":
    raise SystemExit(main())
