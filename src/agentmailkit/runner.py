"""The pipeline. One function, no per-email branches.

    gather sources -> render prompt -> generate -> gate -> deliver -> post

Every step resolves plugins by the names in the job spec, so the engine never
grows a special case: new behaviour is a new plugin, not a new `if`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from . import plugins
from .spec import Context, Job


def _load_prompt(ctx: Context) -> str:
    """A job's `prompt` is either a filename under prompts_dir or inline text."""
    ref = ctx.job.prompt
    candidate = Path(ctx.config.prompts_dir) / ref
    text = candidate.read_text(encoding="utf-8") if candidate.is_file() else ref
    # Inject gathered source blocks as {source_name} placeholders, plus a default
    # {sources} concatenation for prompts that don't name each block explicitly.
    for name, block in ctx.blocks.items():
        text = text.replace("{" + name + "}", block)
    text = text.replace("{sources}", "\n\n".join(
        f"## {n}\n{b}" for n, b in ctx.blocks.items()))
    return ctx.render(text)


def run(job: Job, config: Any, dry_run: bool = False) -> Dict[str, Any]:
    plugins.load_builtins()
    ctx = Context.build(job, config, dry_run=dry_run)
    receipt: Dict[str, Any] = {"job": job.id, "date": ctx.date, "dry_run": dry_run, "steps": []}

    # 1. sources -> text blocks, keyed by alias so same-type sources never collide.
    #    ref syntax: "alias=plugin:arg" (alias optional; defaults to the plugin name).
    for ref in job.sources:
        alias, sep, rest = ref.partition("=")
        if not sep:
            alias, rest = None, ref
        name, arg = plugins.split_ref(rest)
        key = alias or name
        block = plugins.get("source", name)(ctx, arg)
        ctx.blocks[key] = block or ""
        receipt["steps"].append({"source": ref, "alias": key, "chars": len(ctx.blocks[key])})

    # 2. render prompt
    prompt = _load_prompt(ctx)
    receipt["prompt_chars"] = len(prompt)

    # 3. generate (model backend; honors dry_run internally)
    model_name, model_arg = plugins.split_ref(job.model or config.default_model)
    body = plugins.get("model", model_name)(ctx, prompt) if not dry_run \
        else plugins.get("model", model_name)(ctx, prompt)
    receipt["body_chars"] = len(body or "")

    # 4. gates (raise plugins.GateFailure to reject before delivery)
    for ref in job.gates:
        gname, garg = plugins.split_ref(ref)
        plugins.get("gate", gname)(ctx, body)
        receipt["steps"].append({"gate": ref, "passed": True})

    # 5. deliver
    subject = ctx.render(job.subject) or f"{job.id} - {ctx.date}"
    to = job.to or config.default_to
    if dry_run:
        receipt["delivery"] = {"backend": job.delivery, "to": to, "subject": subject, "sent": False, "reason": "dry-run"}
    else:
        result = plugins.get("delivery", job.delivery)(ctx, subject, body, to)
        receipt["delivery"] = {"backend": job.delivery, "to": to, "subject": subject, "sent": True, "result": result}

    # 6. post-hooks (only after a real send)
    for ref in job.post:
        if dry_run:
            receipt["steps"].append({"post": ref, "skipped": "dry-run"})
            continue
        pname, parg = plugins.split_ref(ref)
        plugins.get("post", pname)(ctx, body)
        receipt["steps"].append({"post": ref, "ran": True})

    return receipt
