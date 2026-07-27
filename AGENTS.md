# agentmailkit: setup guide for coding agents

You are setting up **agentmailkit** for the person you are working with. It sends scheduled, LLM-written email digests that run on their machine, read their own files, and send from their own inbox.

Work through this top to bottom. It should take a few minutes and end with a real email in their inbox.

---

## 0. What this tool is, so you explain it correctly

A fixed pipeline, not an autonomous agent:

```
gather sources -> render prompt -> generate -> gate -> render theme -> deliver -> post
```

One JSON job spec plus one markdown prompt equals one email. The model writes only the words; the engine controls everything else, so the same job produces the same shaped email every run.

Do not describe it as an AI agent that manages their inbox. It does not read incoming mail, decide things, or take actions.

---

## 1. Ask these questions first

**Do not skip this.** Defaults produce a generic email nobody opens. Ask, then build to the answers. Ask them together, in one message, and keep it short.

1. **What should the email contain?** Push for specifics. "AI news" is weak; "new Hugging Face models for video generation, plus arXiv papers mentioning agents" is a good job. If they are unsure, offer the shipped jobs as starting points (see step 4).
2. **When should it arrive?** A time and days. Convert to cron.
3. **Where should it send?** Gmail, or another provider over SMTP. Get the recipient address.
4. **Which model?** If they use Claude Code already, `claude_cli:sonnet` needs no API key and is the easiest. Otherwise an Anthropic or OpenAI key, or a local model.
5. **Should it read anything on their machine?** Notes, a repo, a folder, the output of a command. This is the feature no cloud scheduler has, so raise it explicitly. Many people do not realise it is possible.

If they want something not covered by a built-in source, check [docs/sources.md](docs/sources.md), then [docs/plugins.md](docs/plugins.md). Writing a source is about thirty lines.

---

## 2. Install

```bash
pip install agentmailkit          # core, standard library only
pip install agentmailkit[gmail]   # add if delivering via Gmail
pip install agentmailkit[all]     # add if using the Anthropic or OpenAI backends
```

Verify:

```bash
agentmailkit --version
agentmailkit plugins              # lists every registered source, model, gate, delivery, theme
agentmailkit quickstart           # renders all five example jobs to a local HTML gallery, sends nothing
```

`quickstart` is the fastest way to show them what the output actually looks like before you
have configured anything. It forces `echo` as the model and `file` as delivery in code, so it
needs no keys and structurally cannot email anyone.

---

## 3. Create the config

Write `agentmailkit.json` in the project directory:

```json
{
  "root": ".",
  "jobs_dir": "jobs",
  "out_dir": "out",
  "default_to": "THEIR_EMAIL",
  "sender": "THEIR_EMAIL",
  "default_model": "claude_cli:sonnet"
}
```

Delivery-specific settings go under `extra`. See [docs/delivery.md](docs/delivery.md) for the Gmail token and SMTP shapes.

**Never put a secret in this file.** SMTP passwords are referenced by environment variable name; API keys live in the environment. If a credential is needed, tell the human exactly what to set and let them set it.

---

## 4. Build their job

Start from the closest shipped job rather than a blank file. Run `agentmailkit init` first: it
copies all five into `./jobs` so you can edit them. It never overwrites an existing file, so it
is safe to re-run. The five are:

| Job | Sources | Good starting point for |
|---|---|---|
| `morning-brief` | weather, three labelled news feeds, on-this-day | A general daily email |
| `research-digest` | Hugging Face, arXiv | Anything research or ML |
| `curiosity` | archaeology and astronomy feeds, history | Non-work interest email |
| `repo-pulse` | git log, diffstat, TODO markers | Anything about their code |
| `daily-brief` | local files, git log | The minimal shape |

Write two files.

`jobs/<id>.json`:

```json
{
  "id": "their-brief",
  "schedule": "0 7 * * *",
  "prompt": "their-brief.md",
  "model": "claude_cli:sonnet",
  "sources": ["papers=arxiv:cs.AI#6", "weather=weather:THEIR_CITY"],
  "gates": ["nonempty", "min_length:400"],
  "render": "warm",
  "delivery": "gmail",
  "subject": "Their Brief - {date}",
  "dedup": { "window_days": 30 },
  "status": "active"
}
```

`jobs/prompts/their-brief.md`:

