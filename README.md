# agentmailkit

**Scheduled, LLM-written email digests that run on your machine, read your own files, and send from your own inbox.**

Declare a job: a schedule, a prompt, some data sources, a delivery address. agentmailkit runs it on a cron, feeds your local data to an LLM, and emails you the result. A morning news brief, a research digest, a "what changed in my repos" summary, a content-idea bank. Each one is a JSON file plus a prompt, not a bespoke script.

```bash
pip install agentmailkit
agentmailkit run daily-brief --dry-run    # builds and previews, never sends
```

MIT licensed. No account, no vendor, no cloud required.

---

## The point is deterministic stability

agentmailkit is **not** an autonomous agent. It does not decide what to do, wander your filesystem, or take actions you did not ask for.

It is a **fixed pipeline**:

```
gather sources  ->  render prompt  ->  generate  ->  gate  ->  deliver  ->  post
```

The same job spec produces the same shaped output every single day. The LLM writes the *words*; the engine controls everything else. If you want an AI coworker that acts on its own, use an agent framework. If you want a digest that arrives correctly at 7am for the next two years, use this.

## Why not just use ChatGPT / Claude / Gemini schedulers

Every major assistant ships a scheduler now (ChatGPT **Tasks**, Claude Code **Routines**, Gemini **Scheduled Actions**, Copilot **Scheduled Prompts**). They share two hard limits, because they all execute in the vendor's cloud:

1. **They cannot read the files on your computer.** ChatGPT blocks file access inside a task; the others only reach vendor-siloed data (a connected repo, Google Workspace, an M365 tenant). None can read `~/notes/` or a local SQLite database.
2. **They cannot send real email from your inbox.** They deliver into their own app surfaces. There is no arbitrary Gmail or SMTP send.

agentmailkit runs where your data already is. Nothing gets uploaded except the prompt you choose to send to your model, and with a local model, not even that.

