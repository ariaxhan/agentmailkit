# Quickstart

Five minutes, ending with a real email.

## 1. Install and look around

```bash
pip install agentmailkit
agentmailkit list
```

The shipped jobs run immediately, need no API key, and send nothing.

```bash
agentmailkit run morning-brief --dry-run
```

You get a receipt: what each source returned, which gates passed, what it would have sent.

## 2. See what your sources actually produced

Set `"model": "echo"` on a job and run it. Echo returns the assembled prompt, so you see the real material verbatim, for free.

This is the single most useful debugging habit in the tool. Most disappointing digests are a source problem, not a model problem, and this tells you which in two seconds.

## 3. Make it yours

An email is two files.

`jobs/my-brief.json`:

```json
{
  "id": "my-brief",
  "schedule": "0 7 * * *",
  "prompt": "my-brief.md",
  "model": "echo",
  "sources": ["papers=arxiv:cs.AI#5", "weather=weather:YOUR_CITY"],
  "gates": ["nonempty"],
  "render": "warm",
  "delivery": "stdout",
  "subject": "My Brief - {date}",
  "dedup": true
}
```

`jobs/prompts/my-brief.md`:

```markdown
Write my brief for {date} ({day}).

Everything below is real. Cite it verbatim, invent nothing.

## Papers
{papers}

## Weather
{weather}

Lead with the most interesting thing. Under 400 words. Markdown only.
```

Run it:

```bash
agentmailkit run my-brief --dry-run
```

Each source is `alias=name:arg`; the prompt uses `{alias}`. Browse [all sources](sources.md).

## 4. Add a real model

```json
"model": "claude_cli:sonnet"
```

Uses your existing Claude Code login, no API key. Or `anthropic:claude-sonnet-5` / `openai:gpt-5` with the matching key in your environment. See [models](models.md).

## 5. See it rendered

```json
"delivery": "file"
```

Writes the finished HTML to `out/`. Open it in a browser. The theme owns all markup, so this is exactly what will arrive.

## 6. Send it

Add your address and a delivery backend:

```json
"delivery": "gmail",
"to": "you@example.com"
```

```bash
pip install agentmailkit[gmail]
agentmailkit run my-brief --dry-run    # always dry-run first
agentmailkit run my-brief
```

Gmail and SMTP setup: [delivery](delivery.md).

## 7. Schedule it

```bash
agentmailkit schedule cron     # or launchd, systemd, github, cloudflare
```

Prints the config; you install it. See [scheduling](scheduling.md).

---

## Next

- Turn on [dedup](dedup.md) so tomorrow is not a reprint of today
- Pick a [theme](themes.md), or override its colours
- Add a [taper piece](taper.md)
- Write a [plugin](plugins.md) for a source that does not exist yet
