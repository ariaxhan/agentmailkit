"""Built-in model backends. `model(name)` registers fn(ctx, prompt) -> str.

Pick per job as `"backend:model"`, e.g. `"claude_cli:sonnet"`, `"anthropic:claude-sonnet-5"`,
`"openai:gpt-5"`. `echo` is the zero-dependency default used for dry-runs and tests.
"""
from __future__ import annotations

import os
import subprocess

from ..plugins import model


@model("echo")
def echo(ctx, prompt: str) -> str:
    """Return the assembled prompt verbatim. No API, no cost - proves the pipeline."""
    return prompt


# Every tool the CLI could otherwise reach. A model backend's ONLY job is to turn a
# prompt into text; if it can also touch your filesystem or the network it is an agent,
# and agentmailkit is explicitly not that. Learned the hard way: an unrestricted run
# decided to Write its draft into jobs/ instead of printing it.
_DENIED_TOOLS = [
    "Bash", "Edit", "Write", "NotebookEdit", "Read", "Glob", "Grep",
    "WebFetch", "WebSearch", "Task", "TodoWrite",
]


@model("claude_cli")
def claude_cli(ctx, prompt: str) -> str:
    """Generate via the local `claude` CLI (uses your existing Claude Code auth).

    Model tier comes from the job's `model` arg (`claude_cli:sonnet`). The CLI binary
    is configurable via AGENTMAILKIT_CLAUDE_BIN.

    Runs text-only: every tool is explicitly denied, slash commands and project MCP
    config are disabled, and settings come from the user scope so a project's hooks
    cannot inject themselves into a scheduled run. The model returns words. That is all
    it is permitted to do.
    """
    tier = ctx.job.model.partition(":")[2] or "sonnet"
    binary = os.environ.get("AGENTMAILKIT_CLAUDE_BIN", "claude")
    cmd = [binary, "--model", tier, "-p", prompt,
           "--dangerously-skip-permissions", "--setting-sources", "user",
           "--strict-mcp-config", "--disable-slash-commands",
           "--disallowed-tools", *_DENIED_TOOLS]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=int(ctx.job.options.get("timeout", 900)))
    if out.returncode != 0:
        raise RuntimeError(f"claude_cli failed ({out.returncode}): {out.stderr[-500:]}")
    return out.stdout.strip()


@model("anthropic")
def anthropic_api(ctx, prompt: str) -> str:
    """Generate via the Anthropic API. Requires `pip install agentmailkit[anthropic]`
    and ANTHROPIC_API_KEY. Model id is the arg, e.g. `anthropic:claude-sonnet-5`."""
    from anthropic import Anthropic  # lazy: only when this backend is used
    model_id = ctx.job.model.partition(":")[2] or "claude-sonnet-5"
    client = Anthropic()
    msg = client.messages.create(
        model=model_id,
        max_tokens=int(ctx.job.options.get("max_tokens", 4096)),
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()


@model("openai")
def openai_api(ctx, prompt: str) -> str:
    """Generate via the OpenAI API. Requires `pip install agentmailkit[openai]` and
    OPENAI_API_KEY. Model id is the arg, e.g. `openai:gpt-5`."""
    from openai import OpenAI  # lazy
    model_id = ctx.job.model.partition(":")[2] or "gpt-5"
    client = OpenAI()
    resp = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
    )
    return (resp.choices[0].message.content or "").strip()