**The honest comparison.** Against cloud assistants that gap is structural. Against local-first OSS agents ([OpenClaw](https://github.com/steipete/openclaw), [Hermes](https://www.firecrawl.dev/blog/hermes-agent)) it is not: they also run locally, read files, and can email. The difference there is shape. Those are broad autonomous agents you configure down to a task. agentmailkit does one job, declaratively, with no autonomy to supervise.

| | agentmailkit | Cloud schedulers | Local agents |
|---|---|---|---|
| Runs where | Your machine | Vendor cloud | Your machine |
| Reads local files | Yes | No | Yes |
| Sends from your inbox | Yes | No | Yes |
| Deterministic output shape | Yes | No | No |
| Autonomy to supervise | None | n/a | Yes |
| Cost | OSS + your tokens | Paid plan | OSS + tokens |

---

## Adding an email is two files

**1. The job** (`jobs/daily-brief.json`):

```json
{
  "id": "daily-brief",
  "schedule": "30 7 * * *",
  "prompt": "daily-brief.md",
  "model": "claude_cli:sonnet",
  "sources": ["notes=recent:~/notes:3", "commits=shell:git log --oneline -10"],
  "gates": ["nonempty", "min_length:400"],
  "delivery": "gmail",
  "subject": "Daily brief - {date}"
}
```

**2. The prompt** (`jobs/prompts/daily-brief.md`), referencing each source by its alias:

```markdown
Write my brief for {date} ({day}).

## What I wrote recently
{notes}

## Recent commits
{commits}

Keep it under 400 words. Lead with what matters most.
```

That is the whole extension model. No engine changes, ever.

## Plugins

Everything type-specific is a named plugin resolved from the job spec.

| Kind | Built in | Contract |
|---|---|---|
| **source** | `file`, `glob`, `recent`, `shell`, `hf`, `arxiv` | `fn(ctx, arg) -> str` |
| **model** | `echo`, `claude_cli`, `anthropic`, `openai` | `fn(ctx, prompt) -> str` |
| **gate** | `nonempty`, `min_length`, `no_placeholder` | `fn(ctx, body)`, raise to reject |
| **delivery** | `stdout`, `file`, `smtp`, `gmail` | `fn(ctx, subject, body, to) -> dict` |
| **post** | `taper` | `fn(ctx, body)`, runs after a successful send |
| **scheduler** | `launchd`, `cron`, `systemd`, `github`, `cloudflare` | emits host config |

`shell` is the escape hatch: any local command's output becomes prompt context, so you are never blocked waiting for a plugin to exist.

### Research sources are deterministic on purpose

The single most common failure of an LLM research digest is inventing a plausible paper title or a confident download count. `hf` and `arxiv` remove the opportunity: they query the Hugging Face Hub and arXiv APIs directly and hand the model **real** ids, figures, authors and links to cite verbatim. No model sits between the API and the fact.

```json
"sources": ["models=hf:full", "papers=arxiv:cs.AI:6", "learning=arxiv:q=retrieval augmented generation:5"]
```

`hf` takes `full`, `pulse` or `brief`. `arxiv` takes a category (`cs.AI`), an optional count (`cs.LG:5`), or a free-text search (`q=your terms:5`). Both fail open: if an API is down you get a short notice, never a broken run.

### Taper: computational poetry as a companion piece

`taper` is an optional post plugin. After the email is safely sent, it generates a tiny self-contained interactive HTML artifact responding to the same material: one file, no external assets, meaning carried by form and algorithm instead of prose. Where the digest says what happened, the piece is an abstract reply to it.

```json
"post": ["taper"],
"options": { "taper": { "out_dir": "pieces", "max_bytes": 4096 } }
```

It runs only after delivery and fails open by design. A strange generative artifact must never be the reason a digest does not arrive.

**Writing your own** takes one decorator:

```python
from agentmailkit.plugins import source

@source("weather")
def weather(ctx, arg):
    return fetch_forecast(arg)     # any string; lands in the prompt as {weather}
```

Ship it in your own package under the `agentmailkit.plugins` entry-point group and it registers automatically. The core never learns your plugin's name.

## Configuration

One `agentmailkit.json`, no hardcoded paths, so the same install runs against any project:

```json
{
  "root": ".",
  "jobs_dir": "jobs",
  "default_to": "you@example.com",
  "sender": "you@example.com",
  "default_model": "claude_cli:sonnet"
}
```

Every field is overridable by `AGENTMAILKIT_*` environment variables. Secrets are referenced, never stored: OAuth tokens and API keys come from your keychain or env.

## Scheduling, local or cloud

```bash
agentmailkit schedule cron        # or launchd, systemd, github, cloudflare
```

Emits ready-to-use host config from the same job specs. Local is the default. When you want laptop-closed uptime, the `cloudflare` or `github` emitters run the same jobs in CI or a Worker; you trade local file access for always-on.

## Commands

```bash
agentmailkit list                       # configured jobs
agentmailkit run <job> [--dry-run]      # run one job
agentmailkit plugins                    # what is registered
agentmailkit schedule <backend>         # emit scheduler config
```

## Install

```bash
pip install agentmailkit               # core, standard library only
pip install agentmailkit[gmail]        # + Gmail delivery
pip install agentmailkit[all]          # + every model and delivery backend
```

The core has **zero required dependencies**. Backends pull their own libraries only when enabled.

## Try it now

The `jobs/` directory ships as a working example set that runs with no API key and sends nothing:

```bash
agentmailkit run daily-brief --dry-run       # reads local files + git log
agentmailkit run research-digest --dry-run   # hits the live HF + arXiv APIs
```

`examples/` has the same jobs wired for real use: a real model, Gmail or SMTP delivery, and a taper piece.

## Status

Alpha (0.1.0). The engine, plugin system, sources, gates, delivery backends, scheduler emitters and dry-run all work and are exercised end to end.

**Roadmap**, in order:

- A deterministic HTML theme, so digests are beautifully formatted without ever asking the model to write markup
- Deduplication and a seen-ledger, so a daily digest never repeats itself
- `agentmailkit quickstart`, to generate a working sample email set from your real data on first run
- An agent-facing setup guide, so a coding agent can install and extend this without a human

## Contributing

Issues and pull requests welcome. The design rule that governs review: **behaviour is configuration, not code.** If a change adds an `if` to the engine for one email's sake, it probably wants to be a plugin instead.

## License

MIT. See [LICENSE](LICENSE).
