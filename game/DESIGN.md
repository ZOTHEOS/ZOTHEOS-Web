# OLLAMALIZTLI: game design document

A live mini-game at zotheos.org/game, linked from the main page footer. Two modes, five seeded levels each, monochrome chrome on pure black.

Target file: `game/index.html` (one file, inline CSS and JS, ES5, Canvas2D, no libraries, same-origin educational JSON). The build warns above 92,000 bytes of minified JavaScript and fails above 100,000.

Writing rule for every visible string: no em dash. Use a period, a comma or a colon.

> **Revision 2.3 (2026-10-12).** Echo now displays its ring objective, ball possession and a pause legend; aiming uses one direction resolver for preview and strike. Cards can expand published history with canonical receipts. Replay uses its own identifier. The notes below supersede earlier gameplay and size statements.
>
> **Drop challenge pass (integrated, 2026-10-12).** This note supersedes older statements that Drop is unchanged. The ledge/gap and ring random streams retain their layout; row pitch is 88/92/96/100/104 logical units instead of 72, and the ring arena extends 480 units below the final row instead of 400. Strike forces, gravity, ring targets, timers and Assist are unchanged. More vertical room does not increase the ball's jump impulse.
> - **Spikes.** An independent `0xD06B` stream places three-tooth traps on horizontal segments at least 56 units long, clear of the gap lips and markers. The first two rows, every central landing row and the final row stay clear. Nearby traps show hollow rising outlines for at least 0.95 s (1.33 s Calm), turn solid for 0.65 s (0.91 s Calm), then rest for a seeded 1.5 to 2.0 s (2.1 to 2.8 s Calm). Leaving proximity disarms them and requires a fresh full warning.
> - **Original Stone Guardians.** From level 2, a court seed selects Prism, Rampart or Vault from an expandable catalog of original geometric profiles. These are fictional mechanical obstacles, with no deity, sacred depiction or living nation as an enemy. Their central patrol leaves wall ring approaches open. A hollow halo warns for at least 1.1 s (1.54 s Calm), solid contact lasts 0.85 s (1.19 s Calm), and rest lasts 1.8 s (2.52 s Calm). The round body defines contact; decorative rims are safe. Reduced motion suppresses decorative rotation.
> - **Attempts.** Only solid-phase contact costs an attempt, using the existing single failure/retry path. Held balls do not arm hazards. Retries grant 1.0 s protection, then require the full proximity warning again. Assist retains unlimited attempts. Physics clocks advance at 120 Hz; drawing does not advance or mutate hazard state.
> - **Isolated verification, not a human difficulty claim.** A Node VM simulation checked 640 generated courts, 1,935 spike placements and all three guardian profiles; gap/marker safety and the original layout/ring random streams held. With hazards disabled, the taller geometry descended on all 160 courts in a 32-seed x five-level sweep at normal pace and all 160 at Calm pace. A simple hazard-aware bot reached the ring arena on 144/160 normal and 146/160 Calm runs; failures were hazard contacts. A stationary-contact test measured earliest spike damage at 0.958 s normal and 1.333 s Calm. Guardian warning, single attempt loss, retry protection, Assist, and independent rendering schedules passed. Grounded strike rise was 64.965 logical units in one measured level-2 run.
> - **Size.** The isolated Drop source adds 2,998 minified JS bytes to the 91,989-byte replay baseline. The full game must be rebuilt and verified against the unchanged 100,000-byte hard ceiling after the separate history and Echo patches are integrated. Browser feel, final combined minification and human difficulty remain for the integrating seat.

> **Revision 2.2 (presence pass, 2026-10-11).** The Echo follow camera, the new scale, the `FACE` data changes, the terror brackets, the edge markers and the pause map are recorded at the top of `DESIGN_HUNT.md`, which wins on the chase mode. Version `2.2.0`; 91 989 bytes of minified JS, under the 92 000 budget. Drop is unchanged.

