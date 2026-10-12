# Ollamaliztli (live web game)

The mini-game is live at https://zotheos.org/game and linked from the main page footer.

`index.src.html` is the readable source, `build.py` makes `index.html` (ES5, size and writing
gates). Modes: Drop (the stone ring) and Echo (the labyrinth and the Stone Face). `DESIGN.md` and `DESIGN_HUNT.md`
are the design records. `nations.fixture.json` is layout test data only and must never be served as `nations.json`.
Real nation data lives in `data/nations/`.
`py -3.10 build.py --dev` writes `index.dev.html` with the test hooks kept (not committed); `build.py` prints the sha256 of the
injected overlay CSS for hosts with a strict style-src CSP. Revision 2.1 (2026-10-10) is recorded at the top of `DESIGN.md`, and
Revision 2.2 (2026-10-11, the Echo presence pass: follow camera, scale, terror brackets) at the top of `DESIGN_HUNT.md`.

Revision 2.3 (2026-10-12): Echo goals, ring progress, ball status and controls are visible. Drop adds warning phases, active spikes, more vertical room and three original Stone Guardian profiles. Nation cards expand History And Context on request from same-origin `history.json`; all published history facts retain their canonical source receipts. The complete record and official resources are linked at `/nations/resources`. This is a growing collection, not complete worldwide coverage.

Run engine regressions with `py -3.10 -m pytest tools/tests`; the Node acceptance runners use the readable source. After building, run `tools/csp_sync.py` and `--check` to synchronize every game route and its injected CSS.
