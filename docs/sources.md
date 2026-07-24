# Sources

A source turns something into a block of text that lands in your prompt. Reference one in a job as `alias=name:argument`, then use `{alias}` in the prompt file.

```json
"sources": ["papers=arxiv:cs.AI#6", "weather=weather:Brooklyn"]
```

The alias matters: it is how the block reaches the prompt, and it means two sources of the same kind never collide.

Every source is **deterministic** (it returns real data, not a model's recollection of data) and **fails open** (an API being down produces a short notice, never a crashed run).

---

## Local

Sources that read your machine. This is the category no cloud scheduler can offer.

| Source | Argument | Example |
|---|---|---|
| `file` | a path | `notes=file:README.md` |
| `glob` | a glob pattern | `recent=glob:drafts/*.md` |
| `recent` | `DIR` or `DIR:DAYS` | `journal=recent:~/notes:3` |
| `shell` | any command | `commits=shell:git log --oneline -10` |

`shell` is the escape hatch. Any command's stdout becomes prompt context, so you are never blocked waiting for a plugin to exist. Paths resolve against `root` in your config unless absolute.

## Research

| Source | Argument | Example |
|---|---|---|
| `hf` | a preset or any Hub query | `models=hf:full` |
| `arxiv` | a category or any arXiv query | `papers=arxiv:cs.AI#6` |

**`hf`** takes three presets (`full`, `pulse`, `brief`) or, for anything else, the Hub API's own query string:

```
models=hf:models?author=meta-llama&limit=5
video=hf:models?filter=text-to-video&sort=downloads&limit=8
data=hf:datasets?search=clinical&sort=likes&limit=10
```

Whatever the Hub accepts, this accepts. There is no curated category list to outgrow.

**`arxiv`** takes a bare category for the common case, or raw arXiv query syntax verbatim:

```
papers=arxiv:cs.LG#5
search=arxiv:q=retrieval augmented generation#5
precise=arxiv:cat:cs.CL AND abs:agent#8
author=arxiv:au:Hinton#5
```

`#N` sets the item count and is unambiguous even when the query is full of colons.

Both hand the model **real ids, counts, titles, authors and links**. This is the point: the dominant failure of an LLM research digest is inventing a plausible paper title or a confident download number, and a figure that arrives pre-fetched cannot be hallucinated.

## World

| Source | Argument | Example |
|---|---|---|
| `rss` | feed URLs joined by `\|` | `digs=rss:https://www.archaeology.org/feed#5` |
| `news` | `Label=URL` joined by `\|` | see below |
| `history` | `events\|selected\|births\|deaths\|holidays` | `history=history:events#3` |
| `weather` | a place name or `lat,lon` | `weather=weather:Brooklyn#2` |

**`rss`** is the workhorse. Almost everything interesting publishes a feed, so this one plugin unlocks archaeology, science, security advisories, release notes, court dockets, a friend's blog. If a feed is broken it tells you *why* (HTTP error, served HTML, unparseable) rather than returning a convincing silence.

**`news`** is the same machinery with an opinion. Feeds stay **labelled** all the way into the prompt:

```json
"world=news:BBC=https://feeds.bbci.co.uk/news/world/rss.xml|Al Jazeera=https://www.aljazeera.com/xml/rss/all.xml#4"
```

Then ask the prompt to note where outlets agree on facts and where the emphasis diverges. That comparison is the most interesting thing in a news email and it is impossible once you merge feeds into one pile.

**`history`** pulls Wikipedia's on-this-day feed, sampled deterministically per date, so two runs on the same day agree but consecutive days do not repeat.

**`weather`** uses Open-Meteo (no key, no account). It also demonstrates the whole thesis in miniature: a model asked to "check the weather" invents a temperature; a model handed `18C` cannot.

---

## Writing your own

About thirty lines. See [plugins.md](plugins.md).