> **Revision 2.1 (playtest and review fixes, 2026-10-10).** Where this note and anything below, or `DESIGN_HUNT.md`, disagree, this note wins. Version `2.1.0`.
> - **Owner decisions.** The size budget is re-baselined to 92 000 bytes of minified JS, about 40 KB gzipped, because the game loads only when a visitor opens it; `build.py` warns over 92 000 and fails over 100 000 (as built: 90 330 bytes, 39 656 gzipped). Today's court is the **UTC day**: `today()` and the nations rotation `natDay()` both read UTC, so everyone on Earth shares one court at the same moment. The Stone Face keeps its shell teeth; the community-advisor question about them (`DESIGN_HUNT.md` section 27, question 1) stays listed, and section 27 supersedes section 12 below.
> - **Must fixes.** Mouse hover no longer throws: the aim line's point buffer `g.al` is allocated once per level in `E_lay` (the playtester's trace: every mouse move over the canvas emptied the frame). The two-touch rule holds on every level: no contact while it recovers or plays (states 7 and 6), so mark and turn-back are at least 1.0 s apart (a hard assert in the harness; measured minimum 1.008 s on all levels, was 0.008 s on level 3). Level 3 no longer locks its stare on a player sheltering in a claimed court: hunting you onto safe ground it waits at the mouth like every other level (3 s re-entry cooldown), and when its hunt timer runs out it returns to Patrol (it used to keep the Rush label and so ignored every sound for the rest of the level).
> - **Finale.** The silence clock holds while the Stone Face waits at your court, or stands within 2 tiles of a Great Court mouth; a turn-back in the finale gives the clock back at least 3 s plus 75% of one step. Perfect-bot attempts lost to the silence over 40 level runs: 21 before, 15 after (levels are longer now, see below); to the face: 4 before, 2 after. The ball can no longer deadlock against a ring's reach (the corner slide follows the direction pressed instead of the tile centre); with the face asleep every level clears on all 8 test courts (was 39 of 40), with the Great Ring passed 10 to 14 s after it opens on every variant, so a decisive strike from the court floor wins.
> - **Difficulty.** Boards 23x31, 25x33, 27x35, 27x37, 27x37 (one size up); a third side ring on level 2; from level 2, patrol waypoints on the midpoints of the L+1 longest mouth-to-mouth corridors, snapped to a junction when one is within three tiles (`E_corr`); investigate speed 4.5 and 4.9 on levels 4 and 5, above your walk of 4.2 and 4.4 (a deliberate exception to the `DESIGN_HUNT.md` 23.3 assert "investigate below walk", by the playtest decision); pats carry 5 + 0.5 x level tiles before the hearing factor. Measured over 8 courts x 5 levels: perfect bot 100/88/88/88/100 (was 88/100/100/100/100), 120 ms bot 100/88/88/88/100 (was 88/100/100/100/100). The design curve (97/93/88/82/72 and 93/88/80/72/62) is met or passed on levels 1, 3 and 4; level 5 stays easier for a perfect-information bot than the curve asks, and level 2 sits 5 points under on one legitimate loss (XYZ-789). Every other non-clear is a 480 s bot standoff (the bot holding, dodging or sheltering near the face), not a lost attempt; the 120 ms bot lost 10 attempts to the silence and 3 to the face over its 40 runs (was 17 and 2).
> - **Length.** Two passes per side ring on levels 4 and 5: the first pass lights the wall-side stone and is heard (`ring-half {n, of}`, caption "One stone lit. Pass the ring once more to claim it."), the second claims; the HUD dot half-fills (a hard-edged half, no ramp). With the face asleep the levels take 37/42/46/47/55 s (was 31/32/40/36/42); with the hunter, perfect-bot medians 66/42/77/111/127 s (was 60/57/113/70/99). Still under the 70 to 200 s targets on levels 1 to 3.
> - **Dribble.** Control radius 0.9 (was 0.75), spring 9 (was 6), control held 0.2 s after the move vector drops, and a slow ball at a standing player's feet is eased to the spot ahead (spring 4, capped at 2 tiles/s) and comes to rest there. Keyboard turns with control kept: 18/15/18 of 24 at 0/50/150 ms key gaps (was 16/6/6); a stopped player's ball rolls 0 tiles (was 2.45). Pats come at most one per 0.45 s, and a ball eased to a standing player does not pat.
> - **Tell.** Contact never lands within Tn of the eyes first showing, and notice drained below one third resets to 0, so the next fill starts over. Minimum warning from eyes-first-shown to contact in the random-bot sweep: 0.75/0.87/0.62/0.57/0.55 s against Tn 0.75/0.68/0.62/0.56/0.50 (was 0.75/0.67/0.62/0.56/0.23).
> - **Review fixes.** The herald lives on the title only: no nation-card hook and no seen count during play; the herald's hook fires only when its nation or fact changes; a screen-reader separator follows the kind chip; Next and Previous announce through one channel (the live region). Visible Nahuatl follows one convention, no vowel length marks on any screen (Ollamaliztli, Olli, Xayacatl); `TERMS` keeps the dictionary forms (first vowel long in ōllamaliztli, the unattested long ī dropped) and every term now cites its source (Online Nahuatl Dictionary entry; Molina 1571 folios; Karttunen 1992; Sahagún, Primeros Memoriales, ed. Sullivan 1997; Lockhart 2001), shown in About under "Nahuatl words used here". `build.py` prints the sha256 of the injected overlay CSS on every build, for hosts with a strict `style-src` that pass no `opts.nonce` (the API comment documents both). Enter in the court-code field starts the last mode played, or moves focus to Drop. `natValid()` drops ids starting `test-` and facts of kind `test` in the release build; the dev build keeps them for the layout fixture. Math.imul polyfill. `safe-enter` and `safe-leave` fire once the footing has held 0.25 s. The band cache key is numeric and the Drop HUD rebuilds only on change. Tutorial captions return on every open. `face-hear` fires at most four times a second and a stream of sounds no longer freezes the face with retarget pauses; a chase ends once its notice has fully drained outside a rush.
> - **Not validated by bots:** feel on hardware (hover aim line, the half-filled dot, two-pass ring readability), the human difficulty curve, Calm pace, sound.

> **Revision 2.0 (2026-10-09): Run is replaced by Echo.** `DESIGN_HUNT.md` replaces section 3 (Mode 2: Run) and wins over this file on the chase mode, the nations layer and the About text. Drop is unchanged.
> - **API:** `ZTH_GAME.open('echo')` opens Echo; `open('run')` still works and opens Echo. `version` is `2.0.0`. New options: `nations` (an array, or a same-origin URL), `nationsUrl`, `nationsUpdated`, `nationCards` (false keeps nation cards off the level breaks), `contact`, `nationsPage`. With no option the game asks for `nations.json` next to the page (same origin only, 3 s timeout, aborted on close). There is no nation data in the code; if nothing loads, nothing is shown.
> - **As built** (see the build report for the full list of deviations): the keyboard hold-to-aim, the second-finger aim stick, the close-up and the "it plays a resting ball" trigger were cut (section 24.3 cut order); the title herald advances every 14 s and continues to new nations on each visit; seeded room placement tries several Great Court seats before a new try; the straight cap exempts stretches with nothing to open into; V3, V4 and V8 are relaxed (see `DESIGN_HUNT.md` notes in the report).
> - **Size:** about 87 KB minified, over the 72 KB budget. `build.py` warns over 72 000 bytes and fails over 90 000.
> - Test fixture: `nations.fixture.json` (three "Test Nation" entries whose facts say "Test fact, not for release."). Never ship it as `nations.json`.

