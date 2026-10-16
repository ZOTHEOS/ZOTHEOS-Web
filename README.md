# ZOTHEOS-Web

The Theater at `/theater` is generated from `data/theater/films.json` by
`python tools/theater_build.py` (`--check` detects stale output). It contains
original short summaries, official viewing destinations, source dates and
clear distinctions between films, trailers, excerpts and information pages.
`data/theater/research_queue.json` retains unresolved recording matches and
availability failures. No film media or poster artwork is rehosted.

The page loads its fonts, abstract artwork and code locally. Selecting a title
does not create a player. Explicit Load Player consent creates one approved
provider frame; close or a different selection destroys it. Playback requires
the provider's Play control. Source links work without JavaScript. A publisher
metadata response is not a promise of playback or a full-film editorial review.

The Nations build refreshes the Theater after shared fonts change. Both refresh
workflows stage its generated HTML. Route-specific security permits approved
players only on the Theater; other routes keep their existing frame restrictions.
Run the independent renderer/consent contract with
`python -m pytest tools/tests/test_theater_acceptance.py -q` and run the full
website test suite before publication.
