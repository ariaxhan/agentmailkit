# Writing a plugin

The engine has no per-email branches. Everything type-specific is a named plugin resolved from the job spec, so adding behaviour never means editing the core.

Five kinds, one decorator each.

| Kind | Signature | Returns |
|---|---|---|
| `source` | `fn(ctx, arg) -> str` | Text injected into the prompt |
| `model` | `fn(ctx, prompt) -> str` | The generated body |
| `gate` | `fn(ctx, body) -> None` | Nothing; raise `GateFailure` to reject |
| `render` | `fn(ctx, body) -> str` | Finished HTML |
| `delivery` | `fn(ctx, subject, body, to) -> dict` | A small receipt |
| `post` | `fn(ctx, body) -> None` | Nothing; runs only after a confirmed send |

## A source, end to end

```python
from agentmailkit.plugins import source

@source("weather")
def weather(ctx, arg):
    return fetch_forecast(arg)      # any string; lands in the prompt as {weather}
```

Use it:

```json
"sources": ["forecast=weather:Brooklyn"]
```

and reference `{forecast}` in the prompt.

## The context object

| Attribute | What it is |
|---|---|
| `ctx.job` | The `Job` (id, options, sources, ...) |
| `ctx.config` | Loaded config (`root`, `out_dir`, `extra`, ...) |
| `ctx.date`, `ctx.day` | `2026-07-23`, `Thursday` |
| `ctx.dry_run` | True when previewing |
| `ctx.blocks` | Source blocks gathered so far, keyed by alias |
| `ctx.render(text)` | Expands `{date}`, `{day}`, `{id}` |

Per-job settings belong in `options`, namespaced by plugin name:

```json
"options": { "weather": { "units": "imperial" } }
```

```python
units = (ctx.job.options or {}).get("weather", {}).get("units", "metric")
```

## Three rules

**Fail open.** A source that raises kills a scheduled run. Return a short notice instead:

```python
except Exception:
    return f"(weather unavailable for {arg})"
```

**Say why you failed.** `(feed unavailable)` hides breakage for weeks; `(feed unavailable: served HTML, not a feed)` gets fixed in a minute. A convincing silence is worse than an error.

**Be deterministic.** Fetch real values and hand them over. Do not ask a model for a fact you could look up: a figure that arrives pre-fetched cannot be hallucinated. This is the reason `hf`, `arxiv` and `weather` exist as code rather than as prompt instructions.

## Resolving paths

Local sources resolve against `ctx.config.root` unless the argument is absolute:

```python
from pathlib import Path
p = Path(arg).expanduser()
if not p.is_absolute():
    p = Path(ctx.config.root) / p
```

## Shipping it

Drop the module in `src/agentmailkit/sources/` and it registers on import. To ship a plugin in your own package, expose it on the `agentmailkit.plugins` entry-point group:

```toml
[project.entry-points."agentmailkit.plugins"]
myplugin = "mypackage.plugins"
```

It is then discovered automatically and the core never learns its name.

## Before you write one

`shell` already covers a surprising amount. Any command's stdout becomes prompt context:

```json
"sources": ["disk=shell:df -h /", "unread=shell:notmuch count tag:unread"]
```

Write a real plugin when you want the parsing, formatting, error reporting or dedup keys to be consistent, or when you want to share it.