> **Revision 1.1 (playtest and code review fixes, 2026-10-08).** Where this note and a section below disagree, this note wins.
> - **Drop:** the court no longer rotates with tilt (it softened every pixel-snapped line and pushed the court off narrow phones); tilt shows as a small level under the HUD. The ring is drawn standing on its edge, opening sideways, with its back half under the ball and its front half over it, so a pass visibly threads through. The turning ring reads edge-on when open and face-on when closed. Level times are 40, 43, 46, 50 and 54 s (bot descents take 10 to 22 s, so the clock and the +3 s markers matter). A pass needs 25 units/s sideways; slower crossings say "Too soft. Strike it through." "A rare pass." now means a pass on the first strike in the court. A strike with no footing shows a grey arc under the ball and, once per session, a caption. The on-screen Strike button is gone: tap strikes, hold a side to tilt, a second finger strikes at once. Mouse: the pointer's x tilts while hovering, a click strikes; a key press hands tilt back to the keyboard. On touch screens the court floor sits 40 px higher so thumbs do not cover it.
> - **Run:** cacao lies in seeded, mirrored trails on loops only (never in dead-end pockets), 64 + 6 x level beans, so a level takes about 20 to 45 s of perfect play. Each level's twist (rising water, quicker currents, the call, night) starts when half the cacao is taken, with a caption. The gate opens at the Reach in the outer wall at least 60% of the farthest causeway distance from the player, and its target time follows that distance. The lure appears with the twist and is drawn as a broken frame (one stepped side, water on the other). Player speed 6.0, 6.5, 7.0, 7.5, 8.0 (+33%); Ahuizotl 4.7, 5.2, 5.7, 6.2, 6.8 (ratio 0.78 to 0.85, +0.02 x player speed in the Reach). A turn pressed up to 0.42 tile past a junction still takes it. Flood slows the player to 0.8. At night the cacao and the carved frame stay visible, and Ahuizotl outside the light shows its eye. A corner marker leaves a dive ripple where Ahuizotl was. The pool clock is drawn as a fraction of the dive it began. Captions sit beside the maze on wide screens and under it otherwise, never over it.
> - **Shell:** the overlay's CSS is injected as `<style id="zgS">` on open and removed on close, so `ZTH_GAME.open()` works on any host page. On open, `returnFocus` defaults to the focused element, and other children of `body` get `inert` until close. Escape on the pause screen resumes; only the Close button closes. Keys with Ctrl, Meta or Alt are ignored. The court code field shows "Court code ABC-DEF." or "Code not found. Using today's court." and Enter starts Drop. The result screen offers **Replay this court**, **New court**, **Other mode**, **Close**. Static screens draw once and stop the animation loop. The build gates the output on an ES5 parse (acorn) and on no em or en dash.
> - **Size:** about 45 KB minified, 19 KB gzipped (the injected overlay CSS is 3.7 KB of that). Over the 30 KB target; the owner accepts or asks for cuts.

---

## 0. Cultural grounding (read first)

These notes shape every decision below. Each one appears again inline where it matters.

- **Ōllamalīztli** (Nahuatl, also written ollamaliztli or ullamaliztli) is the Mexica name for the Mesoamerican ballgame. It was played for more than three thousand years, from the Gulf Coast and Oaxaca to the Maya region and north toward the present-day US Southwest, where ballcourts also appear (Hohokam). It is not only ancient: **ulama is still played today** in a few towns in Sinaloa. The game must never present it as a dead or exotic thing. The credits line says so plainly (see section 10).
- **Ōlli** is rubber, and the ball. Mesoamerican people made it by mixing latex from *Castilla elastica* with juice of the morning glory vine *Ipomoea alba*, which made it bounce; materials scientists confirmed the chemistry in 1999. It was heavy (several kilograms) and lively. In the game the ball is lively and a little heavy, not a ping-pong ball.
- **Players struck the ball with the hip** (also thighs and forearms in some regional forms), not the hands or feet. Our action button is a **hip strike**, never a "kick" or "throw".
- **Tlachtli** is the court: a long I-shaped alley with sloped or vertical side walls. **Tlachtemalacatl** is the stone ring set high and vertical in the wall, at center court in the Mexica form. Passing the ball through it was rare and decisive. The game treats a ring pass as the big moment of each level, not a routine goal.
- **Xicalcoliuhqui** ("twisted gourd") is the step-fret: a stepped line ending in a hook or spiral. It appears across Mesoamerica (the Zapotec palace walls at Mitla are the famous example) and across Pueblo and other Native traditions of the US Southwest. It is the visual link between Mexican and Native American roots that the owner wants to honour, and it is the only ornament this game uses.
- **Ahuizotl** (āhuitzotl, roughly "spiny water one") is the water creature described by Nahua authors in Book 11 of the Florentine Codex (folio 70v onward): small, like a little dog, black and slick "like rubber", small pointed ears, a long tail **ending in a hand**. Accounts tie it to drowning people at the water's edge, sometimes after a sound like a crying child draws them near. It is a feared creature of the lake, **not a deity and not "evil" in a moral sense**. Mesoamerican gods were not simply evil to the people who honoured them, so we never cast a god as a villain. The game frames Ahuizotl as the danger of the water: something you respect and keep away from.
  - Do not confuse it with **Ahuitzotl**, the eighth Mexica tlatoani (ruled 1486 to 1502), who carried the creature's name. The game never depicts or names the ruler.
  - Credit: the Florentine Codex was compiled under Bernardino de Sahagún, but its Nahuatl text and images were made by Nahua scholars and artists from Tlatelolco and Tenochtitlan. In-game notes say "Nahua accounts recorded in the Florentine Codex", not "Sahagún says".
  - We do not depict gore. The codex passages about what happens to a drowned body stay out of the game.

**Never in this game:** skulls, tzompantli, sacrifice, deities as enemies, feathered headdresses or costumes, faux-glyph fonts, pseudo-Nahuatl words, the word "Aztec" used as flavour, the tonalpohualli (sacred 260-day count) used as a score or seed label (it is still kept by living day-keepers, so it is not a game mechanic), or any "savage" framing. Spellings come from Nahuatl sources; when in doubt, use the plain English word.

**Future:** the owner wants, when he has more human help, to work with people from the cultures themselves. Section 12 lists what a community advisor should review before this ships wider, and how the game is built so names, text and patterns can be swapped without code changes.

---

## 1. Shape of the thing

| | Mode 1: **Drop** | Mode 2: **Run** |
|---|---|---|
| Fantasy | Guide the olli down the carved step-fret wall into the court and through the stone ring | Roll through the canals of a lake city and keep away from Ahuizotl |
| Verb | Tilt the court, strike with the hip | Choose direction, turn early, escape |
| View | Portrait column that scrolls down with the ball | Whole labyrinth on one screen |
| Level ends with | Ring challenge (tlachtemalacatl), 5 variants | The Reach: gate opens, Ahuizotl hunts, 5 variants |
| Session | 1 to 4 minutes | 2 to 5 minutes |

