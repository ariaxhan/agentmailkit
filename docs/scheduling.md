# Scheduling

agentmailkit does not run a daemon. It runs once, exits, and lets your operating system decide when. That keeps it debuggable (`agentmailkit run x` is exactly what the scheduler does) and portable.

Each job carries a cron expression. Emit host config from it:

```bash
agentmailkit schedule cron        # or launchd, systemd, github, cloudflare
```

| Backend | Where it runs | Notes |
|---|---|---|
| `cron` | Linux, macOS | Paste into `crontab -e` |
| `launchd` | macOS | One plist per job for `~/Library/LaunchAgents/` |
| `systemd` | Linux | A `.timer` plus `.service` per job |
| `github` | GitHub Actions | A workflow with one cron trigger per job |
| `cloudflare` | Cloudflare Workers | `wrangler.toml` cron triggers |

## Local is the default

Local execution is the whole premise: the job reads your files and sends from your inbox. A laptop that sleeps will miss runs, which for a daily digest usually just means it arrives when you open the lid.

## Cloud is a real tradeoff, not an upgrade

`github` and `cloudflare` give you laptop-closed uptime and cost you the thing that made this worth running: **the cloud runner cannot see your local files.**

If you go that way, be deliberate:

- Jobs using only network sources (`hf`, `arxiv`, `rss`, `news`, `history`, `weather`) port cleanly.
- Jobs using `file`, `glob`, `recent` or `shell` need their data synced somewhere the runner can reach (a committed folder, R2, KV), and at that point the data has left your machine.
- Secrets move into the platform's secret store.

A reasonable split is to run local-data jobs on your machine and network-only jobs in CI, from the same job specs.

## macOS notes

Two failure modes worth knowing, both learned painfully:

- launchd log paths under `~/Documents` fail with exit 78. launchd opens those files before your script runs and has no permission there. Put launchd-level logs in `~/Library/Logs/`.
- Use an explicit interpreter path in the plist. A bare `python3` may not resolve to the one your dependencies are installed under.
