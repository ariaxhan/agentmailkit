You are writing the daily brief for {date} ({day}).

Use the material below to write a tight, skimmable HTML email. Lead with the one
thing that matters most today. No preamble, no "here is your brief" throat-clearing.

## Project readme (context)
{readme}

## Recent commits
{commits}

---

Write the email as **markdown**, never HTML. A theme turns your markdown into the
finished email, so any HTML tag you write will be shown to the reader as literal text.

Use `## Section` for each section, `- item` for lists, `**bold**` for emphasis, and
`[text](url)` for links. Under 400 words.

Output the email only. No preamble, no commentary about your own process, no notes
about tools. The first character of your reply is the first character of the email.
