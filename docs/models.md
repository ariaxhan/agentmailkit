# Models

Set per job as `backend` or `backend:model`.

| Backend | Needs | Notes |
|---|---|---|
| `echo` | nothing | Returns the assembled prompt. Free, offline, and the fastest way to see exactly what your sources produced |
| `claude_cli` | the `claude` CLI | Uses your existing Claude Code auth. No API key |
| `anthropic` | `pip install agentmailkit[anthropic]` + `ANTHROPIC_API_KEY` | |
| `openai` | `pip install agentmailkit[openai]` + `OPENAI_API_KEY` | |

```json
"model": "claude_cli:sonnet"
"model": "anthropic:claude-sonnet-5"
"model": "openai:gpt-5"
"model": "echo"
```

## Use echo first

Before spending a token, run with `echo` and read the output. It shows you precisely what each source returned and how the prompt assembled. Most disappointing digests are a source problem, not a model problem, and this is how you tell the difference in two seconds.

## Model backends are text-only, deliberately

A model backend's entire job is prompt in, text out. The `claude_cli` backend therefore denies every tool, disables slash commands, and uses strict MCP config.

This is not paranoia. During development, an unrestricted headless run had file-write tools available and used them: it wrote its draft into the working tree instead of printing it, and the stray file was committed before anyone noticed.

A pipeline that promises determinism is only honest if the model is **structurally unable to act**, not merely asked not to. Disabling permission checks grants capability; it does not restrict it.

If you add your own model backend, hold it to the same rule.

## Local models

Anything with an OpenAI-compatible endpoint works via the `openai` backend by pointing `OPENAI_BASE_URL` at it (Ollama, LM Studio, llama.cpp). With a local model nothing leaves your machine at all, including the prompt.
