# Delivery and configuration

## Backends

| Backend | Needs | Use for |
|---|---|---|
| `stdout` | nothing | Development |
| `file` | nothing | Previewing rendered HTML, archiving |
| `smtp` | an SMTP account | Any mail provider |
| `gmail` | `pip install agentmailkit[gmail]` + an OAuth token | Gmail, sent directly with no draft step |

Delivery is where "from your own inbox" happens, which is the thing cloud schedulers structurally cannot do.

> **Never route a send through a model.** The `gmail` backend calls the API directly. An earlier system in this lineage asked a model to "send" via a tool that only supported drafts; it silently created drafts for days while the log reported success. Sending is a deterministic action and belongs in code.

## Configuration

One `agentmailkit.json`, discovered by walking up from the working directory. No hardcoded paths, so the same install runs against any project.

```json
{
  "root": ".",
  "jobs_dir": "jobs",
  "out_dir": "out",
  "default_to": "you@example.com",
  "sender": "you@example.com",
  "default_model": "claude_cli:sonnet",
  "extra": {}
}
```

| Key | Meaning |
|---|---|
| `root` | Base directory for local sources and relative paths |
| `jobs_dir` | Where job specs live (`prompts/` sits inside it) |
| `out_dir` | Where the `file` backend and taper pieces write |
| `default_to` | Recipient when a job does not set one |
| `sender` | From address |
| `default_model` | Model when a job does not set one |
| `extra` | Backend-specific settings |

Every field is overridable by environment: `AGENTMAILKIT_ROOT`, `AGENTMAILKIT_DEFAULT_TO`, and so on. Point at a specific file with `-C path/to/agentmailkit.json` or `AGENTMAILKIT_CONFIG`.

## Gmail

```json
"extra": { "gmail": { "token": "~/.config/agentmailkit/gmail_token.pickle" } }
```

A pickled `google.oauth2.credentials.Credentials` with the `gmail.send` scope. It refreshes itself when expired. Also settable via `AGENTMAILKIT_GMAIL_TOKEN`.

## SMTP

```json
"extra": { "smtp": {
  "host": "smtp.fastmail.com",
  "port": 587,
  "user": "you@example.com",
  "password_env": "SMTP_PASSWORD",
  "starttls": true
} }
```

The password is read from the named environment variable. Secrets are referenced, never stored in config.

## Gates

Gates run after generation and before delivery. A failing gate stops the send, which is the point: a bad digest should never reach your inbox.

| Gate | Checks |
|---|---|
| `nonempty` | The model returned something |
| `min_length:400` | At least N characters |
| `no_placeholder` | No unrendered `{markers}`, `TODO:` or lorem text leaked through |

## Post hooks

Run only after a confirmed send.

| Hook | Effect |
|---|---|
| `taper` | Generates a computational-poetry companion piece. See [taper](taper.md) |
