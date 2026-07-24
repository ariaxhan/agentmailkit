"""The pipeline. One function, no per-email branches.

    gather sources -> render prompt -> generate -> gate -> deliver -> post

Every step resolves plugins by the names in the job spec, so the engine never
grows a special case: new behaviour is a new plugin, not a new `if`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from . import ledger, plugins
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
    # Themes declared in config become usable without touching any code.
    try:
        from .themes import builtin as _themes
        _themes.register_from_config(config)
    except ImportError:
        pass
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

    # 1b. dedup: strip items already delivered BEFORE the model ever sees them. Asking a
    #     model to "not repeat yesterday" is unreliable, and summarizing items you intend
    #     to discard is paid waste. See ledger.py for the full contract.
    dd = ledger.resolve(job, config)
    book = presented = None
    if dd:
        book = ledger.Ledger(dd["path"], dd["window_days"])
        seen = book.seen(job.id)
        presented, dropped = [], 0
        for alias, blk in list(ctx.blocks.items()):
            filtered, keys, n = ledger.filter_block(blk, seen)
            ctx.blocks[alias] = filtered
            presented += keys
            dropped += n
        receipt["dedup"] = {"seen_in_window": len(seen), "dropped": dropped, "fresh": len(presented)}

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

    # 4b. render: the model wrote the words, the theme owns the markup. Deterministic
    #     presentation is the whole point - same structure every run, only content moves.
    if job.render:
        rname, _ = plugins.split_ref(job.render)
        body = plugins.get("render", rname)(ctx, body)
        receipt["rendered"] = {"theme": job.render, "chars": len(body)}

    # 5. deliver
    subject = ctx.render(job.subject) or f"{job.id} - {ctx.date}"
    to = job.to or config.default_to
    if dry_run:
        receipt["delivery"] = {"backend": job.delivery, "to": to, "subject": subject, "sent": False, "reason": "dry-run"}
    else:
        result = plugins.get("delivery", job.delivery)(ctx, subject, body, to)
        receipt["delivery"] = {"backend": job.delivery, "to": to, "subject": subject, "sent": True, "result": result}
        # Record ONLY after a confirmed send. A failed delivery must not burn a day of
        # content by marking unseen items as seen.
        if book is not None:
            keys = ledger.keys_in(body) if dd["record"] == "delivered" else presented
            receipt["dedup"]["recorded"] = book.record(job.id, keys, ctx.date)

    # 6. post-hooks (only after a real send)
    for ref in job.post:
        if dry_run:
            receipt["steps"].append({"post": ref, "skipped": "dry-run"})
            continue
        pname, parg = plugins.split_ref(ref)
        plugins.get("post", pname)(ctx, body)
        receipt["steps"].append({"post": ref, "ran": True})

    return receipt
