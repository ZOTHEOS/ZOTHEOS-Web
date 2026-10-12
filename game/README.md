# Ollamaliztli (prototype, not linked from the site)

The hidden mini-game: `index.src.html` is the readable source, `build.py` makes `index.html` (ES5, size and writing
gates). Modes: Drop (the stone ring) and Echo (the labyrinth and the Stone Face). `DESIGN.md` and `DESIGN_HUNT.md`
are the design records. `nations.fixture.json` is layout test data only and must never be served as `nations.json`.
Real nation data lives in `data/nations/`.
`py -3.10 build.py --dev` writes `index.dev.html` with the test hooks kept (not committed); `build.py` prints the sha256 of the
injected overlay CSS for hosts with a strict style-src CSP. Revision 2.1 (2026-10-10) is recorded at the top of `DESIGN.md`, and
Revision 2.2 (2026-10-11, the Echo presence pass: follow camera, scale, terror brackets) at the top of `DESIGN_HUNT.md`.
