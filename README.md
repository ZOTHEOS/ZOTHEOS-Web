# ZOTHEOS-Web

The Theater at `/theater` is generated from `data/theater/films.json` by
`python tools/theater_build.py` (`--check` detects stale output). It contains
original short summaries, official viewing destinations, source dates and
clear distinctions between films, trailers, excerpts and information pages.
`data/theater/research_queue.json` retains unresolved recording matches and
availability failures. No film media or poster artwork is rehosted.

The page loads fonts, abstract artwork and code locally. Provider thumbnails and
one selected ready player contact their providers automatically. Playback still
requires the provider's Play control; no Load or Unload step is needed. Selecting
an external-only story removes the player and retains its official viewing link.
A publisher metadata response is not a promise of regional access, accurate
captions or a full-film editorial review.

Each story has a native `/theater#film-<id>` link. Opening it selects that record
without silently loading a different featured player first. A source-only link
creates no player. Ordinary selection and filters do not rewrite URL history or
persist searches. The Where To Watch facet distinguishes configured Watch Here
players from Official Site destinations; viewing restrictions remain visible.
Without JavaScript, the featured player and every official source/story link
remain in the static page.
The Nations build refreshes the Theater after shared fonts change. Both refresh
workflows stage its generated HTML. Route-specific security permits approved
players only on the Theater; other routes keep their existing frame restrictions.
Run the independent renderer/player contract with
`python -m pytest tools/tests/test_theater_acceptance.py -q` and run the full
website test suite before publication.
