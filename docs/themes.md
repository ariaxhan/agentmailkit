# Themes and the renderer

**The model writes words. It never writes markup.**

This is the single most important design decision in agentmailkit. Ask a model for HTML and you get a slightly different email every day; some days it forgets the styles entirely, some days it invents a layout. Take markup away from it and the email is byte-identical forever, while the content still changes.

Set one field:

```json
"render": "warm"
```

Omit it and the model's output is delivered untouched.

## Palettes

| Theme | Look |
|---|---|
| `warm` | Cream ground, gold rule, white cards. The default |
| `slate` | Cool grey-blue, quieter. Good for work digests |
| `ink` | Dark background, warm accent |
| `plain` | No theme; pass the model output straight through |

Override any colour per job without writing a theme:

```json
"options": { "theme": { "accent": "#7b6cd9", "ground": "#f7f6ff" } }
```

Or globally in config under `extra.theme`.

## Adding a theme

**Additive by construction.** Every palette is a partial dict merged over a shared `BASE` that defines every key the renderer reads. A new theme therefore cannot alter or break an existing one, and a palette that omits keys (or misspells one) falls back to `BASE` rather than raising mid-render.

### With no code at all

Declare it in `agentmailkit.json`:

```json
"extra": {
  "themes": {
    "forest": { "accent": "#3f7d4f", "accent_soft": "#a8c9ae", "ground": "#f4f7f4" }
  }
}
```

Then use it like any built-in:

```json
"render": "forest"
```

Supply one key or all nine. Anything you leave out is inherited.

### At runtime

```python
from agentmailkit.themes.builtin import register_palette

register_palette("forest", {"accent": "#3f7d4f", "ground": "#f4f7f4"})
```

### Palette keys

| Key | Used for |
|---|---|
| `ground` | Page background |
| `card` | Card background |
| `ink` | Body text |
| `muted` | Dates, footers, secondary text |
| `accent` | Top rule, card border, link underline |
| `accent_soft` | Second stop of the top gradient |
| `rule` | Dividers |
| `font` | Body font stack |
| `mono` | Stat tiles and inline code |

### A theme with different structure

If you want to change the *layout* rather than the colours, register a `render` plugin instead and return whatever HTML you like:

```python
from agentmailkit.plugins import render

@render("newspaper")
def newspaper(ctx, body):
    return my_html(body)
```

Ship it in your own package via the `agentmailkit.plugins` entry point and the core never learns its name. See [plugins.md](plugins.md).

## What the model may write

A deliberately small markdown subset. Anything outside it is escaped rather than honoured, so a model cannot inject layout.

```markdown
## Section            starts a new card
### Subheading        heading inside the card
- item                bullet list
> quote               pull quote
---                   divider
**bold**  *em*  `code`  [text](url)
@stats: Now=18C, Stories=4, Oldest=1921
```

`@stats:` renders the KPI tile row. It must be its own line. If you want tiles, say so explicitly in the prompt and show the exact format, or the model will skip it.

Bare URLs are auto-linked, so sources that emit plain links still look right.

## House style is enforced, not requested

Em dashes, en dashes and non-breaking spaces are substituted at render time.

A prompt saying "never use em dashes" is a suggestion a model will eventually ignore. A substitution in code is a guarantee. Anything that must be true on every single run belongs in the engine, not in a prompt.

Extend it per job:

```json
"options": { "render": { "house_style": { "utilise": "use" } } }
```

## Why inline styles

Every style is inline. No `<style>` block, no external fonts, no images to fetch. This is not a stylistic choice: it is the only thing mail clients render reliably.

## Titles and footer

```json
"options": { "render": {
  "title": "Morning Brief",
  "subtitle": "{day}, {date}",
  "footer": "Sent from my kitchen table"
} }
```

Title defaults to the job's subject.
