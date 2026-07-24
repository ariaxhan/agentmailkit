# Taper pieces

An optional companion artifact. After the email is safely sent, agentmailkit can generate a tiny self-contained interactive HTML fragment responding to the same material: one file, no external assets, meaning carried by form and algorithm rather than prose.

Where the digest says what happened, the piece is an abstract reply to it.

> The Taper form comes from **[taper.badquar.to](https://taper.badquar.to)**, a journal of tiny computational literature where every piece must fit in a couple of kilobytes. The constraint is the medium. All credit for the form belongs there; this plugin only generates pieces in its spirit.

[See a generated piece](https://ariaxhan.github.io/agentmailkit/samples/taper-piece.html)

## Enabling it

```json
"post": ["taper"],
"options": {
  "taper": { "out_dir": "pieces", "max_bytes": 4096 }
}
```

| Option | Default | Meaning |
|---|---|---|
| `out_dir` | `<out_dir>/pieces` | Where pieces are written |
| `max_bytes` | `4096` | Size budget, warned on rather than enforced |
| `model` | the job's model | Override the generating model |
| `slug` | the job id | Used in the filename and `data-type` |
| `prompt` | built in | Replace the brief entirely |

Output lands at `<out_dir>/<date>-<slug>.html` and contains a single `<section>` element, which makes pieces trivial to embed in a static index page.

## Why it is a post hook

It runs **only after a confirmed send**, and it fails open: if generation fails or the model returns something that is not a `<section>`, it logs and returns.

A strange generative artifact must never be the reason a digest does not arrive. The email is the product; this is a bonus.

## Publishing them

Pieces are self-contained fragments, so a gallery is a loop over a directory. This repo's own sample gallery works exactly that way: wrap each `<section>` in a minimal page and link them from an index.
