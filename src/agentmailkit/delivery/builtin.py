"""Built-in delivery backends. `delivery(name)` registers fn(ctx, subject, body, to) -> dict.

`stdout`/`file` need nothing. `smtp` uses the stdlib. `gmail` needs
`pip install agentmailkit[gmail]` + an OAuth token. Delivery is where "from your own
inbox" happens - the thing cloud schedulers can't do.
"""
from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from ..plugins import delivery


def _is_html(body: str) -> bool:
    b = body.lstrip()[:200].lower()
    return b.startswith("<") and ("<html" in b or "<h1" in b or "<h2" in b or "<p" in b or "<div" in b)


@delivery("stdout")
def to_stdout(ctx, subject, body, to) -> dict:
    print(f"--- {subject} -> {to or '(no recipient)'} ---\n{body}")
    return {"backend": "stdout"}


@delivery("file")
def to_file(ctx, subject, body, to) -> dict:
    out_dir = Path(ctx.config.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ext = "html" if _is_html(body) else "txt"
    path = out_dir / f"{ctx.date}-{ctx.job.id}.{ext}"
    path.write_text(body, encoding="utf-8")
    return {"backend": "file", "path": str(path)}


@delivery("smtp")
def via_smtp(ctx, subject, body, to) -> dict:
    """Send through any SMTP server. Config in config.extra['smtp'] =
    {host, port, user, password_env, starttls}. Password read from that env var."""
    s = ctx.config.extra.get("smtp", {})
    host, port = s.get("host", "localhost"), int(s.get("port", 587))
    msg = MIMEText(body, "html" if _is_html(body) else "plain")
    msg["Subject"], msg["From"], msg["To"] = subject, ctx.config.sender or s.get("user", ""), to
    with smtplib.SMTP(host, port, timeout=60) as srv:
        if s.get("starttls", True):
            srv.starttls()
        if s.get("user"):
            srv.login(s["user"], os.environ.get(s.get("password_env", "SMTP_PASSWORD"), ""))
        srv.send_message(msg)
    return {"backend": "smtp", "host": host}


@delivery("gmail")
def via_gmail(ctx, subject, body, to) -> dict:
    """Send via the Gmail API using a stored OAuth token (no draft intermediary).
    Token path: config.extra['gmail']['token'] or AGENTMAILKIT_GMAIL_TOKEN."""
    import base64
    import pickle
    from email.mime.text import MIMEText as _M
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    token_path = ctx.config.extra.get("gmail", {}).get("token") or os.environ.get("AGENTMAILKIT_GMAIL_TOKEN")
    if not token_path:
        raise RuntimeError("gmail delivery needs a token: set config.extra.gmail.token or AGENTMAILKIT_GMAIL_TOKEN")
    with open(os.path.expanduser(token_path), "rb") as f:
        creds = pickle.load(f)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(os.path.expanduser(token_path), "wb") as f:
            pickle.dump(creds, f)
    service = build("gmail", "v1", credentials=creds)
    msg = _M(body, "html" if _is_html(body) else "plain")
    msg["to"], msg["subject"] = to, subject
    if ctx.config.sender:
        msg["from"] = ctx.config.sender
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"backend": "gmail", "id": result.get("id"), "labels": result.get("labelIds", [])}