Both modes share: one seeded run of 5 levels, a speed curve, a pause screen, a result screen with score and run code, the same ball, the same carving style, the same accessibility settings.

The title screen shows the word **Ollamaliztli** with a one-line gloss: "The ballgame of Mesoamerica. Ōlli is the rubber ball." Two large buttons: **Drop** and **Run**. Under them: "Today's court" (default) or "New court", and a **Calm pace** switch.

---

## 2. Mode 1: Drop

### 2.1 Core loop

1. The ball rests at the top of a carved column of step-fret ledges. The player presses Space, taps, or clicks to **drop** it.
2. Gravity pulls it down. The player **tilts** the court left or right; the ball rolls along ledges and falls through gaps.
3. The player can **hip strike** (Space or tap) when the ball is touching or within a hair of a surface: a short bounce up and in the tilt direction. One strike per contact, with a 0.5 s cooldown. This is how you climb back out of a pocket and how you send the ball through the ring.
4. **Court markers** (small carved stone discs, like the markers set in real court floors) sit on some ledges. Rolling over one scores and adds 3 seconds.
5. At the bottom the column opens into the **tlachtli**, an I-shaped court seen from the side. The ring is set in one wall. Pass the ball through it to finish the level.
6. Next level: steeper, faster, longer, different layout, different ring.

Fail states: the level timer reaches zero, or the ball drops out of the court floor (the end zones of the I are open pits only on levels 4 and 5, marked with a stepped edge). Either one costs one of three **attempts** for the run; the level restarts from the top with the same seed.

### 2.2 Physics

All values are in logical units: playfield width is 360 units, the camera shows 360 x 640, and the canvas scales to fit.

- Ball radius 9. Restitution 0.62 on ledges (rubber, lively), 0.45 on walls. Rolling friction 0.985 per frame at 60 Hz, applied as `pow(f, dt*60)` so it is frame-rate independent.
- Fixed physics step of 1/120 s with an accumulator; render at display rate. Max 8 substeps per frame so a stalled tab does not spiral.
- Tilt is an input value from -1 to 1 that eases toward the held direction (time constant 0.08 s) and applies lateral acceleration `tiltAcc * tilt`. The court art rotates by up to 4 degrees with the tilt (0 degrees under reduced motion; a small chevron at the top shows the tilt instead).
- Hip strike impulse: up 330, sideways 160 x sign(tilt) (straight up if tilt is near zero). Shown by a short arc stroke on the ball's side (the hip contact), never a foot.
- Collision against axis-aligned segments only (the step-fret is all horizontals and verticals plus the hook corners), which keeps collision cheap and exact: circle versus segment with corner caps.

### 2.3 Level generation (the step-fret column)

A level is a stack of **rows** 72 units apart. Each row is a ledge drawn as a step-fret: a horizontal run that steps up or down in 12 unit risers and ends in a square hook at one end. Each row has one or two **gaps** wider than the ball.

Rules that keep every level solvable by construction:

- Gap width is at least 2.6 ball diameters on level 1, narrowing to 2.0 on level 5.
- The horizontal distance between a row's nearest gap and the next row's gap is at most `reach(L)`, computed from tilt acceleration and fall time between rows, then multiplied by 0.75 for margin.
- Hook ends never face a gap within 30 units (no pocket you cannot strike out of).
- Every fourth row is a **landing**: full-width with a central gap, so the camera has a calm beat.
- Markers sit only on ledge runs at least 60 units long, never on hooks.

Column length per level: 12, 16, 20, 24, 28 rows.

### 2.4 Ring challenges (the boss of each level)

The court is drawn side-on: floor, two end zones (the bars of the I), and walls rising on left and right. The **tlachtemalacatl** is a carved stone ring, mounted **vertically in the wall** as it was in real courts, so the ball passes through it sideways. The ball is struck through it with the hip, never thrown. A soft rule from the real game shapes difficulty: a ring pass was rare and decisive, so the ring is always hard and the level is won the moment the ball goes through.

The ring has an outer radius, an **aperture** (inner radius, always larger than the ball), and a pass test: the ball centre crosses the ring plane while inside the aperture, moving through it with horizontal speed over 60.

Each level has a fixed challenge **type**, and the boss seed changes its **parameters**, so level 3 is always "the turning ring" but never the same turning ring twice.

| Level | Challenge | What the seed varies |
|---|---|---|
| 1 | **The still ring.** Fixed on one wall. Teaches the strike-through. | Wall side, ring height (40 to 60% of wall), aperture 1.9 to 2.2 ball widths, one floor marker position |
| 2 | **The sliding ring.** Slides up and down its wall on a slow sine. | Side, centre height, amplitude 30 to 70 units, period 2.6 to 3.6 s, start phase |
| 3 | **The turning ring.** Turns on its vertical axis: it is passable when it faces you (drawn as a full circle) and blocked when edge-on (drawn as a thin bar). The open window is shown by a carved notch on the floor that fills as the ring opens. | Side, height, turn period 3.0 to 4.2 s, open fraction 35 to 45%, start phase |
| 4 | **The paired rings.** One ring on each wall. Only one is **live** (solid white stone with a hard outline); the other is **sleeping** (outline only). They swap on a steady rhythm, never faster than once per 2 s, and the next swap is announced by a carved tick mark sweeping round the live ring like a clock hand. End zones become pits. | Both heights, swap period 2.4 to 3.4 s, which ring starts live, aperture 1.8 to 2.0 |
| 5 | **The walking ring.** One ring moves along a slow path (a rounded rectangle or a figure-eight, seed chooses) across a tall wall, while the court walls **step inward** one fret at a time on a fixed cadence, narrowing the court. Aperture is smallest here. | Path shape, path size, speed 0.18 to 0.28 cycles per second, which wall steps first, step cadence 4 to 6 s, aperture 1.7 to 1.8 |

Ring timer: each ring challenge has its own short clock (25 s on level 1 down to 18 s on level 5). If it runs out, the attempt is spent and the ball returns to the court centre, not the top of the column; the column does not need replaying.

### 2.5 Speed curve (Drop)