```markdown
Write the brief for {date} ({day}).

Everything below came from live APIs. Figures, titles and links are real. Cite them
verbatim and never invent one. If it is not in the material below, it does not go in
the email.

## Papers
{papers}

## Weather
{weather}

---
Write as markdown. Lead with the single most interesting thing. Under 400 words.
Markdown only, never HTML: the theme owns all formatting.
```

Rules that matter:

- Each source is `alias=name:arg`, and the prompt references it as `{alias}`.
- Ask for **markdown, not HTML**, whenever `render` is set. The theme owns markup.
- Turn `dedup` on for anything with a feed, or day two repeats day one.
- Full field reference: [docs/jobs.md](docs/jobs.md).

---

## 5. Verify before it can send

```bash
agentmailkit run their-brief --dry-run
```

Read the receipt and check, in this order:

1. **Sources returned real content.** Each has a `chars` count. A tiny count or a `(feed unavailable: ...)` message means fix the source before anything else.
2. **Gates passed.**
3. **The subject and recipient are right.**

To see the actual material a source produced, temporarily set `"model": "echo"` and run again. Echo returns the assembled prompt, costs nothing, and answers most "why is this email bad" questions immediately.

To see the rendered HTML without emailing anyone, set `"delivery": "file"` and open the file in `out/`.

Only when all of that looks right, do a real run:

```bash
agentmailkit run their-brief
```

Confirm with the human that it actually arrived. A receipt saying `"sent": true` means the API accepted it, which is not the same as it being in their inbox.

---

## 6. Schedule it

```bash
agentmailkit schedule cron        # or launchd, systemd, github, cloudflare
```

This prints config; it does not install anything. Show the human the output and let them install it, since it makes something run on their machine on a schedule.

If they want laptop-closed uptime, read them the tradeoff in [docs/scheduling.md](docs/scheduling.md): a cloud runner cannot see their local files.

---

## 7. Hand off

Tell them, briefly:

- Which files you created, and that an email is two files: a job and a prompt.
- How to change the wording: edit the prompt, no code.
- How to preview safely: `--dry-run`, and `echo` plus `file` delivery.
- Where the seen-ledger lives, and that deleting a line makes an item eligible again.

---

## Verify the engine itself

Before changing any core behaviour, run the test suite. It is offline and deterministic
(the `echo` model plus local sources only, no network, no inbox):

```bash
pip install -e ".[dev]"
ruff check src
pytest -q
```

The suite locks the invariants that must be true every run: a dry-run never sends, a real
run delivers a file and only a file, every gate rejects what it should, the dedup ledger
collapses arxiv versions and filters seen items, the quickstart gallery can structurally
never send, and the Taper interaction check accepts real listeners while rejecting
timer-only pieces. Anything that must hold every run belongs in a test here, not in a prompt.

`ruff check src` is the other half of the gate (`[tool.ruff]` in `pyproject.toml`): pyflakes
+ pycodestyle errors + import sorting only. Deliberately not pyupgrade/bandit/blind-except/
refurb - see the comment above `select` in `pyproject.toml` for why each is excluded.

## Reference

| Topic | Doc |
|---|---|
| All sources and their arguments | [docs/sources.md](docs/sources.md) |
| Job spec fields, prompt conventions | [docs/jobs.md](docs/jobs.md) |
| Themes, house style, the markdown subset | [docs/themes.md](docs/themes.md) |
| The dedup contract | [docs/dedup.md](docs/dedup.md) |
| Delivery backends, config, gates | [docs/delivery.md](docs/delivery.md) |
| Model backends | [docs/models.md](docs/models.md) |
| Scheduling and the cloud tradeoff | [docs/scheduling.md](docs/scheduling.md) |
| Writing a plugin | [docs/plugins.md](docs/plugins.md) |

## Things that will trip you up

- **A source returning nothing is the most common failure.** Check `chars` in the receipt before blaming the model or the prompt.
- **Not every site has an RSS feed.** `rss` reports the reason (`served HTML, not a feed`). Believe it and find the real feed URL.
- **A model asked for HTML while a theme is set** produces double markup. Ask for markdown.
- **`--dry-run` never sends,** so it is always safe. There is no reason to skip it.
- **Do not route sending through a model.** The delivery backends call APIs directly, on purpose. If you are tempted to have an LLM "send the email", do not.
