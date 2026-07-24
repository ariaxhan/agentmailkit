# How this compares

Two different comparisons, because agentmailkit competes with two very different things.

---

## Against cloud assistant schedulers

ChatGPT **Tasks**, Claude Code **Routines**, Gemini **Scheduled Actions**, Microsoft Copilot **Scheduled Prompts**.

| | agentmailkit | Cloud schedulers |
|---|---|---|
| Runs where | Your machine | Vendor cloud |
| Reads your local files | Yes | No |
| Sends from your inbox | Yes (Gmail, SMTP) | No, output stays in their app |
| Custom pipeline | Yes, config-driven | A prompt |
| Deterministic output shape | Yes | No |
| Task limits | Your cron | Typically 3 to 15 active tasks, hourly minimum |
| Cost | OSS plus your tokens | Paid plan |

The first two rows are **structural**, not a feature gap someone forgot to build. These products execute in the vendor's cloud, so there is no path to `~/notes`, a local SQLite file, or your git working tree, and no credential to send mail as you. ChatGPT blocks file access inside a task outright; Gemini and Copilot reach only vendor-siloed data (Workspace, an M365 tenant); Claude Routines see connected repos rather than your disk.

**When they are the better choice:** you want a daily summary in three sentences of setup, with no install, no key, and no machine that has to be awake. That is a real advantage and this tool does not match it.

---

## Against local-first OSS agents

[OpenClaw](https://github.com/steipete/openclaw), [Hermes](https://www.firecrawl.dev/blog/hermes-agent), and similar self-hosted agents.

Here the local-files advantage **disappears**. They also run on your machine, read your files, and can send email. Anyone claiming otherwise is selling something.

The difference is shape.

| | agentmailkit | Local autonomous agents |
|---|---|---|
| What it is | A digest engine | An autonomous agent |
| Decides what to do | Never | Yes, continuously |
| Output shape | Fixed by config | Varies by run |
| Surface to supervise | None | Tool use, actions, a heartbeat loop |
| Setup | A JSON file and a prompt | Configure a general agent down to a task |

agentmailkit is deliberately **not** an agent. It does not triage your inbox, draft replies, decide what deserves attention, or take actions you did not specify. It gathers named sources, renders a prompt, generates text, checks it, and sends it. Every run, the same way.

That constraint is the product. An autonomous agent is more capable and more interesting; a fixed pipeline is the thing you can leave running for two years without wondering what it did this morning.

**When they are the better choice:** you want something that acts on your behalf, handles incoming mail, or chains tool use across a task. Use those. They are good, and this is not trying to be them.

---

## The one-line version

> The simplest way to get a genuinely useful email every morning, built from your own data, that looks the same every time and never repeats itself.

Everything in that sentence is a deliberate constraint, and each one is why something else is not a better fit.

## What is not claimed

- Not zero-setup. The cloud schedulers beat it on time-to-first-email.
- Not always-on for free. A sleeping laptop misses runs unless you move to CI or a Worker, which costs you local file access.
- Not free-free. You pay for model tokens unless you run a local model.
- Not more capable than an autonomous agent. It is narrower on purpose.