| Level | Gravity | Tilt accel | Max fall speed | Column rows | Level time | Ring time |
|---|---|---|---|---|---|---|
| 1 | 820 | 620 | 520 | 12 | 60 s | 25 s |
| 2 | 900 | 660 | 560 | 16 | 66 s | 23 s |
| 3 | 990 | 700 | 600 | 20 | 72 s | 21 s |
| 4 | 1080 | 740 | 640 | 24 | 78 s | 20 s |
| 5 | 1180 | 780 | 680 | 28 | 84 s | 18 s |

**Calm pace** multiplies gravity, tilt and max speed by 0.7 and timers by 1.4, and ring motion periods by 1.4.

---

## 3. Mode 2: Run

### 3.1 Core loop

The playfield is the canal city: a grid labyrinth of **causeways** (paths) between **chinampas** (blocks, drawn as carved step-fret stone), seen from above. In the centre is a small square of open water: Ahuizotl's pool.

1. The ball rolls continuously along causeways in the current direction.
2. The player chooses the next direction at any time; the turn is **buffered** and happens at the next junction where it is possible (pre-turning, so play feels fluid and forgiving). The ball can reverse instantly at any time.
3. Collect every **cacao bean** on the causeways (cacao was valued and traded across Mesoamerica; it reads well as a small oval with a centre line).
4. Four **court markers** sit near the corners. Taking one makes Ahuizotl **return to its pool** and stay under the water for a few seconds. You cannot defeat Ahuizotl; you only keep your distance. (This replaces the Pac-Man "eat the ghost" idea, which would turn a creature of Nahua lore into prey and feels wrong.)
5. When all beans are taken, **the Reach** begins: a gate opens somewhere in the outer wall and Ahuizotl hunts with more intent. Leave through the gate to finish the level. This is the boss of the Run.
6. Caught: lose one of three lives (see 3.5).

**Water channels that change direction:** from level 3 on, some causeway segments carry a **current**, shown as small chevrons drawn inside the path. Rolling with a current is faster (x1.25), against it slower (x0.7). Currents reverse on a seeded rhythm, and every reversal is announced 1.5 s ahead by the chevrons turning hollow. This is the "can change direction" idea from the owner, layered on the player's own turning.

### 3.2 Labyrinth generation

Grid: 19 columns x 21 rows (odd sizes so walls and paths alternate cleanly). Tile size fits the shorter screen side.

1. Carve the **left half** with a seeded randomized depth-first walk on the coarse cell grid.
2. **Braid**: remove 75% of dead ends (level 1) down to 55% (level 5) by opening one wall each, so there are loops to run around; a labyrinth without loops is unfair in a chase.
3. **Mirror** to the right half. Real ballcourts and much Mesoamerican architecture are bilaterally symmetric; the symmetry also makes the board readable at a glance.
4. Stamp the 3 x 3 pool at the centre with one entrance, whose side is seeded.
5. **Wrap tunnels**: one or two horizontal rows open at both edges (seeded rows), as canals that pass under the city. The ball and Ahuizotl wrap; Ahuizotl moves through them at 0.6 speed (it is slower out of open water), which gives the player a known escape.
6. Validate with breadth-first search from the start tile: every path tile reachable, the start at least 8 tiles from the pool entrance, no corridor longer than 9 tiles without a junction. If a check fails, advance the maze sub-seed by one and regenerate. This is deterministic: the same run code always produces the same board.
7. Walls are drawn as step-fret blocks: each block's outline gets a stepped corner and, on blocks of 3 or more tiles, a hook. The hook direction is seeded per block, so boards look carved rather than tiled.

### 3.3 Ahuizotl: behaviour

Design goal: fair, readable, escalating. The player should always be able to say why they were caught.

**Look:** a low, dog-like silhouette, black fill with a hard white outline, small pointed ears, slick body (one clean highlight line), and a long tail that ends in a small open hand. Two small white eyes. It is drawn with respect and a little eerie calm, not as a cartoon monster: no teeth, no blood, no snarl. When it moves through the pool or a tunnel it shows only the hand-tipped tail and three short ripple lines.

**States:**

| State | What it does | How the player reads it |
|---|---|---|
| **Under** | Stays in its pool for a set time at level start and after a marker. | Only ripples visible; a thin ring around the pool closes like a clock to show time left. |
| **Follow** | Moves along paths toward where the player **was** a short moment ago (a trail lag). Picks, at each junction, the neighbour with the shortest path distance to that target, using a distance field rebuilt only when the target tile changes. It never reverses in a corridor, only at dead ends or junctions (the classic arcade rule, which makes it predictable). | Moves at a steady pace below the player's. |
| **Reach** | When it has a straight line of sight to the player within 4 tiles along a corridor, it stops, raises its **tail-hand** above its body (telegraph), then lunges along that corridor for up to 4 tiles at 1.35 x player speed. | The raised hand is the warning. Telegraph time is long and constant per level, and it is the only time it is faster than you. |
| **Rest** | After a lunge, it pauses for 0.8 s. | Hand lowered, body still. Your window to slip past. |

Fairness rules, always on:

- Outside a lunge, Ahuizotl is **slower than the player** at every level (see the curve).
- Hit test is generous: caught only if the centres are within 0.55 tile.
- It never spawns or resurfaces within 6 tiles of the player.
- After a catch, the player respawns at the start with 2 s of protection, shown as the ball drawn in outline only (no blinking).
- The lure (level 4 Reach) is always visually distinct from a real gate.

### 3.4 The Reach (the boss of each Run level)

When the last bean is taken, the gate opens and a short line appears: "The gate is open. Keep away from the water." Ahuizotl's trail lag drops and its speed rises (still below yours). Each level has a fixed Reach type; the boss seed varies its parameters.

