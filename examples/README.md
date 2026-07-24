# Examples

The `jobs/` directory at the repo root is already a working example set: it runs
immediately with no API key, because those jobs use the `echo` model and print to
stdout instead of sending.

```bash
agentmailkit run daily-brief --dry-run
agentmailkit run research-digest --dry-run    # hits the live HF + arXiv APIs
```

This directory holds the next step: what those jobs look like once you point them at
a real model and a real inbox.

## Files

| File | What it shows |
|---|---|
| `production-digest.json` | The research digest wired for real use: a real model, Gmail delivery, quality gates, and a taper piece |
| `agentmailkit.gmail.json` | Config for sending through Gmail |
| `agentmailkit.smtp.json` | Config for sending through any SMTP server |

## Using one

Copy the job into `jobs/`, copy the config to the root, then dry-run before you ever
let it send:

```bash
cp examples/production-digest.json jobs/
cp examples/agentmailkit.gmail.json agentmailkit.json
agentmailkit run production-digest --dry-run
```

`--dry-run` builds everything and reports what it *would* send without sending it.
Always use it first on a job that has a real delivery backend attached.

## Going from example to yours

Three edits cover most cases:

1. **Point the sources at your data.** `file:`, `glob:`, `recent:` and `shell:` read
   your machine. `shell:` in particular means you are never blocked: any command's
   output can become prompt context.
2. **Rewrite the prompt.** It is a plain markdown file. Source aliases arrive as
   `{alias}` placeholders.
3. **Set the schedule** as a cron expression, then emit host config with
   `agentmailkit schedule cron` (or `launchd`, `systemd`, `github`, `cloudflare`).
