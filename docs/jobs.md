# Jobs and prompts

An email is two files: a JSON job spec and a markdown prompt. There is no third file and no code.

## The job spec

```json
{
  "id": "morning-brief",
  "schedule": "0 7 * * *",
  "prompt": "morning-brief.md",
  "model": "claude_cli:sonnet",
  "sources": ["weather=weather:Brooklyn", "papers=arxiv:cs.AI#5"],
  "gates": ["nonempty", "min_length:400"],
  "render": "warm",
  "delivery": "gmail",
  "to": "you@example.com",
  "subject": "Morning Brief - {date}",
  "post": ["taper"],
  "dedup": { "window_days": 14 },
  "options": {},
  "status": "active"
}
```

| Field | Meaning |
|---|---|
| `id` | Unique name; also the CLI argument |
| `schedule` | Cron expression, used to emit host config. agentmailkit does not run a daemon |
| `prompt` | Filename under `jobs/prompts/`, or inline prompt text |
| `model` | `backend` or `backend:model`. See [models](models.md) |
| `sources` | List of `alias=name:arg`. See [sources](sources.md) |
| `gates` | Quality checks run before delivery. A failing gate stops the send |
| `render` | Theme name, or omit to send the model's output untouched. See [themes](themes.md) |
| `delivery` | `gmail`, `smtp`, `file`, `stdout`. See [delivery](delivery.md) |
| `to` | Recipient; falls back to `default_to` in config |
| `subject` | Supports `{date}`, `{day}`, `{id}` |
| `post` | Hooks that run only after a confirmed send |
| `dedup` | `true`, or `{window_days, path, record}`. See [dedup](dedup.md) |
| `options` | Free-form per-job settings read by plugins |
| `status` | `active`, or anything else to skip it in scheduler output |

## The prompt

A plain markdown file. Each source arrives as `{alias}`; `{date}` and `{day}` are also available.

```markdown
Write the brief for {date} ({day}).

## Weather
{weather}

## Papers
{papers}

Keep it under 400 words. Markdown only.
```

Two habits that make output much better:

**Tell the model the material is real and must be cited verbatim.** Sources hand over genuine ids, figures and links. Say so explicitly, and say that anything not present in the material does not go in the email.

**Ask for markdown, never HTML.** If you use a theme, the theme owns all markup. A model writing HTML is a model that will format the email differently on a bad day.

## Where jobs live

`jobs/*.json` and `jobs/prompts/*.md` by default, configurable via `jobs_dir`. A file may hold one job object or a list of them.

```bash
agentmailkit list                       # every configured job
agentmailkit run morning-brief --dry-run
```

`--dry-run` gathers sources, builds the prompt, generates, and runs gates, then reports what it *would* send without sending it. Use it on any job wired to a real inbox.
