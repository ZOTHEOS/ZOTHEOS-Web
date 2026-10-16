# ZOTHEOS-Web

The Theater at `/theater` is generated from `data/theater/films.json` by
`python tools/theater_build.py` (`--check` detects stale output). It contains
original short summaries, official viewing destinations, source dates and
clear distinctions between films, trailers, excerpts and information pages.
`data/theater/research_queue.json` retains unresolved recording matches and
availability failures. No film media or poster artwork is rehosted.

The page loads fonts, abstract artwork and code locally. Provider thumbnails and
one selected ready player contact their providers automatically. Eligible YouTube
and Vimeo previews start muted when the screen and controls are visible, then
pause outside view or when the tab is hidden. Poster and Next Story selections
remain muted previews, capped at 15 seconds on phones and 45 seconds on desktop.
Actual Play, Sound or native playback controls take deliberate control. Manual
Pause stays paused until Play. Still, device reduced motion and Save-Data prevent
automatic previews. Difficult-content, audio-led and uncertain-caption holds wait
for Play; National Film Board and PBS use native provider controls. No Load or
Unload step is needed. Selecting an external-only story removes the player and
retains its official viewing link.
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

The build-time `caption_tracks.json` sidecar retains dated caption observations;
`preview_policy.json` records preview holds. Neither certifies caption accuracy or
complete-film review. Current player reports determine Sound and caption labels.
The Theater keeps the shared themes, motion, intensity and translation controls.
The stepped light frame is original project geometry, with no claim to traditional
or ceremonial meaning. No generated video loop or additional media provider is
required by this implementation.

The independent muted-preview, command-order, selection-boundary and reading-layout
contracts are in `tools/tests/test_theater_presentation_acceptance.py`,
`test_theater_command_order.py`, `test_theater_story_preview_boundaries.py` and
`test_theater_translation_layout.py`. Run the full website suite before publication.
