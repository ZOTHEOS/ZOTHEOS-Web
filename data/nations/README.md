# Indigenous nations of today: the ZOTHEOS registry

`nations.json` is the source of truth: nations and peoples of today, each with its own name first, where it lives,
and facts in our own words. Every fact carries its source (title, publisher, URL), the exact phrase on that page that
supports it, and the date it was checked. `nations.min.json` is the same data, minified.

- `sources/` holds the research, verification and respect-review files for every region, so each decision can be
  traced.
- `tools/merge.py` assembles `nations.json` from `sources/`; `tools/validate.py` checks the shape and the writing
  rules; `tools/nations_refresh.py` re-fetches every source, checks that the phrase is still there and marks facts
  stale (run weekly; a stale fact is hidden until a person re-verifies it).
- `ARCHITECTURE.md` describes the whole system (naming, rotation, announcing, the hub, the news shelf, governance).
- `REPORT.md` records totals, drops with reasons and the open judgment calls.

Facts are compiled with AI help from published sources and checked by a second pass; corrections and takedown
requests from any nation are honored. Nothing here is a game object: nations never appear near the game's
antagonist, on a fail screen or in scoring.