| Level | The Reach | What the seed varies |
|---|---|---|
| 1 | **The gate.** One gate opens in the outer wall. | Which wall and position of the gate, which side Ahuizotl leaves the pool from |
| 2 | **Rising water.** Causeway segments flood one at a time. A segment about to flood shows ripple lines for 2 s first. Flooded segments are passable but slow you to 0.6 and speed Ahuizotl to 1.0 of base. | Gate position, flood order, flood interval 2.5 to 3.5 s, number of floods 4 to 6 |
| 3 | **Turning currents.** All currents on the board reverse together at the start of the Reach, then on a seeded rhythm. | Gate position, which segments carry currents, reversal period 4 to 6 s |
| 4 | **The call.** Two openings appear. One is the gate (a carved step-fret frame); the other is a **lure**, drawn as an opening with ripple rings. Entering the lure costs nothing but turns you back and Ahuizotl turns toward you. This echoes the Nahua accounts of Ahuizotl drawing people to the water's edge with a sound like crying. Caption on first sight: "Not every opening is a way out." | Positions of gate and lure, which is nearer the player |
| 5 | **Night canal.** The board is lit only within a hard-edged circle around the ball (radius 5 tiles); outside it the walls are hidden but beans already taken and the gate frame remain visible as single white lines. No soft falloff, no blur: a crisp edge. Ahuizotl's raised hand is always drawn, even outside the light. Currents and one flood wave also apply. | Gate position, current layout, flood order, light radius 4.5 to 5.5 tiles |

### 3.5 Speed curve (Run)

Speeds in tiles per second.

| Level | Player | Ahuizotl (Follow) | Ratio | Trail lag | Telegraph | Under time | Marker time | Dead ends removed |
|---|---|---|---|---|---|---|---|---|
| 1 | 6.0 | 4.7 | 0.78 | 1.2 s | 0.75 s | 4 s | 7 s | 75% |
| 2 | 6.4 | 5.4 | 0.84 | 1.0 s | 0.70 s | 3.5 s | 6 s | 70% |
| 3 | 6.8 | 6.0 | 0.88 | 0.8 s | 0.62 s | 3 s | 5.5 s | 65% |
| 4 | 7.2 | 6.6 | 0.92 | 0.6 s | 0.56 s | 2.5 s | 5 s | 60% |
| 5 | 7.6 | 7.2 | 0.95 | 0.45 s | 0.50 s | 2 s | 4.5 s | 55% |

During the Reach, ratio rises by 0.03 and trail lag drops by 0.15 s (never below 0.3 s). **Calm pace** multiplies both speeds by 0.7 and all telegraph and warning times by 1.4.

Three lives per run. Lose all three: result screen.

---

## 4. Seeding

Deterministic everywhere. The same run code reproduces the same boards, the same rings and the same Ahuizotl decisions given the same inputs. There is no `Math.random()` in game logic (only for choosing a "New court" code).

**Run seed:** a 32-bit integer.

- "Today's court" (default): hash of the local date string `YYYY-MM-DD` plus the mode letter. Everyone gets the same court each day, so people can compare.
- "New court": a random 32-bit value.
- Shown on the pause and result screens as a short code of 6 characters from an unambiguous alphabet (`23456789ABCDEFGHJKMNPQRSTUVWXYZ`, no 0/O/1/I/L), for example `K7Q-4MX`. A URL hash `#olli=K7Q4MX` or the code field on the title screen replays it.

**Streams:** each consumer gets its own seed so changing one generator never shifts another.

```
mix(a, b)        = splitmix32-style avalanche of (a ^ (b * 0x9E3779B9))
levelSeed(L)     = mix(runSeed, L)
mazeSeed(L)      = mix(levelSeed(L), 0x4D41)   // board or column layout
bossSeed(L)      = mix(levelSeed(L), 0xB055)   // ring or Reach parameters
currentSeed(L)   = mix(levelSeed(L), 0xC0A1)   // currents, floods
creatureSeed(L)  = mix(levelSeed(L), 0xA417)   // tie-breaks in Ahuizotl junction choice
artSeed(L)       = mix(levelSeed(L), 0xF4E7)   // hook directions, ornament only
rng(seed)        = mulberry32(seed)
```

Ahuizotl's path choice is deterministic; the creature stream is used only to break ties between equal-distance neighbours, so replays match exactly.

Retrying a level after a failure uses the **same** level seed (learnable). A new run with "New court" changes everything.

---

## 5. Controls

| Action | Keyboard | Touch | Mouse |
|---|---|---|---|
| Drop: tilt | Left/Right, A/D | Hold left or right half of the screen (or drag horizontally) | Pointer x relative to centre while the button is held, or hold left/right half |
| Drop: drop ball, hip strike | Space, W, Up | Tap with a second finger, or the on-screen **Strike** button (bottom centre, 64 px) | Click (right-click also strikes) |
| Run: direction | Arrows, WASD | Swipe (threshold 18 px, direction by dominant axis); optional on-screen pad (setting) | Click a point on the board: the ball turns toward it at the next junction |
| Pause / resume | P, Escape | Pause button (top right, 44 px) | Pause button |
| Restart level | R (on pause or result screens only) | Button | Button |
| Close the game | Escape on the pause screen, or the Close button | Close button | Close button |

All on-screen buttons are real `<button>` elements over the canvas, at least 44 x 44 CSS px. Touch uses Pointer Events with `touch-action: none` on the canvas only, so the page behind does not scroll while playing.

Input is read into a small state object each step; no game logic runs inside event handlers.

---

## 6. Scoring and results

**Drop**

- Court marker: 100
- Level clear: 1000 x level
- Time bonus: 20 per remaining second of level time
- Ring pass: 2500 x level. A pass with the ring's aperture under 1.8 ball widths, or through a moving ring, adds the label "A rare pass." (In the real game a ring pass was rare enough to end the match, so it is the biggest number on the board.)
- Unused attempts at run end: 1500 each

**Run**

- Cacao bean: 10
- Court marker: 50
- Level clear: 1000 x level
- Reach time bonus: 30 per second under the target time (20 s on level 1 down to 12 s on level 5)
- Clean level (no catch): x1.5 on that level's total
- Remaining lives at run end: 2000 each

The result screen shows: mode, total score, the level reached, the run code, best score for this mode (stored with `localStorage` inside try/catch; if storage fails the game still works and simply shows no best), and buttons **Play again**, **Replay this court**, **Other mode**, **Close**.

No leaderboard, no network, no tracking. This is an offline product's easter egg.

---

## 7. Failure and restart

