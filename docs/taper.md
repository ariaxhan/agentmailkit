# Taper pieces

An optional companion artifact. After the email is safely sent, agentmailkit can generate a tiny self-contained interactive HTML fragment responding to the same material: one file, no external assets, meaning carried by form and algorithm rather than prose.

Where the digest says what happened, the piece is an abstract reply to it.

> The Taper form comes from **[taper.badquar.to](https://taper.badquar.to)**, an online literary magazine for small computational pieces published by Bad Quarto, running since 2018. Every piece fits in a couple of kilobytes; the constraint is the medium. All credit for the form belongs there. This plugin only generates pieces in its spirit, and reading a few real ones will tell you more than this page can.

## What the form actually is

The generator brief is grounded in characteristics observed in real published pieces, because the obvious guesses are wrong. It is not "generative art with a caption".

- **Language is usually the material.** Pieces are built from a small curated vocabulary, a set of nouns, a list of exclamations, the lines of a poem. The code arranges, reveals or destroys those words. It is a poem whose typesetting is an algorithm.
- **It unfolds over time.** Words arrive one at a time on a timer, lines vanish in a shuffled order, a form animates frame by frame. A static composition is not a Taper piece.
- **Committed palettes, often light.** A saturated ground (warm sand, ochre, acid yellow, hot blue) with dark earth-toned text is at least as common as black. Muddy grey on near-black is the classic failure.
- **Type is a material.** Sizes vary dramatically inside one piece, from an enormous opening line to near-footnote. Serif is common.
- **The whole viewport is the field**, with elements often absolutely positioned at randomised percentages rather than stacked in the middle.
- **A closing gesture** when the sequence exhausts itself.

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
