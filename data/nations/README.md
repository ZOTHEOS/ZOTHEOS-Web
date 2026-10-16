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

ZOTHEOS compiles facts from published sources with separate evidence and meaning checks; corrections and takedown
requests from any nation are honored. Nothing here is a game object: nations never appear near the game's
antagonist, on a fail screen or in scoring.

## Current Scope, Checked October 16, 2026

The registry contains 461 researched profiles and 1,302 raw facts. Publication controls currently show
1,300 facts and retain two existing holds. The latest bounded batch adds Nansemond Indian Nation and
Upper Mattaponi Tribe as separate profiles, with eight sourced facts, four titled history layers and
four direct links to their own resources. Every earlier canonical record and fact date is preserved.

The directory preserves 2,272 differently scoped source records in eight lists. Ten source records
have reviewed links to researched profiles. These overlapping units are not a count of distinct
Indigenous Nations. US and worldwide coverage remain incomplete; government recognition is not the
definition of Indigenous identity. Four state inventories are preserved, while 46 other state source
scopes and four additional inclusion lanes remain pending.

Matching Names now places a readable summary beside the results and offers clear recovery routes
when no records match. Searching researched profiles remains a separate route. All directory names
stay available without JavaScript; filters do not remove pending names from the underlying record.