- Every failure stops play immediately and shows one calm line of why: "Time ran out." "The ball left the court." "Ahuizotl reached you." Then a short beat (0.8 s, skipped under reduced motion) and the level resumes from its start with the same seed.
- Losing the last attempt or life shows the result screen.
- Never a game-over shout, a red flash or a skull. Black screen, white text, the ball resting.

---

## 8. Visual language

**Palette:** `#000` background, everywhere. Foreground ramp: `#ffffff` (ball highlight, live elements, text), `#e6e6e6` (primary carving), `#b8b8b8` (secondary carving, inner lines), `#8c8c8c` (inactive or past). Nothing darker than `#8c8c8c` is used for anything the player must see, because the owner's display lifts near-black and dim greys mush. No broad gradients, no grain, no blur, no glow halos. The one exception is the ball's highlight, a small radial gradient confined to the ball's own 9 unit radius.

**Carving style:** every wall and ledge uses the hero band's language: a step-fret drawn as a **double line**, outer stroke `#e6e6e6` at 1.5 CSS px, inner stroke `#b8b8b8` at 1 CSS px, 3 units inside, so it reads as cut stone with a lip. Fills are pure black. Lines snap to half device pixels for crispness at devicePixelRatio 1 and 2 (`ctx.setTransform(dpr,0,0,dpr,0,0)` and `+0.5` offsets on odd widths).

**The ball (ōlli):** a white disc with a crisp darker rim (`#b8b8b8`, 1 px) and a small offset highlight. It reads as the chrome of the site and as raw latex at once. Rolling is shown by one short arc on its face that rotates with distance travelled (disabled under reduced motion).

**Ring:** a thick carved annulus with eight short radial cuts, like a stone ring. Live: solid `#ffffff` with the double outline. Sleeping (level 4): outline only, `#8c8c8c`.

**Water (Run):** never a fill or gradient. Water is three or four short horizontal hairlines per tile that drift by one unit per second (static under reduced motion).

**Ahuizotl:** see 3.3. Outline `#ffffff`, fill `#000`, eyes `#ffffff`.

**Type:** inherit the site's self-hosted fonts when mounted on zotheos.org (the host passes its font family through a CSS custom property `--zth-game-font`); fall back to `system-ui, sans-serif`. Title in letter-spaced capitals, body at 15 to 16 CSS px minimum. No decorative "Aztec" fonts.

**Motion:** transitions are cuts or short fades (150 ms). Nothing pulses faster than 2 per second. Ring rhythm changes are drawn as a sweeping tick, never a blink.

**Layout:**

- 390 x 844 phone: Drop fills the width (360 logical units scaled to about 358 CSS px with a 16 px gutter); Run tiles are about 18 CSS px. HUD is a single top row: level, score, time or lives, pause.
- 1600 x 993 desktop: Drop column is centred at 993 px tall (scale about 1.5), the side areas show the level's step-fret pattern as a static carved frame and the seed code; Run board is centred and fits the height.
- Canvas backing store is `cssSize * min(devicePixelRatio, 2)`. Resize is handled on `resize` with a 100 ms debounce.

---

## 9. Opening from the left band

**The trigger:** on the left Xicalcoliuhqui band of the hero, one step of the fret carries a small resting ball, the same white disc as the game's ōlli, about 10 px. It is a real `<button>` with `aria-label="Play ollamaliztli, the ballgame"` and a visible focus ring. It is an easter egg: quiet, but reachable by keyboard and screen readers, never hidden from them.

**The hand-off:**

1. On activation, the site's band animation lets the ball **roll down the steps** of the band (about 500 ms, following the step path that already exists in the band geometry).
2. As it reaches the bottom of the visible band, the overlay opens from the left edge: a black layer slides in 0 to 100% width over 220 ms, and the Drop column's first rows are drawn so they line up with the band's step pattern. The band becomes the maze.
3. The title screen appears with focus on the **Drop** button.

Under `prefers-reduced-motion: reduce`, steps 1 and 2 are replaced by an instant cut to the title screen.

**Lazy loading:** nothing of the game exists on page load except the button. On first activation the site creates the overlay `<iframe src="/game/index.html">` (or injects the script) and calls `ZTH_GAME.open()` once it has loaded. Inside the game file, no animation loop, no listeners and no canvas exist until `open()` is called.

### 9.1 API

```js
window.ZTH_GAME = {
  version: "1.0.0",
  open: function (mode, opts) {},  // mode: "drop" | "run" | undefined (title screen)
                                   // opts: { seed: "K7Q4MX", calm: true, returnFocus: el }
  close: function () {},           // stops the loop, removes every listener, clears the canvas,
                                   // returns focus to opts.returnFocus, fires onClose
  isOpen: function () {},          // boolean
  onClose: null,                   // optional callback set by the host
  onSound: null                    // audio hook, see below
};
```

`close()` must leave nothing running: cancel the `requestAnimationFrame`, remove keyboard, pointer, resize, `visibilitychange` and `blur` listeners, and drop references to large arrays. `open()` after `close()` starts fresh. When the tab is hidden or the window loses focus, the game pauses itself.

**Audio hook (no audio now):** the game calls `ZTH_GAME.onSound(name, data)` if the host has set it. Names: `drop`, `bounce` (data: impact speed 0 to 1), `strike`, `marker`, `ring-pass`, `ring-miss`, `bean`, `gate-open`, `current-turn`, `ahuizotl-rise` (the telegraph), `caught`, `level-clear`, `run-end`, `pause`, `resume`. The owner will design the sound himself; the game never ships sound files.

---

## 10. Text in the game

All short, plain, no em dash.

- Title: **Ollamaliztli**
- Gloss: "The ballgame of Mesoamerica. Ōlli is the rubber ball."
- Drop description: "Guide the ōlli down the carved wall and strike it through the stone ring."
- Run description: "Roll through the canals, gather the cacao, and keep away from Ahuizotl."
- First ring: "Strike with the hip. In the old game, a ring pass was rare and decisive."
- Ahuizotl first sight: "Ahuizotl, the water creature of Nahua accounts. It reaches with the hand on its tail."
- Pause: "Paused." Buttons: Resume, Restart level, Calm pace, Close.
- About (one screen, from the pause menu):
  - "Ōllamalīztli is the Nahuatl name for the Mesoamerican ballgame, played for more than three thousand years from Mexico to Central America, with courts as far north as present-day Arizona."
  - "Ulama, its descendant, is still played today in Sinaloa, Mexico."
  - "The step-fret, xicalcoliuhqui, is carved and woven from Oaxaca to the Pueblos of the Southwest."
  - "Ahuizotl is described by Nahua scholars in Book 11 of the Florentine Codex."

