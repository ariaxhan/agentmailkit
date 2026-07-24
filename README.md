# agentmailkit

**Scheduled, LLM-written email digests that run on your machine, read your own files, and send from your own inbox.**

### → [See real emails it produces](https://ariaxhan.github.io/agentmailkit/)

Live samples, generated end to end. Nothing hand-written. Start there, it explains this faster than the README can.

```bash
pip install agentmailkit
agentmailkit run morning-brief --dry-run
```

MIT licensed. No account, no vendor, no cloud required.

---

## What it is

An email is **two files**: a JSON job and a markdown prompt.

```json
{
  "id": "morning-brief",
  "schedule": "0 7 * * *",
  "sources": ["papers=arxiv:cs.AI#6", "weather=weather:Brooklyn"],
  "render": "warm",
  "delivery": "gmail",
  "dedup": true
}
```

The engine runs one fixed pipeline and never grows a special case:

```
gather sources -> render prompt -> generate -> gate -> theme -> deliver -> post
```

## Why not the built-in schedulers

ChatGPT **Tasks**, Claude **Routines**, Gemini **Scheduled Actions** and Copilot all execute in the vendor's cloud, which costs them two things:

- **They cannot read the files on your computer.** Not `~/notes`, not a local database, not your git working tree.
- **They cannot send real email from your inbox.** Output stays inside their app.

agentmailkit runs where your data already is. Nothing is uploaded except the prompt you choose to send to a model, and with a local model, not even that.

**And it is deterministic.** It is not an autonomous agent: it does not decide things, wander your filesystem, or act unrequested. The model writes the words; the engine owns everything else, so the same job produces the same shaped email every run. Local OSS agents can also read files and send mail, but they are broad autonomous systems you configure down to a task. This does one job, predictably, for years.

Full comparison including the honest counter-case: [docs/comparison.md](docs/comparison.md).

## For agents

**Hand your coding agent this link and it will set the whole thing up, asking you the right questions as it goes:**

```
https://github.com/ariaxhan/agentmailkit/blob/main/AGENTS.md
```

[AGENTS.md](AGENTS.md) is a complete setup runbook: what to ask you, how to install, how to build your first job, how to verify before anything can send, and how to schedule it. `CLAUDE.md` is a symlink to the same file, so they can never drift apart.

## What ships

| Job | Pulls | Interesting because |
|---|---|---|
| `morning-brief` | weather, three news outlets, on-this-day | Outlets stay labelled, so the model can contrast their framing |
| `curiosity` | archaeology and astronomy feeds, history | No work content at all, on purpose |
| `research-digest` | Hugging Face, arXiv | Real ids, counts and links the model cannot invent |
| `repo-pulse` | git log, diffstat, TODO markers | Reads your working tree, which no cloud scheduler can |
| `daily-brief` | local files, git log | The minimal shape to copy |

**Ten sources built in:** `file`, `glob`, `recent`, `shell`, `hf`, `arxiv`, `rss`, `news`, `history`, `weather`. Anything with a feed or an API joins them in about thirty lines.

**Ideas worth stealing:** your city's council agendas, security advisories for your exact dependency list, exchange rates, a friend's blog, release notes for the tools you use, tide tables, ISS pass times over your house.

**Nothing repeats.** A seen-ledger strips already-sent items before the model ever sees them, so day two is not a reprint of day one.

## Docs

| | |
|---|---|
| [Quickstart](docs/quickstart.md) | Five minutes to a real email |
| [Setup guide for agents](AGENTS.md) | Hand this to your coding agent |
| [Sources](docs/sources.md) | All ten, with arguments and examples |
| [Jobs and prompts](docs/jobs.md) | Every job field, prompt conventions |
| [Themes](docs/themes.md) | The renderer, palettes, enforced house style |
| [Dedup](docs/dedup.md) | The seen-ledger contract |
| [Delivery and config](docs/delivery.md) | Gmail, SMTP, gates, configuration |
| [Models](docs/models.md) | Backends, and why they are text-only |
| [Scheduling](docs/scheduling.md) | cron, launchd, systemd, CI, and the cloud tradeoff |
| [Taper pieces](docs/taper.md) | The optional computational-poetry companion |
| [Plugins](docs/plugins.md) | Write a source in about thirty lines |
| [Comparison](docs/comparison.md) | Versus cloud schedulers and local agents, honestly |

## Install

```bash
pip install agentmailkit            # core, standard library only
pip install agentmailkit[gmail]     # + Gmail delivery
pip install agentmailkit[all]       # + Anthropic and OpenAI backends
```

The core has **zero required dependencies**. Backends pull their own libraries only when enabled.

## Status

Alpha (0.1.0). Engine, plugins, dedup, themes, delivery and scheduler emitters all work and are exercised end to end against live APIs.

Next: a `quickstart` command that generates a working sample set from your own data on first run.

## Contributing

Issues and pull requests welcome. The rule that governs review: **behaviour is configuration, not code.** If a change adds an `if` to the engine for one email's sake, it probably wants to be a plugin.

## License

MIT. See [LICENSE](LICENSE).
