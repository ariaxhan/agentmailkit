# Deduplication

**This is what separates a scheduled digest from a scheduled annoyance.**

Sources return whatever is currently trending or recently published. On consecutive days they return substantially the same items, so without a memory of what already went out, day two is mostly a reprint of day one and the reader stops opening it.

Turn it on:

```json
"dedup": true
```

Or configure it:

```json
"dedup": { "window_days": 30, "path": "state/seen.jsonl", "record": "delivered" }
```

## The contract

Every clause is load-bearing.

**1. Filter before the prompt, not after.** Already-sent items are removed from the material the model ever sees. You cannot reliably ask a model to "not repeat yesterday", and paying to summarize items you intend to discard is waste.

**2. Record only after a confirmed send.** If delivery fails, nothing is marked seen, so the next run can still surface those items. Recording at generation time would silently burn a day of content on a failed send.

**3. Deterministic keys.** An item is identified by its normalized URL. No fuzzy similarity, no embeddings, no model judgement. The same item is the same item.

**4. A window, not forever.** Items age out (default 30 days) so a genuinely recurring thing may legitimately reappear later.

## What counts as the same item

URLs are normalized before comparison: scheme and `www.` dropped, tracking parameters stripped, trailing slashes and case ignored, and arXiv versions collapsed so `abs/2607.21595v1` and `v2` are one paper rather than two.

## delivered vs presented

```json
"record": "delivered"   // default
```

Marks seen only the items whose links actually appear in the sent email. If the model was shown twenty items and wrote about four, the other sixteen remain available tomorrow, because they were never actually sent to you.

```json
"record": "presented"
```

Marks seen everything the model was shown. Stricter, guarantees no repeat, but burns items the model chose to omit.

The default is the honest one.

## Inspecting it

The ledger is append-only JSONL. Greppable, readable, and safe to hand-edit when something goes wrong.

```bash
wc -l state/seen.jsonl
grep morning-brief state/seen.jsonl | tail -5
```

To make an item eligible again, delete its line.

## Seeing it work

The `dedup` block in a run receipt reports exactly what happened:

```json
"dedup": { "seen_in_window": 42, "dropped": 13, "fresh": 17, "recorded": 4 }
```

Thirteen items were suppressed as already-sent, seventeen fresh ones reached the model, and four were recorded because four made it into the email.