---

## 11. Accessibility

- **Focus:** the overlay is a modal dialog (`role="dialog"`, `aria-modal="true"`, labelled by the title). Focus is trapped inside while open and returned to the band button on close. Start, Pause and Close are always real buttons with visible focus outlines (2 px white, 2 px offset).
- **Screen readers:** the canvas has `role="img"` and an `aria-label` that names the mode. A visually hidden `aria-live="polite"` region announces only events, never per frame: level start ("Level 3 of 5. The turning ring."), ring pass, catch, lives left, level clear, result. Score is read on pause and result screens.
- **Reduced motion:** if `prefers-reduced-motion: reduce`, **Calm pace** starts on, the court does not rotate with tilt, the ball's rolling arc and water drift are static, intro and failure beats are cut, and camera follows with no easing overshoot. The player can still switch Calm pace off.
- **No flashing:** nothing changes brightness more than 2 times per second anywhere. Ring swaps, current reversals and warnings use shape changes (outline to fill, chevron to hollow chevron, a raised hand), never blinking.
- **Readable:** text at least 15 CSS px, contrast white on black. No information carried by grey level alone: live versus sleeping ring is also fill versus outline; currents are also chevron direction.
- **Motor:** every action has a keyboard path; no simultaneous key chords required; buffered turns in Run; generous hit tests; Calm pace slows everything. An **Assist** setting (pause menu) gives Drop unlimited attempts and Run unlimited lives; scores in Assist are shown but not saved as best.
- **Timeouts:** the game auto-pauses on tab hide and window blur, so nobody loses a run to a notification.

---

## 12. For a future cultural advisor

The owner wants this to grow, with real people from the cultures, into something that honours many traditions accurately. To make that easy:

- All visible text lives in one `TEXT` object at the top of the file, so wording and spellings can be changed without touching game code.
- All Nahuatl terms are listed in one `TERMS` object with the spelling used, a plain gloss and the source. Today: ōllamalīztli, ōlli, tlachtli, tlachtemalacatl, xicalcoliuhqui, āhuitzotl, chinampa, cacao (cacahuatl).
- The step-fret carving is generated from one `FRET` description (step count, step size, hook shape), so a different regional pattern (for example a Pueblo or Zapotec variant chosen with a community advisor) can be added as data.

Questions to put to an advisor before a wider release:

1. Is a game about Ahuizotl, framed as the danger of the water, acceptable and respectful to Nahua and Mexican audiences today?
2. Spelling and diacritics: ōllamalīztli versus ullamaliztli in visible text.
3. Should the game link to or name living ulama players and organizations in Sinaloa (with their consent), and could some recognition or support flow back to them?
4. Is cacao an appropriate collectible, or is there a better, more neutral item?
5. Is there any use of the step-fret here that a particular community considers restricted?

---

## 13. Build budget and structure

Target: under 30 KB of unminified-but-tight JS, under 6 KB of CSS and HTML.

| Part | Budget |
|---|---|
| Core: loop, fixed step, input, resize, dpr, pause, API, a11y live region, storage | 6 KB |
| Seeds and RNG (mix, mulberry32, code encode/decode) | 1 KB |
| Shared drawing: fret stroke, ball, text, HUD | 3 KB |
| Drop: physics, column generator, camera, markers | 6 KB |
| Drop: five ring challenges | 3 KB |
| Run: maze generator, braid, mirror, validate, distance field | 5 KB |
| Run: player movement, currents, Ahuizotl states, the five Reaches | 5 KB |
| Text, terms, screens | 1 KB |

Rules: ES5 only (`var`, function declarations, no arrow functions, no classes, no template literals, no `let`/`const`), no `Map`/`Set` needed, typed arrays allowed (`Uint8Array`, `Int16Array` are ES5-era in practice and widely supported) for the grid and distance field.

---

## 14. Test checklist

- Same run code produces identical boards, rings and Ahuizotl paths across reloads (log a hash of each generated level).
- 500 seeds per level: Drop columns pass the reach check; Run mazes pass BFS validation with no regeneration loop longer than 5 tries.
- 60 Hz and 144 Hz displays give the same physics (fixed step).
- 390 x 844 touch and 1600 x 993 mouse and keyboard both playable end to end.
- `close()` mid-level: no rAF callbacks, no listeners left (check with a counter in dev builds).
- Reduced motion on: no court rotation, no drift, Calm pace on by default.
- Nothing changes brightness faster than 2 per second (inspect the ring swap, current flip, telegraph, protected respawn).
- Search the file for the em dash character: zero results.
- Text read by a screen reader at level start, catch, clear and result.

---

### Sources consulted

- Ahuizotl (mythology), Wikipedia, quoting Florentine Codex Book 11: https://en.wikipedia.org/wiki/Ahuizotl_(mythology)
- Florentine Codex glyph entry for ahuitzotl, Book 11 f.71r, Aztec Glyphs database: https://aztecglyphs.wired-humanities.org/content/ahuitzotl-fcbk11f71r
- The Ulama ballgame: past, present, and future, Material Intelligence: https://www.materialintelligencemag.org/rubber-collection/the-ulama-ballgame-past-present-and-future
- How a 3,400-year-old ballgame survives in Mexico against all odds (AP via WTOP, May 2026): https://wtop.com/lifestyle/2026/05/how-a-3400-year-old-ballgame-survives-in-mexico-against-all-odds/
- Rubber and morning glory processing (Hosler, Burkett and Tarkanian, Science 1999), summarized at Geo-Mexico: https://geo-mexico.com/?p=450

Not independently confirmed in this pass and kept out of the game text: claims from secondary sources that Ahuizotl takes eyes, teeth and nails. The tlachtemalacatl ring details come from general archaeological knowledge and should be confirmed by the advisor.
