Write the morning brief for {date} ({day}).

Everything below was fetched from live APIs. Temperatures, headlines, years and links
are real. Cite them exactly and never invent one.

## Weather
{weather}

## World news, by outlet
{world}

## On this day
{history}

---

Write the email as markdown. Structure, exactly:

The VERY FIRST LINE must be a stats line in this exact format, nothing before it:

    @stats: Now=18C, Stories=4, Oldest=1921

Choose three tiles that genuinely summarise today (a temperature, a story count, the
oldest year in the history section). Short labels, short values. This line is required.

## Today
One short paragraph: the weather in plain language and the single thing most worth
knowing this morning. No preamble.

## What happened
The three or four stories that matter. One line each on the actual event.
Where two outlets covered the same story differently, say so plainly and name them:
what they agree on factually, and where the emphasis diverges. That contrast is the
most valuable thing in this section, so do not flatten it into a neutral summary.

## On this day
The most interesting one or two historical entries, told as a fact worth repeating,
not a Wikipedia sentence. Include the year.

Rules: link every story. Plain language, no hype, no "in today's fast-moving world".
Under 400 words. Markdown only, never HTML: the theme owns all formatting.
