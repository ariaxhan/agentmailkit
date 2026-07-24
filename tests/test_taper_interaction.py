"""The 07-24 lesson, made permanent: interaction is a hard rule of a Taper piece, and it
is enforced by a check in code, not requested in a prompt. This test guards that check so
a regression that loosens it fails here instead of shipping a static, un-interactive piece.
"""
from __future__ import annotations

from agentmailkit.posts.taper import INTERACTION_RE


INTERACTIVE = [
    "<section><script>el.addEventListener('mousemove', f)</script></section>",
    "<section><script>document.addEventListener('click', g)</script></section>",
    "<div onmousemove='warm()'></div>",
    "<a onclick='reveal()'>word</a>",
    "<style>.w:hover{color:red}</style>",
    "<canvas><script>c.addEventListener('pointerdown', p)</script></canvas>",
    "<div><script>x.addEventListener('touchstart', t)</script></div>",
]

STATIC = [
    "<section><script>setInterval(tick, 100)</script></section>",  # timer alone is a film
    "<section><p>just some words, no listener</p></section>",
    "<div><script>let t = setTimeout(done, 2000)</script></div>",
]


def test_interaction_regex_accepts_real_listeners():
    for html in INTERACTIVE:
        assert INTERACTION_RE.search(html), f"should count as interactive: {html!r}"


def test_interaction_regex_rejects_timer_only_pieces():
    for html in STATIC:
        assert not INTERACTION_RE.search(html), f"should NOT count as interactive: {html!r}"
