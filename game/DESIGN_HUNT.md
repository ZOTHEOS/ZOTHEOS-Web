# ECHO: the chase mode of Ollamaliztli (Revision 2.0)

Status: final design for build, 2026-10-09. Replaces Mode 2 (Run) in DESIGN.md section 3. Where this file and DESIGN.md disagree about the chase mode, the nations layer or the About text, this file wins. **Drop is unchanged** in gameplay, physics, levels, rings, controls and text; the only shell changes it sees are listed in section 1.4.

Built from the judges' combined verdict (Echo won two of three panels and had the highest total, 124 against 108, 107 and 102). It includes grafts from Mask, Dark Court and Fret, and it fixes every fatal flaw the judges named (traceability in section 25).

Writing rule kept: no em dash or en dash anywhere, in this file or in any visible string. Ranges are written "9 to 11 s".

> **Revision 2.2 (presence pass, 2026-10-11).** Where this note and any section below disagree, this note wins. Version `2.2.0`. Every change is render only: the game logic, sound hooks, nations layer and Drop are untouched (flows pass, 100 bot runs with 0 assert failures, and the determinism hashes of all five levels are identical before and after).
> - **Camera (replaces 16.1 "Tile size" and "Camera").** A close follow view. The short side of the view holds about 8 tiles on a landscape screen and 7 on a portrait phone; the long side caps it at 13 and 12. The tile is a whole number of device pixels, clamped to 24 to 150 CSS px. Measured: 1600 x 993 at 1.25x gets a 111 CSS px tile and shows 13.0 x 8.1 tiles (also at 1x); 390 x 844 at 2x gets 51 px and shows 7.0 x 13.9 tiles (the width sets it). The view follows you with a dead zone of 0.07 of the view either side on each axis and a lead toward the way you move, up to 1.6 tiles (at most 0.16 of the view), eased over 0.35 s; the centre eases over 0.12 s. Both run on real time in the drawing code, never in the game logic. The lead shrinks with the terror band (x1, 1, 0.8, 0.5, 0.3) so the Stone Face stays in view behind a fleeing player; there is no lead under reduced motion; on touch portrait you sit 8% of the view above the centre, clear of the thumbs. The view is clamped to the board plus one tile and snaps, with no pan, on a new level, a resize or a turn back. Its offset is rounded to whole device pixels: on six consecutive frame pairs with the camera moving 9 to 11 device px a frame, the picture is the previous frame shifted by whole pixels, with 0 differing pixels outside the moving bodies and the screen-space overlays.
> - **Layout (replaces 16.1 "View" and "Caption strip").** The view spans the window less two band gutters of 9.5 band units (a unit is the window's short side / 125 device px, at least 3), from the HUD to a 44 px caption strip under it (84 px under the view on portrait). Captions no longer use the left gutter, so both carved bands always show, and they are fixed in screen space (they no longer scroll with the view). Under 700 px wide and on portrait, 16 px margins and no bands. HUD, captions, bands and the nation card stay in screen space.
> - **Scale (replaces W = 1.5 tiles in 11.1 and the sizes in 16.2 item 9).** The Stone Face is 1 tile wide: 111 CSS px tall on the 1600 x 993 window (was about 78 at the whole-board zoom), 51 px on the phone. It reads larger on screen, and with the heavier walls below it still nearly fills a passage. Your yoke radius is 0.18 tile and at least 11 CSS px (40 px across on the desktop, 22 on the phone; was 30), the head disc 0.57 of it, its stroke 0.13 of it. The ōlli radius is 0.12 tile and at least 6 px (27 and 12 px across). Line weights: seen walls are grooves of half-width 0.35 tile (was 0.2) with lines of max(1.4 CSS px, T / 70), so at this zoom the seen stone reads as solid carved blocks, the passage between two walls is 1.3 tiles wide on screen (the face, 1.06 tiles wide, nearly fills it) and the drawn stone sits close to where bodies actually stop; the face outline is max(1.5 CSS px, W / 50), its features max(1 px, W / 80), the closed lids W / 60.
> - **The face (changes to the `FACE` data in 11.1, for a harder stare at rest).** The brow ledge is one solid carved bar from y -0.24 to -0.205 (was two thin rules). The eye almond is hooded under it: inner (0.07, -0.085), outer (0.31, -0.12), up (0.19, -0.165), lo (0.19, -0.02). The obsidian pupils are 0.05, 0.042, 0.032 and 0.023 W (was 0.034 to 0.018), so the resting stare is dark, and they still shrink in three hard steps; offset 0.05 and 0.012 W. The open mouth shows 7 square shell teeth of 0.026 x 0.032 W on each lip (was 11 of 0.018 x 0.02); lips at 0.245 and 0.29, the open lower lip at 0.345. The glint is at most 0.45 of the pupil radius. Still an original Teotihuacan-craft reading: no fangs, no goggles, no deity markers. The edge-on slab, the three-quarter turn (s = 0.71) and the full face read as three distinct shapes at the new size.
> - **Eyes through the dark (adds to 8.4 and 11.5).** Drawn at 1.3 times the face scale and full width, each shell in a hard white rim (the 1.18 socket almond, stroked at twice the carved line): the brightest mark on the screen (measured: 978 pure white pixels against 391 for your yoke and 4 for the ball, whose shading peaks below white). Its sight reaches 12 to 14 tiles and the view's half-width is about 6.5, so when it sees you from beyond the view the eyes stand just inside the view's edge, toward it: rule 2 holds at any zoom.
> - **Terror brackets (replaces 16.2 item 11's drawing).** Four corner stairs close in from the view's corners: band + 1 steps of 0.055 of the view's short side (62 device px at 1600 x 993 at 1.25x, so a reach of 62 px at band 0 to 310 px at band 4). The stone they cover is solid black and their edge is the carved double line: darkness and light with hard edges, a change of shape and never of brightness. Bands, thresholds, hysteresis, the 0.6 s hold and `terror {band}` are unchanged; with the mouth opening on the teeth in a rush, they are the fear in motion.
> - **Edge markers (replaces 16.2 item 12's markers).** A chevron just inside the view's edge points at what lies beyond it, behind a square for an unclaimed court or a circle for the ball's last known place. In the finale the Great Court's marker is white at twice the line weight, so the Great Ring stays easy to find off view. Marker size max(6, min(10, T / 9)) CSS px.
> - **Pause.** The whole board as memory lines (every remembered wall, #8c8c8c), claimed courts as white squares and you as a white disc, fitted above the pause panel, whose words move to the bottom. A window too short for it (under 5 CSS px a tile) keeps the solid panel. Captions clear on pause.
> - **Budget and build.** 91 989 bytes of minified JS, 40 591 gzipped (2.1 was 90 444), under the 92 000 budget. To fit: an unused generator helper and the captions-in-gutter case for very wide windows (which now simply show more tiles across) were removed, and line-join settings that were already the canvas default were dropped. `build.py` now writes LF on every platform. The `/game` CSP hashes in `vercel.json` follow the build; a run under those headers shows 0 `securitypolicyviolation` events.
> - **Performance.** 4x CPU slowdown, level 1 and a busy level 5 chase: 60 fps at 1600 x 993 (1.25x and 1x) and 390 x 844 (2x), game script 0.5 to 0.8 ms median a frame and under 3 ms worst. No arrays or objects are created per frame (a sampling heap profile over 600 draws: 17.9 KB, against 16.3 KB for 2.1, all number boxing in canvas calls).
> - **Not validated by bots:** the feel of the lead and dead zone on hardware, the bracket sizes on the owner's display, thumb comfort on a phone.

---

## 0. The ten rules (the contract every other section serves)

1. **Hips, never hands.** You cannot carry the ōlli. You move it with soft hip touches (the dribble) and hip strikes. Every knock of the ball on stone lights the stone around it for half a second and is heard along the corridors.
2. **If you can see its eyes, it can see you.** The Stone Face's two shell eyes are drawn through any darkness exactly while it sees you, and only then (with a 0.5 s debounce so they never flicker). While they show, its notice fills. Its obsidian pupils turn toward you and shrink in three hard steps. It can hunt you only after a full notice that took at least the level's notice time (0.75 s on level 1, 0.50 s on level 5).
3. **The step-fret is the escape.** On a straight it is faster than you (x1.14 to x1.20). At every 90 degree turn it stops to turn its stone face (0.32 s to 0.22 s). Straight corridors are capped at 7 tiles. A chase ramp, corner learning and a loop reversal end endless loops.
4. **Claimed courts are safe ground.** Strike the ōlli through a court's stone ring to claim it. The Stone Face never enters a claimed court. It waits at the mouth for a few seconds (4.0 s to 2.5 s), then leaves.
5. **The Great Ring finale.** When every side ring is claimed, the Great Ring wakes. It is Drop's ring of the same level, seen from above: still, sliding, turning, paired, walking. The claimed rings then fall silent one by one, and a silent court is no longer safe. Pass the ōlli through the Great Ring to clear the level. If every ring falls silent first, you lose an attempt.
6. **Two touches.** The first touch only marks you. The second turns you back: you lose one of three attempts and return to your last claimed court with 3 s of protection. The Stone Face is set back at its post, never within 6 path tiles of you and never in your sight.
7. **Make it play.** Strike the ōlli into the Stone Face at 3 tiles/s or faster and it must stop and play the ball back toward your last claimed court, travelling at most about 7 tiles. This works once every 4 s. It is never defeated, hurt or chased.
8. **Seeded and fair.** Five levels, each with a fixed trial whose parameters are seeded, plus a seeded temperament. Court codes replay exactly, and Today's court uses the letter E. Game logic uses no trigonometry and no Math.random.
9. **Crisp darkness.** Visibility is per tile with a stepped, fret-like edge. Memory is single grey lines and the unknown is pure black. There are no gradients, glows, fog, grain, blur or vignettes. Nothing changes brightness more than twice a second.
10. **Nations never touch the hunter.** Indigenous nations of today appear only on calm static screens: the title herald (with a Pause control), the card between levels (the next trial is named only after Continue), About, and the result of a won run. The source and checked date are always visible. If the data fails, nothing is shown.

---

## 1. Name, title copy, what changes

### 1.1 Names

| Thing | Visible name | Notes |
|---|---|---|
| Mode | **Echo** | Title button text ECHO, beside DROP. Plain English. The fantasy: you see by the knocks you make. |
| Pursuer | **the Stone Face** | Used in full in every caption. Described once as "a stone mask that no one wears". Its role, in English only: it keeps the labyrinth. |
| Nahuatl word note | **xāyacatl**, "face; mask" | Appears only in About and TERMS, never as a creature name. Sources in section 28. |
| Torches of the lit courts | **ocote** (from Nahuatl **ocotl**) | Appears only in About and TERMS. |

No compound Nahuatl words are coined anywhere. The mode has no Nahuatl name, because any compound we built would be pseudo-Nahuatl.

### 1.2 Title-screen mode buttons (exact)

- **DROP**: "Guide the ōlli down the carved wall and strike it through the stone ring." (unchanged)
- **ECHO**: "Strike the ōlli to see the dark. The Stone Face hears every knock."
  - Second line, smaller (`.sub`, inside the same button): "A tense chase in the dark. No gore."

### 1.3 Removed with Run

All of Run goes: `R_new`, `maze` (mirrored), `trails`, `currents`, `floodGroup`, `far`, `R_reset`, `R_step`, `pArrive`, `aArrive`, `R_lay`, `R_board`, `R_draw`, `ahu`, `RPAR`, the `C`/`RW` constants and `runbot.js`. TERMS loses `ahuizotl`, `chinampa` and `cacao`. TEXT loses `run`, `runDesc`, `firstAhu`, `gate`, `gateL`, `tw`, `runHint`, `runTouch`, `runLv` and About line 4. Kept from the Run section because Echo reuses them: `bfs` (generalized to a width and height), `nb`, `deg`, `repair` (made non-mirrored), `chev` (edge markers) and `gateArt` (the Entry niche). Removed as well: `setDir`, `move` and the pre-turn cornering (no grid-locked movement), and `water`.

### 1.4 Shell changes (the only ones Drop sees)

- `ZTH_GAME.open('echo')` is new. `open('run')` maps to `'echo'` so old host links keep working. The version becomes `2.0.0`.
- Title: the button `Mr` becomes `Me` (Echo). The nations herald is added at the bottom of the title panel (section 19).
- Between levels, in both modes: when nations data has loaded and `opts.nationCards !== false`, the 1.6 s level-clear beat is followed by the nation card panel with a Continue button. Without data, both modes behave exactly as now.
- The result screen of a **won** run lists the nations met in the run (section 19.4).
- About gains the Stone Face lines, the word notes, the nations section and credits (section 20).
- The pause screen gains a **Close-up** switch, shown in Echo only.
- "Other mode" toggles Drop and Echo. Best score keys: `zth_olli_best_drop` (unchanged) and `zth_olli_best_echo`.

---

## 2. Pitch, and why this is neither Pac-Man nor Dead by Daylight

**Pitch.** It is night in a labyrinth of stone ballcourts. You have one rubber ball and almost no light: you see about three tiles around you, and the edge of what you see is stepped like the fret. You cannot carry the ball, because nobody touched the ōlli with their hands. You can only touch it with your hip. Every time it knocks against stone, the walls around the knock appear for a moment, and a crisp line of sound runs away from it along the corridors. That is how you see. Everything that knocks is heard by the Stone Face: a broad stone mask covered in mosaic, with shell eyes and obsidian pupils and nothing behind it. It is wider than the corridors. Strike the ball through the stone rings to claim the courts. A claimed court is yours, and the Stone Face will not step inside it. Claim them all and the Great Ring wakes. Make the last pass while the courts fall silent, and the Stone Face closes its eyes and lets you pass.

So the ball is, at once, your **light** (knocks reveal), your **noise** (knocks are heard), your **decoy** (send it rattling down a far corridor), your **key** (ring passes), your **exit** (the Great Ring pass) and your **shield** (strike it into the Stone Face and it has to play it).

| Pac-Man | Echo |
|---|---|
| Eat every pellet | Nothing to eat. 2 to 4 skill shots per level with a bouncing ball, then one decisive pass. |
| Whole symmetric maze on screen | An asymmetric labyrinth, never mirrored, larger than the screen, dark except what you light by knocking or walk past. |
| Tile-locked runner with buffered turns | Free 8-way and analog movement, plus a second body (the ball) with real physics. |
| Ghosts on fixed target timers | One hunter with senses (sight cone, line of sight, hearing by path), memory, a readable face and a seeded temperament. |
| Power pellet turns the hunter into prey | Never. The most you can do is make it play the ball. |

| Dead by Daylight | Echo |
|---|---|
| Generators with skill-check bars | Mobile objectives: dribble the ball into a court and strike it through a ring. The ring pass was the rare, decisive moment of the real game. |
| The killer sees everything; survivors hear a heartbeat | Inverted. You are the near-blind one and make your own light by making noise. The Stone Face sees only down the corridor it faces, and listens. |
| Pallets and windows make loops | The carved step-fret is the loop: the hunter pays a pause at every turn. |
| Hooks, injury, sacrifice | None. The worst outcome is "The Stone Face turned you back." |
| Exit gates opened by levers | The exit is a ring pass under a falling silence, the most skilful act in ōllamalīztli. |
| Safe nowhere | You create safe ground: every claimed court. |
| Killer powers about harm | Trials drawn from stone and mosaic craft and from the court itself: loose tesserae, a face that turns on a rhythm, moving stones, a mosaic that gathers. |

---

## 3. Culture and framing (non-negotiable, read before the mechanics)

- **The Stone Face is a guardian, and the labyrinth is a trial.** It keeps the courts at night. It is an opponent in a game, the way the other side was in the ballgame. It returns the ball. When you make the last pass it closes its eyes and lets you pass.
- **Words never used for it:** evil, demon, monster, devil, god, spirit, cursed, haunted, kill, death, dead, sacrifice, Aztec. The game never says where it came from. There is no tomb, no curse, no museum object coming to life.
- **It is an original design.** It draws on the general craft of Teotihuacan stone masks (broad, flat, expressionless faces, not made to be worn), on Mesoamerican mosaic work, and on shell eyes with obsidian or pyrite pupils. It copies no object and no deity.
- **Nothing wears it.** There is no body, no column, no hands, no cords. From behind you see a hollow carved shell with two drilled ear holes.
- **Never on the Stone Face** (each item marks a specific deity, object or trope):
  - ringed "goggle" eyes, rings round the pupils, fangs or pointed teeth, a curl over the lip, water or cloud swirls (Tlaloc);
  - flayed skin, double lips, slit eyes over an open mouth, ties or cords at the back of the head (Xipe Totec);
  - horizontal face bands, a mirror at the temple or foot (Tezcatlipoca);
  - a skull or skeletal jaw, empty eye sockets, a mosaic skull, alternating turquoise and lignite bands;
  - an all-turquoise face with gold eyelids (Xiuhtecuhtli);
  - a beak or buccal mask, a cut-conch jewel (Ehecatl-Quetzalcoatl);
  - bells on the cheeks; a two-headed serpent nose ornament; ear spools or any ear ornament; feathers or a headdress; glyphs; jaguar or other animal traits; a toothless downturned mouth;
  - red, blood, gore, injury, a broken or shattered mask;
  - any copy of the Pakal mask, the Malinaltepec mask, the British Museum turquoise mask, or any living ceremonial or dance mask (for example the Parachico Patrón).
- **Shell whites are always filled.** Whenever an eye is drawn open, its almond is filled white. A closed eye is a single lid line, never an empty almond. The echo ghost (section 9.4) draws no eyes at all. This prevents the skull read on black.
- **Living mask traditions** are acknowledged in About in one line and are never imitated.
- **Nations of today never share a screen, a caption, a sound cue or a data path with the Stone Face** (section 19).
- All of the Stone Face's geometry lives in one `FACE` data object and all wording in `TEXT`, so an advisor-led redesign is a data change.

---

## 4. The loop and the first minute

### 4.1 Core loop (one level)

1. **Start** in the Entry niche on the bottom edge, the ōlli resting at your side. The Stone Face sleeps at its post near the centre for its wake time (eyes closed).
2. **Explore.** Walking is silent. Dribbling makes soft pats. Striking the ball down a corridor is loud and lights the stone at every knock.
3. **Find a court.** The outlines of all courts are known from the start (drawn as grey memory). A court is lit by ocote torches, so you can see into it along any line of sight up to 12 tiles. Lit also means the Stone Face sees across it from far.
4. **Line up.** Bring the ball into the court and strike it along the alley through the stone ring.
5. **Claim.** "Ring claimed. This court is safe ground." A ring pass is heard across the whole labyrinth, so the Stone Face is coming. The ball rolled on through the ring into the far end zone, so collect it inside your safe court and choose which mouth to leave by.
6. Repeat for every side ring. Then **the Great Ring wakes**, and the claimed rings begin to fall silent one by one.
7. **The last pass.** Bring the ball into the Great Court and pass it through the Great Ring. "The Stone Face lets you pass." Level clear.
8. Then, if nations data is loaded, the nation card. Continue. The next level starts and names its trial in the caption.

A level takes 70 to 120 s of good play on level 1 and 120 to 200 s on level 5. A full run takes 8 to 13 minutes.

### 4.2 The first sixty seconds of level 1

You stand in a stepped niche at the bottom of a black screen. Around you, a small pocket of carved stone, three or four tiles each way; where the light ends, a short grey crossbar closes each corridor. Far above, the grey outlines of the courts you have been shown. Caption: "Level 1 of 5. The stone face. It listens." Then: "Arrows or the mouse to walk. Space or click to strike. Hold Space to aim."

You walk. The ball rolls ahead of you with small pats. At a junction you strike it down the dark corridor to the left. It knocks off the far wall: for half a second the stone around each knock appears in full carving, then stays behind as grey memory. A crisp line runs away from the knock along the corridors and bends round a corner. That is your sound travelling. Caption: "Every knock lights the stone around it. Every knock is heard."

You follow the knocks to the ball and find a lit court: torch brackets on its end walls and a stone ring jutting from the alley wall. You dribble into the end zone, and the aim line passes through the slot, which turns solid. Strike. The ball threads the ring and the ring turns white. "Ring claimed. This court is safe ground."

The sound of the pass runs out through every corridor. Somewhere it passes something: for a moment, a frozen grey outline of a broad face, where the sound touched it. The step-fret brackets in the corners of the view step inward. Then again. Out past the court mouth, in total black, two white almonds with dark pupils appear. "The Stone Face. If you can see its eyes, it can see you." The pupils jump toward you and get smaller. You step back into the court. It comes to the mouth, too wide for the passage, and stares in. It does not enter. After four seconds it turns edge-on, a thin slab, and glides away.

---

## 5. World, units and seeds

- **Tiles.** The labyrinth is an odd-sized grid of square tiles (sizes in section 13). Tile (i, j) covers [i - 0.5, i + 0.5] x [j - 0.5, j + 0.5] in world units, with its centre at (i, j), as in Run's `tileOf`. All speeds are in tiles per second.
- **Arrays** (allocated once for the largest board, 27 x 37 = 999 tiles, and reused every level):
  - `grid` Uint8Array: 0 wall, 1 floor, 2 slab (level 4).
  - `zone` Uint8Array: 0 corridor, 1 to 4 side court index, 8 Great Court, 9 the Stone Face's post, 10 Entry.
  - `mem` Uint8Array: 1 if the tile is remembered.
  - `vis` Uint16Array visibility stamps (a tile is visible when `vis[t] === visStamp`, so nothing is cleared per frame).
  - `lit` Int32Array: the step number until which a tile is knock-lit.
  - `fblk` Uint8Array: tiles the Stone Face may not enter (ring footprints, claimed courts).
  - `jpass` Uint8Array: your junction passes during the current chase (section 11.8).
  - Distance fields Int16Array: `DT` (the Stone Face's target), `DF` (from the Stone Face's own tile), 8 wave fields `WV[0..7]`, a scratch field, and one queue `BQ`.
- **Fixed step** 1/120 s with the existing accumulator (max 8 substeps per frame). All timers count in this step.
- **Seeds**, as DESIGN.md section 4:

```
levelSeed(L) = mix(runSeed, L + 1)
mazeSeed     = mix(levelSeed, 0x4D41)   // rooms, carve, braid, slabs; try t uses mix(mazeSeed, t)
bossSeed     = mix(levelSeed, 0xB055)   // trial parameters, temperament, Great Ring variant, wake time
faceSeed     = mix(levelSeed, 0xA417)   // patrol order, Listen cadence, tie-breaks
artSeed      = mix(levelSeed, 0xF4E7)   // mosaic net, lost tesserae, fret hook directions, ornament only
```

- Today's court: `today('E')`. Codes, the `#olli=` hash, New court and Replay this court work unchanged. `Math.random` is used only for New court.
- **No trigonometry in game logic.** Facing uses 8 literal unit vectors, aim rotation uses literal constants, friction uses a literal per-step factor, and ring motion uses polynomial waves. `Math.sqrt` is allowed (it is correctly rounded everywhere). `Math.sin`, `cos`, `atan2`, `pow`, `exp` and `log` appear only in drawing code and in render-only tables.

---

## 6. You

### 6.1 Body and movement

- Body: a circle of radius 0.28 tile. Collision against wall tiles (and closed slabs, and ring footprints) as axis-aligned boxes, resolved on x, then on y.
- **Corner slide:** if one axis is blocked and the overlap with the blocking tile is under 0.35 tile, you are moved toward the opening at full speed. Thumbs never snag on corners.
- Input gives a move vector m with |m| <= 1 (keyboard: 8 directions, diagonals use 0.7071067811865476; stick: analog; mouse: toward the pointer). Velocity = m x speed, with no acceleration ramp.
- Speed: **walk** speed from the table (3.6 to 4.4). While the ball is under dribble control (6.2): x0.85. While marked, for 1.2 s after the first touch: x1.4.
- Facing: the last nonzero move direction, as a unit vector. It is the default aim.
- Walking makes no sound.

### 6.2 The dribble (hip touches)

The ball is **under control** when all of these hold:
- you are moving (|m| > 0.2);
- the ball centre is within 0.75 tile of yours;
- the dot product of your move direction and the direction from you to the ball is at least 0.2;
- the ball's speed is at most 1.6 x your speed (so a struck ball flying past is not captured).

Under control, each step: target point P = you + moveDir x 0.55; ball velocity = your velocity + (P - ball) x 6; then clamp the ball's speed to 1.4 x walk.

- A **pat** sound event (section 9) is emitted when control begins and every 0.45 s while it lasts. Wall contacts while under control count as pats, not bounces.
- **Nudge:** if the ball is touching you (centres within 0.46) but not under control, it is pushed out along the contact normal and gains 1.3 x the normal component of your velocity. It emits a pat.

### 6.3 The hip strike

- One input: Space, J or K; a tap; a quick click or a right-click.
- It works only if the ball centre is within 0.70 tile of yours ("in reach"). Otherwise a short grey arc is drawn at your hip and, at most once every 6 s, the caption "The ōlli is out of reach."
- Ball velocity becomes aim x strike speed (9.0 to 10.2 tiles/s by level). Cooldown 0.35 s. It emits a strike event at your position.
- The existing hip arc (`ball(..., hit)`) shows the strike for 0.2 s.

### 6.4 Aim and aim help

- **Default aim** = your facing. On mouse it is the direction from you to the pointer. On touch it is the second finger's drag or flick (section 15).
- **Keyboard precision aim:** hold Space for 0.25 s to plant. You stop moving, the aim line shows, and Left and Right (or A and D) rotate the aim by 3 degrees per step at 40 steps per second (rotation by the literal constants cos 3 = 0.9986295347545738, sin 3 = 0.052335956242943835, renormalized each step). Release Space to strike. Shift cancels.
- **Aim snap, in order** (Assist widens the ring tolerance to 1.0 tile):
  1. **Stone Face snap.** If the Stone Face is within 4 tiles of the ball, in line of sight, and the dot product of the aim and the direction from the ball to the Stone Face is at least 0.90, then aim = the direction from the ball to the Stone Face.
  2. **Ring snap.** If the ball is on a tile of a court whose ring is a valid target (an unclaimed side ring, or the awake Great Ring), the dot product of the aim and the alley axis pointing toward the ring is at least 0.82, and the ball's lateral offset from the slot's centre line is at most 0.6 tile, then aim = the direction from the ball to the slot's current centre point.
  3. Otherwise, raw aim.
- **Aim line** (keyboard plant, mouse hover with the ball in reach, touch second finger): from the ball along the aim to the first wall, plus a 1.5 tile stub of the reflection. It is drawn #ffffff dashed (4 and 4 CSS px) and clipped to tiles you can currently see, so you can never aim into the dark. When it passes through a ring slot in view, the slot outline turns solid.

---

## 7. The ōlli

- Radius 0.18 tile, drawn with the existing `ball()` at 0.18 x T.
- **Rolling friction:** speed is multiplied by the literal per-step factor `0.9935498190591483` (that is 0.46 per second). The ball stops below 0.25 tiles/s. Maximum speed is 12 tiles/s (0.1 tile per step, under the radius, so it cannot tunnel).
- **Walls**, closed slabs and ring stones are boxes. Circle-versus-box collision runs on x, then y, with corner caps (the generalized Drop `cpt`). Restitution 0.72 on the normal; the tangent keeps 96%.
- A strike at 9 tiles/s travels about 8 to 11 tiles with bounces.
- **Knock:** any impact whose normal speed is over 0.6 tiles/s. Knocks within 0.1 s and 1 tile of each other merge into one (the louder one is kept). Each knock is a sound event (section 9) and, by kind, lights stone (7.1).
- **The Stone Face's body** is a circle of radius 0.45 tile for the ball. Contact at 3 tiles/s or more triggers Make it play (11.9) when it is ready. Otherwise the ball bounces off with restitution 0.5 and a knock.
- **Out of sight:** when the ball's tile is neither visible nor lit, the ball is not drawn. A hollow #b8b8b8 circle marks where you last saw it or last heard it knock. When that point is off screen, a small hollow circle sits on the view edge on the line toward it.

### 7.1 Knock light ("strike to see")

- A knock lights every tile within radius r_k (Euclidean, between tile centres) that has a clear line of sight from the knock tile, using the same ray chains as your sight (8.1). You do not need line of sight to it yourself: you see the stone by its sound.
- r_k = 1.5 + 0.35 x impact speed, capped at 5 tiles. A ring pass lights every tile of that court plus r_k 4.5 around the ring. A tessera click lights 1.5. The Stone Face's own return strike lights 3.0 at the Stone Face, so you see it play.
- Lit tiles show for 0.5 s (Calm 0.7 s): `lit[t] = max(lit[t], step + 60)`. A repeated knock extends the light and never relights it from dark. Then they pass into memory.
- When light ends, walls go from the double carved line to the single grey memory line. They change shape, not from white to black, which keeps the change gentle on the owner's display.

---

## 8. Seeing

### 8.1 Your sight

- **Sight radius** R (3.5 tiles on level 1 down to 3.0 on level 5; Calm +0.5).
- **Ray chains**, built once at init: 128 rays from a tile centre, each a list of tile offsets (Int8Array) walked by DDA out to radius 12. They are render-only, so `Math.cos` is allowed at init.
- **Recompute** visibility only when your tile changes, a slab changes, or a court is claimed. Walk each ray: mark tiles with `vis = stamp` while within R, or while the tile is lit by a court (8.2); stop after the first wall or closed slab, which is itself marked visible.
- Every visible tile and every lit tile enters memory.

### 8.2 Lit courts

All tiles of side courts and the Great Court (floor and wall ring) are **lit by ocote torches**. A ray keeps marking court tiles out to 12 tiles, even past R. So you see into a court along any line of sight up to 12 tiles, and the Stone Face standing in it.

### 8.3 Memory and what you know at the start

- At level start, the wall rings of every court and of the Stone Face's post are already in memory. You know the plan of the courts, but not the routes between them.
- **Edge markers.** When an unclaimed court's centre is off screen, a small hollow square sits on the view edge on the line toward it. The Great Court gets a double square, drawn only in the finale.

### 8.4 What shows through darkness (on purpose and few)

1. The Stone Face's eyes, only while it sees you (rule 2).
2. Claimed rings, solid white (they are sounding).
3. The awake Great Ring.
4. The gathering outline on level 5 (12.5).
5. The hollow last-known marker of the ball.
6. The echo ghost (9.4).
7. Sound fronts, drawn only on remembered or visible tiles.

---

## 9. Sound: what is heard, and how you see it travel

### 9.1 Events

Each event has a source tile and a base radius in **path tiles** (corridor distance, not straight-line). The heard radius is base x level hearing x temperament x Calm.

| Event | Base radius | Drawn front |
|---|---|---|
| Pat (dribble touch, nudge) | 5 | no (a 0.2 tile tick mark at the ball, 0.15 s) |
| Hip strike, at you | 8 | yes |
| Bounce, impact speed v | 2 + 0.9 v, only if v >= 1.0, capped at 12 | yes if v >= 4.5 |
| Ball hits a ring's stone (a miss) | 14 | yes |
| Ring claimed | the whole labyrinth | yes |
| Great Ring miss | 14 | yes |
| Tessera click (level 2) | 16 | yes |
| Moving stone (level 4), heard by you only | 8 | yes, hollow ticks |
| A ring falls silent (finale), heard by you only | 8 | yes, hollow ticks |

The Stone Face's own return strike and its footsteps are not events it hears.

### 9.2 Waves

- Each event takes a slot in a pool of 8 wave slots (the oldest is replaced). It runs one BFS from its source over floor tiles into `WV[slot]`, cut off at its radius (or the whole map for a claimed ring).
- The **front** travels at 14 tiles/s: front = age x 14.
- **Drawing:** for every tile in the camera window that is remembered or visible, and for each active wave whose front is within 16 tiles, draw a crisp #e6e6e6 1 px line across the tile edge between a tile with distance floor(front) and a neighbour with floor(front) + 1. The line bends round corners because it follows the BFS. You-only events use hollow ticks (two short marks instead of a line).
- Waves do not add to memory. Knock light reveals; waves show travel.

### 9.3 How the Stone Face hears

- It hears an event at the moment the front reaches its current tile, if that tile's distance in the wave field is within the heard radius. Sound reaches it a little late, with distance.
- It **follows the newest sound it heard**, in Patrol, Investigate, Search, Listen and Wait. It ignores sounds while seeing you (notice step 1 or more), in Rush, Play, Recover and Gathering.
- **Asleep**, it wakes early on hearing any event with a base radius of 10 or more.

### 9.4 Echo ghost

When a drawn front passes the Stone Face's tile while it is not drawn (out of sight, not lit) and within 16 tiles of you, a frozen #b8b8b8 outline of it appears there for 0.6 s. It shows the outline at that moment's edge-on width, and nothing else: no eyes, no mouth. You learn where it was, not where it is. Only one ghost shows at a time.

---

## 10. Courts, rings, safe ground, the finale

### 10.1 Court shapes (tile units, vertical orientation; horizontal is the transpose)

- **Side court**, 5 wide x 9 tall: end zone A is rows 0 to 1 (5 wide), the alley is rows 2 to 6 (3 wide, columns 1 to 3), end zone B is rows 7 to 8. The alley's side walls (columns 0 and 4, rows 2 to 6) are wall. There is a wall ring around the whole footprint. **Mouths** are at the middle of each end zone's outer edge, column 2. The **ring** juts from one alley side wall (side seeded) at row 4.
- **Great Court**, 7 wide x 13 tall: end zones are rows 0 to 2 and 10 to 12 (7 wide), the alley is rows 3 to 9 (3 wide, columns 2 to 4). One mouth per end zone at column 2 or 4 (seeded per end, odd column). The Great Ring is at row 6.
- **Post** (the Stone Face's niche), 3 x 3, with 1 mouth (levels 1 and 2) or 2 mouths (levels 3 to 5) at odd positions on different sides. It is not lit and never safe ground.
- **Entry**: one cell on the bottom row, drawn as a small stepped niche with `gateArt`.

### 10.2 The ring, top-down

In real courts the stone ring stood out from the alley wall. From above it reads as a carved bar jutting into the alley with a slot (the hole) in it. The ball must pass the slot moving along the alley.

- Footprint along the axis: 0.30 tile thick, centred on the ring row.
- Across the alley, measured from the wall face: stone A 0.35, slot w, stone B 0.35. w = slot width in ball widths x 0.36 tile (table, section 13).
- The ball collides with stones A and B. **You and the Stone Face** are blocked by the whole footprint, because the ring is high on the wall and only the ball goes through. For the Stone Face's pathing, the two alley tiles nearest the ring wall in the ring row are in `fblk`. For the Great Ring, its widest reach is blocked.
- **Pass test:** the ball centre crosses the ring plane (the line across the alley at the ring's current axial position) while inside the slot's current lateral span, with axial speed of at least 1.5 tiles/s. A slower crossing: "Too soft. Strike it through." (at most once every 3 s).
- **Drawing:** two filled stone blocks with the slot outlined between them.
  - Unclaimed: outline #e6e6e6, black fill.
  - Claimed: solid white, plus a carved disc on the court floor at its centre.
  - The sleeping Great Ring: outline #b8b8b8 with the slot drawn closed.
  - In memory: #8c8c8c outline.
  - Unclaimed rings are drawn once seen; claimed rings and the awake Great Ring are always drawn.
- **Torches:** each end wall of a lit court carries a small stepped bracket with one teardrop flame outline. It is static and has no halo. The court is simply drawn, because it is lit.

### 10.3 Claiming and safe ground

- The first pass through a side ring claims it.
  - Score 1000 x level.
  - Sound event "ring claimed" (heard everywhere).
  - Knock light on the whole court.
  - The court's tiles join `fblk` (the Stone Face may not enter).
  - The court becomes **safe ground**: no contact can count while your tile is a safe-ground tile.
  - The mark clears (11.10).
  - The caption reads: "Ring claimed. This court is safe ground."
- **Wait:** if the Stone Face is chasing you and you are on safe ground, it goes to the outside tile of the nearest mouth of that court and stares in. It waits (4.0, 3.6, 3.2, 2.8, 2.5 s by level, Calm x1.4) and then leaves on Patrol, taking the waypoint farthest from that mouth first. It can still see you inside (the court is lit), and its notice can fill, but it never enters.
- A claimed ring still lets the ball through in both directions.

### 10.4 The Great Ring and the falling silence (the endgame)

- When the last side ring is claimed:
  - The Great Ring wakes (it turns solid and its motion begins): "Every ring is claimed. The Great Ring is open. The rings will fall silent one by one."
  - The Stone Face wakes if it is asleep, and its patrol changes to the finale route (11.4).
- **The silence.** After a 3.0 s grace, the claimed rings fall silent one at a time, in the order they were claimed.
  - Silence step = max(table value [14, 12, 11, 10, 9 s], 2.0 x Dmax / (0.85 x walk) / number of side rings), x1.4 under Calm. Dmax, computed at generation, is the largest path distance from any side court's centre to the Great Court's nearer end-zone centre.
  - A silent ring returns to an outline with a broken slot. Its court is no longer safe ground and leaves `fblk`. Its HUD dot empties. Caption: "A ring fell silent." It emits a you-only wave.
- **Pass:** the Great Ring pass test (10.2) clears the level: "The Stone Face lets you pass." The Stone Face's eyes close wherever it is. Score: 2500 x level, plus 20 per second left on the whole silence clock.
- **All silent:** "The rings fell silent." You lose one attempt (none under Assist). Then:
  - every side ring is claimed again and the silence clock restarts after its grace;
  - you return to the court claimed last, with the ball at your feet and 3 s of protection;
  - the Stone Face is set back at its post, asleep for half its wake time (11.11).

### 10.5 The Great Ring variants (Drop's ring of the same level, seen from above)

All motions are polynomial waves of the phase p in [0, 1): tri(p) = 1 - |2p - 1|, S(q) = 3q^2 - 2q^3, wave(p) = 2 S(tri(p)) - 1. Under Calm, every period is x1.4. The boss seed varies the parameters.

| Level | Variant | Rule | Seeded |
|---|---|---|---|
| 1 | **Still** | Fixed. | Side wall, slot 2.2 to 2.3 ball widths |
| 2 | **Sliding** | The ring extends from and retracts into its wall: lateral offset = amp x (0.5 + 0.5 wave(t / per + ph)). The passage beside it never drops below 0.7 tile. | amp 0.6 to 1.0 tile, period 2.6 to 3.6 s, phase |
| 3 | **Turning** | Open while (t / per + ph) mod 1 is under the open fraction, otherwise solid (the slot is drawn closed). A carved notch bar on the court floor beside the ring fills as it opens. | Period 3.0 to 4.2 s, open fraction 0.35 to 0.45, phase |
| 4 | **Paired** | One ring on each alley wall at row 6. Only one is live (solid); the other sleeps (outline, slot closed). They swap every per seconds. The next swap is shown by a tick sweeping round the live ring like a clock hand. | Period 2.4 to 3.4 s, which starts live, slot 1.8 to 2.0 |
| 5 | **Walking** | The ring walks along its wall: axial offset = A x wave(p), lateral offset = amp x (0.5 + 0.5 wave(2p + 0.25)) for the figure-eight, or (0.5 + 0.5 wave(p + 0.25)) for the rounded loop, with p = speed x t. | Path shape, A 1.5 to 2.0 tiles, amp 0.6 to 0.9, speed 0.18 to 0.28 cycles/s |

Aim snap aims at the slot's current centre and never leads a moving target. Timing is the skill.

---

## 11. The Stone Face

### 11.1 Look: the `FACE` data object (from the cultural research, adjusted)

Units: W = face width. The origin is the face centre, y points down. **W = 1.5 tiles**, so it is wider than a corridor and overlaps the walls: it does not fit. It is drawn upright on the top-down board, the way you would see a standing slab from where you are.

```js
// ES5. Every x is multiplied by sx (11.2), then scaled by W and offset; final points are rounded to device pixels.
var FACE = {
  outline: [-0.40,-0.50, 0.40,-0.50, 0.46,-0.44, 0.46,-0.20, 0.53,-0.20, 0.53,0.08,
            0.46,0.08, 0.43,0.18, 0.30,0.42, 0.17,0.50, -0.17,0.50, -0.30,0.42, -0.43,0.18,
            -0.46,0.08, -0.53,0.08, -0.53,-0.20, -0.46,-0.20, -0.46,-0.44],   // closed; fill #000, stroke #fff 1.5 css px
  ear: [0.495,-0.06, -0.495,-0.06], earR: 0.02,      // drilled holes on the rectangular ear tabs, stroke only, no ornament
  band: { y0:-0.46, y1:-0.27, x0:-0.38, x1:0.38, units:4 }, // step-fret band, rules at y0 and y1
  brow: [-0.235, -0.215],                             // two straight rules, x -0.40 to 0.40, the carved ledge
  eye: { inner:[0.08,-0.09], outer:[0.30,-0.115], up:[0.19,-0.19], lo:[0.19,-0.04],   // right eye; mirror x for left
         rim:1.18, pr:[0.034,0.030,0.024,0.018], pdx:0.055, pdy:0.018 },
  nose: [-0.035,-0.21, -0.05,0.08, -0.10,0.12, -0.06,0.14, 0.06,0.14, 0.10,0.12, 0.05,0.08, 0.035,-0.21], // open polyline
  mouth: { x0:-0.15, x1:0.15, up:0.245, lo:0.295, loOpen:0.33, teeth:11, tw:0.018, th:0.02 },
  tess: { cell:0.11, jit:0.02, yTop:-0.04 },          // mosaic below yTop; lost cells by level in MPAR
  inset: 0.04                                          // back view: inner hollow outline
};
```

- **Outline:** a flat top, chamfered upper corners, rectangular ear tabs, and a jaw tapering to a flat chin. It is filled black, so it hides the walls behind it.
- **Brow band:** the game's own step-fret (drawn from the `FRET` data, single #e6e6e6 lines at this size). Four units are mirrored at the centre line, the two left units hooking right and the two right hooking left, so they meet in a point above the nose. Below it, two straight rules form the carved ledge. The band uses `FRET` data, so an advisor can replace it with plain rules by setting `units: 0`.
- **Eyes** (inlays):
  - Socket rim: the almond scaled by 1.18, 1 px #e6e6e6.
  - Shell: the almond (two quadratic curves through `up` and `lo`) filled #fff. The outer corner sits 0.025 W higher than the inner corner: a hard stare without an expression.
  - Obsidian pupil: a #000 disc clipped to the almond. Radius `pr[step]`. Offset toward you in screen space by up to `pdx` and `pdy` times k, with k = 0.4 when not noticing, 0.7 at step 1, 1.0 at steps 2 and 3.
  - Glint: a steady #fff square, max(2 device px, 0.014 W), at the pupil centre offset by (-0.35 r, -0.35 r). It is drawn only when the Stone Face is in your sight or lit, never in darkness, and it never flashes.
  - **Closed** (asleep, blind on level 3, gathering origin on level 5, after the last pass): one horizontal lid line per eye from inner to outer corner. No almond.
- **Nose:** a long straight bridge to a wide flat base, as an open polyline.
- **Mouth:**
  - Closed: two straight lip lines, with short vertical ticks at the corners.
  - Open (from full notice through Rush): the lower lip drops to `loOpen`. Eleven square shell teeth, filled #fff and evenly spaced, show along the upper lip, and eleven along the lower lip.
  - Never fangs, points, a downturned mouth or a wide gape.
- **Mosaic:** a seeded jittered grid (cell 0.11 W, jitter 0.02) over the face below `yTop`, leaving out the eye almonds scaled 1.25, the nose box and the mouth box plus 0.02. It is clipped to the outline and stroked #8c8c8c at 1 px in one path. A seeded fraction of cells (12% on level 1 to 18% on level 5) is **lost**: those cells have no seams, as bare stone. The asymmetric pattern is true to aged mosaics, and each level's face looks different and older. The seams are precomputed once per level into a Float32Array.
- **Level of detail:** below a drawn W of 48 CSS px (phones), draw only the outline, brow rules, eyes and the mouth slot.

### 11.2 Edge-on, face, back

- Let u = the unit vector from the Stone Face to you (world space), f = its facing, and s = dot(f, u).
- s >= 0.12: **front.** Every x is multiplied by sx = max(0.12, s).
- s <= -0.12: **back.** sx = max(0.12, -s). Draw the outline, an inner outline inset by 0.04, and the two ear holes. No features: a hollow shell.
- Between: **slab.** Only the outline, at sx = 0.12.
- The x coordinates are multiplied directly, never through `ctx.scale`, so strokes stay crisp.
- When it turns toward you at a junction, a thin slab swells into a full face in hard eighth-steps (11.3). That turn is the core scare.

### 11.3 Facing and turning (stone moves in hard steps)

- Facing f is one of 8 literal unit vectors: (0, -1), (0.7071067811865476, -0.7071067811865476), (1, 0), and so on.
- It turns one eighth-step every 0.12 s (Calm 0.17 s): 90 degrees takes 0.24 s and 180 degrees takes 0.48 s. Each step toward you while visible, or while the eyes show, emits `face-turn`.
- The "best facing" toward a target vector v is the index maximizing dot(f_i, v). Ties are broken by faceSeed.

### 11.4 Movement

- It moves tile-centre to tile-centre along a BFS distance field, 4-way. The field is rebuilt only when its target tile changes, or when a slab or `fblk` changes. Its drawn position is smooth.
- **Corner pause:** whenever its next step turns 90 degrees from its current direction, it stops for the corner pause (0.32 s to 0.22 s) and turns two eighth-steps in that time. A reversal costs twice the pause. This applies in every moving state, and it is the step-fret escape.
- **Patrol glide:** in Patrol only, movement runs in a 0.5 s cycle: glide 0.35 s at patrol speed / 0.7, then hold 0.15 s. Each glide start emits `face-step`. The glide speed stays below your walk at every level.
- **Patrol route:** the outside tiles of the mouths of unclaimed side courts, in a seeded cyclic order. When it chooses the next waypoint: if it heard a knock in the last 20 s, it takes the unclaimed-court mouth nearest (by path) to the last knock tile; otherwise the next in order. In the **finale** the route is the two outside tiles of the Great Court mouths, alternately, with a 2.0 s Listen at each, facing outward. Finale hearing is x1.25.
- **Listen** (the junction sweep): in Patrol, at every 3rd to 5th junction (seeded per stop; temperament "Waits": every 2nd to 3rd), and on arrival at a waypoint, it stops. It turns in eighth-steps to face each open branch in seeded order, holding 0.4 s on each, for at most 3 branches (Waits: x1.5 holds).

### 11.5 Sight, notice and the eyes

The Stone Face **sees you** when all three hold:
- dot(f, u) >= 0.70 (a cone of about 45 degrees each side);
- a clear grid line of sight (integer supercover line between the two tile centres; walls and closed slabs block it, and a diagonal step between two wall corners is blocked);
- distance d (Euclidean, tile centres) <= E.

E is the eye range: S + 2 normally, or 12 if you stand on a lit court tile (where S also becomes 12). S is the stare range by level and temperament.

**Rule 2 exactly:** its eyes are drawn through darkness if and only if it sees you, and while it sees you its notice m fills. Everything else depends on m.

**Debounce (no flicker at a line-of-sight boundary):**
- "Sees you" turns on when the raw test passes, but only if at least 0.5 s have passed since it last turned off.
- It turns off when the raw test fails, but only after it has been on for at least 0.5 s.
- The eyes follow the debounced value. The fill counts only while both the debounced value and the raw test are true.

So the eyes never toggle faster than twice a second. They may linger up to 0.5 s after it loses sight of you, but the fill stops at once.

- **Fill rate** while it sees you, per second:
  - 1 / Tn if d <= S_eff / 2;
  - 1 / (1.5 Tn) if d <= S_eff;
  - 1 / (3 Tn) if d <= E.

  S_eff = S, except when you have not moved for 1.0 s and are not on a lit tile: then S_eff = 3. Standing still in the dark buys time.
- **Drain** while it does not see you: m falls at 1 / (2 Tn) per second.
- **Steps**, all shape changes:

| m | Step | Pupils | Behaviour |
|---|---|---|---|
| under 1/3 | 0 | k 0.4, r 0.034 | It continues what it was doing. The eyes showing are the tell. |
| 1/3 to 2/3 | 1 | k 0.7, r 0.030 | It **stops** and turns to face you. Sounds are ignored. `face-eyes {step:1}`. aria "The Stone Face sees you." (at most once per 8 s) |
| 2/3 to 1 | 2 | k 1.0, r 0.024 | Holds, facing you. `face-eyes {step:2}` |
| 1 | 3 | k 1.0, r 0.018, mouth opens | **Rush.** `face-eyes {step:3}`, `face-rush` |

- If you break sight at step 1 or more, it investigates your last seen tile at investigate speed, then Searches.
- **Close sense:** within 1.5 tiles with line of sight, it turns toward you at once, even facing away (it senses you). Then the normal sight rule applies, so the eyes show and m fills at the fastest rate. No contact is possible until m reaches 1.

### 11.6 States

| State | Behaviour | What you see |
|---|---|---|
| **Asleep** | At its post for the wake time (seeded within the range per level, Calm x1.4). It wakes when the time ends and you are at least 6 path tiles away; early on hearing a base-radius-10 event; or when you come within 3 tiles with line of sight (it turns toward you; m starts at 0). | Eyes closed. The post is always drawn in memory. `face-wake` on waking, plus aria "The Stone Face wakes." |
| **Patrol** | Route and glide (11.4). | A slab gliding, swelling into a face when it turns your way. |
| **Listen** | Sweep (11.4). | The face turning across each branch. The worst moment. `face-listen` |
| **Investigate** | It goes to the newest heard tile at investigate speed (continuous, no glide). A newer sound retargets it after a 0.2 s pause, during which it turns toward the first step of the new path. On arrival: Search. | `face-hear` on each retarget |
| **Search** | At the tile, it faces each open branch for 0.5 s (eighth-steps between them), then Patrols. | `face-search` |
| **Rush** | m = 1. It paths to your tile while it sees you, at rush speed x chase ramp. After losing sight for 0.4 s it goes to your last seen tile at the same speed, with m set to 2/3, then Searches. | A full face coming, mouth open. `face-lost` plus aria "The Stone Face lost you." when it starts searching |
| **Play** | 11.9 | Edge-on slab, ball at its chin |
| **Recover** | 1.0 s after marking you; 0.6 s after Play. Still, pupils centred, mouth closed. | Your window to slip past. |
| **Wait** | At a claimed court's mouth (10.3). | It hangs in the mouth, staring in. `face-wait` |
| **Gathering** | Level 5 only (12.5). | |

**Rush speed** = rush x (1 + ramp). The **chase ramp** rises by 0.015 every 4 s of continuous sight, capped at 0.09. It resets after 3 s without sight, after Play, and after it marks you.

### 11.7 Corner learning

Within one chase (from m reaching 1 until it returns to Patrol), each corner pause after the 8th is multiplied by max(0.5, 1 - 0.06 x (k - 8)), where k counts corners in this chase. Stepped corridors stay an escape (even at minimum pause and full ramp it is slower than you on a 2-tile fret, x0.86 on level 1). They just stop being a free lead.

### 11.8 Loop reversal

During a chase, every time you enter a junction tile (3 or more floor neighbours), its count in `jpass` rises (the tiles touched are listed, so they can be cleared cheaply when the chase ends). When any junction reaches **3 passes**:
- the Stone Face stops for 0.3 s and turns to the opposite direction (`face-cut`);
- it rebuilds its path to your tile with the next tile of its current path treated as wall, so it goes the other way round the loop and meets you head-on;
- it keeps this path for 6 s, or until it sees you within 4 tiles, then resumes normal Rush;
- the counts reset.

### 11.9 Make it play (the ball as a shield)

- **Trigger:** the ball touches its body circle at 3 tiles/s or more, and its play cooldown (4 s) is ready, in any state except Asleep and Gathering. Also: in Patrol, Investigate or Search, it sees the ball resting (speed under 0.25) within S in its cone with line of sight; it goes to the ball and plays it.
- **Play:**
  - It stops and turns edge-on (two eighth-steps away from you).
  - The ball rests at its chin for the play time (1.2, 1.1, 1.0, 0.9, 0.8 s, Calm x1.4).
  - Then it strikes the ball at 5.5 tiles/s (it travels about 7 tiles at most) along the first step of the BFS path from the ball toward the court you claimed last (or the Entry if none). The opponent returns the ball toward your side, so it never strands it far away. The strike lights 3.0 tiles around it.
  - Then Recover 0.6 s, then Search at its tile, with m set to min(m, 2/3).
- Score +150, at most 3 times per level. The chase ramp resets.
- **Within the cooldown,** the ball just bounces off it with a knock.
- Caption, first time only: "It plays the ōlli back."

### 11.10 Contact

- **Contact** means all of these:
  - centres within 0.55 tile;
  - line of sight between the two tiles;
  - it is in Rush (or, on level 3, moving with a hunt, 12.3);
  - m reached 1 in this chase, and that fill took at least Tn;
  - you are not protected;
  - your tile is not safe ground.
- **First contact marks you.** "The Stone Face touched you. Once more and it turns you back."
  - You get x1.4 speed for 1.2 s.
  - It goes to Recover for 1.0 s, and you may pass through its body during that time.
  - Your yoke is drawn with a gap. The HUD shows the broken-yoke glyph, read as "Marked".
  - `marked`.
- **Contact while marked turns you back:** "The Stone Face turned you back." with the attempts left. `caught`, then the existing `fail()` beat.
- **The mark clears** when you claim a ring, or after 30 s without it seeing you.

### 11.11 Return after being turned back

- You respawn at the centre of the court you claimed last (safe ground), or at the Entry if you have claimed none. The ball rests 0.6 tile above you. You have 3 s of protection, drawn as the yoke in outline only, with no blinking.
- The Stone Face is cut (not animated) to its post if that is at least 6 path tiles from you and not in your sight; otherwise to the patrol waypoint farthest from you that is. It sleeps for 50% of its wake time.
- Claimed rings stay claimed.
- **Close-up** (switch on the pause screen; on by default unless Calm pace or reduced motion is on): before the caption, the face is drawn 3 tiles wide at the contact point, clamped into the view. Outline, open eyes and open mouth only, with no mosaic and no motion, for 0.6 s. It is one static line drawing with a small white area, never full screen, never flashing. `closeup`.

---

## 12. The five trials and the temperament

Each level has a fixed trial; the boss seed varies its parameters, the Great Ring's parameters and the temperament. Level 3 is always the turning face, but never the same turning face twice.

### 12.1 Level 1: The stone face

The base Stone Face. It teaches knocks, rings, safe ground, the eyes and the frets. The temperament is always **Listens** on level 1.

### 12.2 Level 2: Fallen tesserae

- While patrolling, a tessera comes loose from its mosaic every 3.5 to 5 s (seeded): a filled white square 0.12 tile wide, rotated by artSeed. It falls at junction tiles only, or anywhere (seeded). The cap is 10 to 14 (seeded); the oldest is removed first. `tessera-drop`.
- Tesserae are drawn only where you see or where knocks light.
- If you come within 0.3 tile of one, or the ball rolls within 0.25 of one, it **clicks**: base radius 16, a 1.5 tile knock light, and the tessera is removed. `tessera-click`.
- A struck ball sets them off too, so a well-aimed strike is a decoy.
- First click caption: "A tessera clicked. It heard that."

### 12.3 Level 3: The turning face

- It turns on a steady rhythm: period 3.0 to 4.2 s, a still fraction of 0.50 to 0.60 of each period, and a seeded phase.
- **Still phase:**
  - It cannot move.
  - Its stare range is S + 3.
  - It turns one eighth-step every 0.25 s toward the next open branch (seeded rotation), or toward its newest heard sound.
  - Notice works normally.
- **Moving phase:**
  - Its eyes are closed and it is blind: no sight, no close sense, and m drains.
  - It hears normally.
  - It moves continuously toward its target: your last seen tile if it has a **hunt** (m reached 1 within the last 8 s), at rush speed; otherwise its newest heard tile, at 1.3 x investigate speed. Corner pauses apply.
  - With a hunt, contact counts (11.10).
  - Without a hunt, if it comes within 1.0 tile of you, the phase switches to still at once (the rhythm restarts from that moment), its eyes open and notice begins from its current m. No contact counts.
- **Turn clock:** a notch bar under the HUD (120 x 8 CSS px, #e6e6e6). It fills from the left during the still phase and is drawn as ticks during the moving phase. A carved notch marks each switch. `turn-tell` fires 0.6 s before a switch (x1.4 Calm) and `turn {still}` at the switch.
- Caption: "It turns on a rhythm. While it faces, it cannot move. While it moves, it cannot see."

### 12.4 Level 4: The moving stones

- 5 to 7 **slabs** (single wall tiles chosen at generation, section 14.3) open and shut, each on its own rhythm: period 6 to 10 s, open fraction 0.45 to 0.55, seeded phase.
- **Warning** 1.5 s (Calm x1.4): a tick bar along the slab's long axis fills in 3 hard steps of 0.5 s. `stone-warn`. The change itself is a cut. `stone-move {open}`, plus a you-only wave of radius 8.
- A slab never closes on a tile occupied by you, the ball or the Stone Face. It holds closing until the tile is clear.
- An open slab is a shortcut. All validation is done with every slab closed, so slabs only add routes and never cut the labyrinth.
- The Stone Face rebuilds its path on every change.
- **Memory:** remembered slabs are always drawn **dotted** (a preallocated dash pattern), because their state may have changed.
- Caption: "Some stones slide open and shut. Your memory of them may be wrong."

### 12.5 Level 5: The gathered face

- **Trigger:** every 10 to 14 s (seeded cooldown), the Stone Face, if in Patrol, Investigate or Search, looks at the loudest event (by base radius) it heard in the last 3.0 s. It **gathers** there if all of these hold:
  - the event tile is at least 8 path tiles from it;
  - the event tile is at least 6 path tiles from you;
  - the event tile is not in your sight.
- **Tell** (1.2 to 1.6 s seeded, Calm x1.4), drawn even in darkness:
  - At the destination, step 1: the outer outline (#e6e6e6, full face width). Step 2: plus the brow rules and band. Step 3: plus the mosaic seams. Step 4: plus the eyes, closed.
  - At the origin, its eyes close and its outline becomes a single #8c8c8c line.
- At the end of the tell, a cut: it is at the destination, eyes open, in Listen. The origin is empty. It never breaks, scatters or shatters: it is simply elsewhere. `gather-tell` at the start, `gather` at arrival.
- Your sight is 3.0 tiles on this level.
- "It gathers at the ball, not at you": bait it with a far strike, then go the other way.
- Caption: "It gathers where the loudest knock was. Watch for its outline."

### 12.6 Temperament (seeded from the boss seed on levels 2 to 5)

| Temperament | Caption | Effect |
|---|---|---|
| Listens | "It listens." | Hearing x1.25, stare S - 1 |
| Watches | "It watches." | Stare S + 2 (so E = S + 4), hearing x0.8 |
| Waits | "It waits." | Listen at every 2nd to 3rd junction, Listen holds x1.5, patrol hold 0.25 s instead of 0.15, Wait at claimed mouths +1.5 s |

The temperament is named in the level-start caption and on the pause screen, so a shared Today's court has a character people can talk about.

---

## 13. Numbers (one MPAR table, normal pace)

Speeds are in tiles/s and times in s. `walk` is your speed without the ball under control; dribbling is x0.85.

| L | Board | Side rings | Walk | Patrol | Investigate | Rush | Rush / walk | Corner pause | Notice Tn | Stare S | Your sight | Hearing x | Wake | Strike | Wait | Silence step min | Braid | Side slot (ball widths) | Great slot | Play time | Lost tesserae |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 21 x 29 | 2 | 3.6 | 2.2 | 2.9 | 4.1 | 1.14 | 0.32 | 0.75 | 7 | 3.5 | 1.00 | 9 to 11 | 9.0 | 4.0 | 14 | 0.50 | 2.5 | 2.2 | 1.2 | 12% |
| 2 | 23 x 31 | 2 | 3.8 | 2.4 | 3.1 | 4.4 | 1.16 | 0.30 | 0.68 | 7 | 3.5 | 1.05 | 8 to 10 | 9.3 | 3.6 | 12 | 0.45 | 2.35 | 2.1 | 1.1 | 13.5% |
| 3 | 25 x 33 | 3 | 4.0 | 2.6 | 3.4 | 4.7 | 1.18 | 0.28 | 0.62 | 8 | 3.25 | 1.10 | 7 to 9 | 9.6 | 3.2 | 11 | 0.40 | 2.2 | 1.95 | 1.0 | 15% |
| 4 | 27 x 35 | 3 | 4.2 | 2.8 | 3.6 | 5.0 | 1.19 | 0.25 | 0.56 | 8 | 3.0 | 1.15 | 6 to 8 | 9.9 | 2.8 | 10 | 0.35 | 2.05 | 1.8 | 0.9 | 16.5% |
| 5 | 27 x 37 | 4 | 4.4 | 3.0 | 3.8 | 5.3 | 1.20 | 0.22 | 0.50 | 9 | 3.0 | 1.20 | 5 to 7 | 10.2 | 2.5 | 9 | 0.30 | 1.9 | 1.7 | 0.8 | 18% |

**Chase math (the step-fret rule).** This is the Stone Face's effective speed over your walk, by how often the corridor turns. A turn every 2 tiles: 0.69, 0.70, 0.71, 0.73, 0.76. Every 4 tiles: 0.86, 0.87, 0.88, 0.91, 0.93. Every 6 tiles: 0.93, 0.95, 0.96, 0.99, 1.01. Run the frets and you gain; run a straight and you lose. So the generator caps straights at 7.

**Calm pace:** Stone Face speeds x0.8. Tn, wake, wait, play time, silence step, Great Ring periods, slab warning, gather tell, turn tell and eighth-step time x1.4. Hearing x0.85, corner pause x1.2, your sight +0.5, knock light 0.7 s. Your own speeds do not change, because slowing you makes stealth harder, not calmer. As now, Calm applies from the next level.

**Assist** (pause menu): unlimited attempts, ring snap tolerance 1.0 tile, Tn x1.5. Not saved as best.

**Constants:**
- your radius 0.28; ball radius 0.18;
- reach 0.70; strike cooldown 0.35 s;
- catch radius 0.55; close sense 1.5;
- eye range S + 2 (12 on lit tiles);
- wave speed 14 tiles/s; knock light 0.5 s;
- play cooldown 4 s; return strike 5.5 tiles/s;
- protection 3 s; mark clears after 30 s unseen;
- finale grace 3.0 s;
- terror bands at path distances 20 / 14 / 9 / 5.

```js
// [walk, patrol, invest, rush, corner, Tn, S, sight, hearX, wakeMin, wakeMax, strike, wait, silence,
//  rings, w, h, braid, slotSide, slotGreat, playT, lost]
var MPAR = [
  [3.6,2.2,2.9,4.1,.32,.75,7,3.5,1.00,9,11,9.0,4.0,14,2,21,29,.50,2.5,2.2,1.2,.12],
  [3.8,2.4,3.1,4.4,.30,.68,7,3.5,1.05,8,10,9.3,3.6,12,2,23,31,.45,2.35,2.1,1.1,.135],
  [4.0,2.6,3.4,4.7,.28,.62,8,3.25,1.10,7,9,9.6,3.2,11,3,25,33,.40,2.2,1.95,1.0,.15],
  [4.2,2.8,3.6,5.0,.25,.56,8,3.0,1.15,6,8,9.9,2.8,10,3,27,35,.35,2.05,1.8,.9,.165],
  [4.4,3.0,3.8,5.3,.22,.50,9,3.0,1.20,5,7,10.2,2.5,9,4,27,37,.30,1.9,1.7,.8,.18]
];
```

These are starting values. The bot harness (section 23) tunes them, and must never push a tell below its floor (section 11.10 and 23.4).

---

## 14. Map generation (seeded, always solvable)

### 14.1 Steps for level L, try t (sub-seed `mix(mazeSeed, t)`, t = 0 to 29)

1. **Grid** w x h from MPAR, all wall. Cells are the tiles at odd (x, y), with 1 <= x <= w - 2 and 1 <= y <= h - 2.
2. **Rooms.** Every room footprint has an odd origin, keeps one corridor cell of clearance to the outer wall and to every other room (their wall rings never touch), and is placed in this order:
   - **Entry:** the cell (xe, h - 2), xe odd, in the middle 60% of the width.
   - **Great Court:** orientation r() < 0.5 vertical (7 x 13) else horizontal (13 x 7). Its centre lies in the top 40% of rows. Chosen uniformly among valid origins.
   - **Post:** 3 x 3, at the valid origin whose centre is nearest the board centre (ties by r()). At least 4 tiles from every court's wall ring.
   - **Side courts:** for each, orientation from r(). The best of 12 random valid origins, maximizing the minimum Chebyshev distance to existing rooms and to the Entry. Rejected if the court's centre is within 8 tiles (Manhattan) of the Entry.

   If any room cannot be placed, the try fails. Room footprints and wall rings are **reserved**.
3. **Carve** (iterative DFS on a preallocated Int16Array stack) over free (unreserved) cells, from the Entry cell.
   - With o = the unvisited neighbour directions: if the current direction is in o and r() >= bias, keep it; otherwise pick uniformly among o without it (or it, if it is the only one).
   - bias = 0.55, or 0.85 inside **fret zones**: 2 (levels 1 and 2) or 3 (levels 3 to 5) seeded 4 x 4 cell rectangles that make staircase corridors.
   - Then start a new DFS from every unvisited free cell, in seeded order, so the forest covers all free cells.
4. **Rooms carved:** their floors become `grid = 1` with their `zone`. Court inner walls stay wall.
5. **Mouths:** open each mouth's wall-ring tile. Each mouth joins a room floor tile to the corridor cell outside it, which exists by the clearance rule.
6. **Join:** label floor components by BFS. While there is more than one, scan wall tiles between two free cells of different components in seeded order and open the first; relabel. This is bounded by the number of walls.
7. **Braid:** each dead-end cell (zone 0, exactly one open side), in seeded order, opens one closed wall toward an adjacent free cell with probability braid(L).
8. **Cap straights:** any corridor run longer than 7 tiles without a side opening gets a side wall opened at its middle (the existing `repair`, without the mirror). At most 24 repairs.
9. **Level 4 slabs** (14.3).
10. **Derived data:** `zone`, `fblk` (ring footprints), the patrol waypoints, Dmax for the silence step, par (21.1), and the initial memory (court wall rings and the post).
11. **Validate** (14.2). On failure, try t + 1.

### 14.2 Validation (BFS, with every slab closed)

- V1: every floor tile is reachable from the Entry.
- V2: **every court lies on a cycle.** With that court's floor tiles blocked, the outside tile of mouth A reaches the outside tile of mouth B. This holds for the Great Court and every side court, so there is always another way round a court.
- V3: the Entry is at least 14 path tiles from the post's nearest mouth.
- V4: the Entry to the Great Court's nearest mouth is at least 0.6 x the farthest floor distance from the Entry.
- V5: each side court's nearest mouth is at least 8 path tiles from the Entry.
- V6: every mouth's outside tile has at least 2 floor neighbours outside the room (never a dead-end pocket), and no outside tile is shared by two rooms.
- V7: the nearest mouths of any two courts are at least 6 path tiles apart.
- V8: at least 20% of the corridor tiles of degree 2 are corners.
- V9: no straight corridor run is longer than 7 tiles without a side opening.

**Fallback (after 30 failed tries, always valid):** the pillar field.
- Rooms go at fixed slots per level: the Great Court vertical at the top centre; the post at the centre; side courts at the left-middle, right-middle, left-lower and right-lower slots; the Entry at the bottom centre. The layout is flipped horizontally if r() < 0.5.
- Every wall tile between two free cells is opened, leaving pillars at (even, even).
- A pillar field minus separated rectangles is connected, so V1 and V2 hold; the fixed slots satisfy V3 to V7 (checked once per board size by the test); V9 holds trivially; V8 is exempt.
- On level 4 the fallback adds 6 slabs on opened tiles, no two within 3 tiles of each other and none within 2 of a mouth or the Entry.

This makes generation always terminate, deterministically. The target is a fallback rate at or under 0.5%.

### 14.3 Level 4 slabs

- **Candidates:** wall tiles with floor on two opposite sides (both zone 0) that are not on a room's wall ring, not within 2 tiles of the Entry or any mouth, and whose two floor neighbours are at least 8 path tiles apart with the tile closed (so opening it is a real shortcut).
- **Choose** 5 + floor(3 r()) by seeded greedy spacing (Chebyshev at least 5 between slabs).
- **Closed = wall.** Validation runs with all slabs closed, so the labyrinth is connected in every mix of open and closed states.

---

## 15. Controls

| Action | Keyboard | Touch (portrait and landscape) | Mouse |
|---|---|---|---|
| Walk | Arrows or WASD, 8 directions | **Floating stick:** the first finger down anywhere on the view sets the origin. A 48 px #8c8c8c ring is drawn there. Dead zone 8 px; speed = clamp((d - 8) / 32, 0.35, 1) of full speed in the drag direction. Lift to stop. | Hold the left button on the view for 180 ms or drag 6 px: you walk toward the pointer (full speed beyond 1 tile from you, stopping within 0.3). |
| Strike | Space, J or K (tap under 0.25 s) | **Tap** with any finger (under 200 ms and 12 px). A second finger can tap while the first steers. **Flick** a second finger (over 600 px/s) to strike in the flick direction. | **Quick click** (under 180 ms, under 6 px) strikes toward the pointer; right-click strikes toward the pointer. |
| Precise aim | Hold Space 0.25 s to plant; Left and Right rotate the aim; release to strike; Shift cancels | **Second finger drag** (over 12 px): an aim stick. The aim line shows along the drag direction; release to strike; drag back within 12 px of its start to cancel. | Hover with the ball in reach: the aim line shows toward the pointer. |
| Pause | P or Escape | Pause button (44 px, top right) | Pause button |
| Restart level | R on the pause or result screen | Button | Button |

- Two inputs only: move and strike. There is no sprint, no hiding button, no pickup.
- Input fills `inp` only (new fields `mx`, `my`, `ax`, `ay`, `plant`; existing `sb` pulse). No game logic runs in handlers. A `keyup` clears its own axis. Keys with Ctrl, Meta or Alt are ignored. Shift is allowed.
- The game pauses on blur and tab hide, as now. Touch uses Pointer Events with `touch-action: none` on the canvas only.

---

## 16. The screen

### 16.1 Layout and camera

- **HUD** row at the top (52 px), as now.
- **Caption strip:**
  - Portrait: a 52 px strip at the bottom, under the view.
  - Landscape and desktop: in the left gutter if it is at least 140 px wide; otherwise a 44 px strip under the HUD.
  - Captions never cover the labyrinth.
- **View:** width = min(W - 32, 25 T) CSS px, centred. Height = everything between the HUD and the caption strip. Gutters of at least 9u carry the cached step-fret bands (`drawBand`).
- **Tile size** T = clamp(round(min(viewW, viewH) / 15), 24, 52) CSS px. A 390 x 844 phone gets 26; landscape 844 x 390 gets 24; a 1600 x 993 desktop gets 52.
- **Camera:** it follows you with 1.2 tiles of lookahead along your facing (none under reduced motion). It eases with factor 0.2 per frame (render only), snaps to whole device pixels and is clamped to the board plus 1 tile. On coarse pointers in portrait, you sit 42% of the way down the view, so thumbs never cover you.

### 16.2 Draw order, each frame (render only, no allocation)

1. Clear #000. Clip to the view rectangle.
2. **Memory walls:** for remembered wall segments not currently seen, single #8c8c8c lines, one path. Remembered slabs are dotted.
3. **Seen walls** (visible or lit): `groove()` double line (#e6e6e6 outer, black channel, half-width 0.2 T), all batched in one path, stroked twice.
   - Wall segments run between the centres of adjacent wall tiles, as in Run's `R_board`.
   - A segment is drawn in the seen style if both of its tiles are seen; in the memory style if both are remembered; otherwise as a half segment from the known tile.
4. **Light edge:** a #b8b8b8 1 px crossbar on each tile edge between a visible floor tile and a non-visible floor neighbour. The stepped edge of your sight.
5. Courts: torch brackets and flames (seen), claimed floor discs, the level 3 floor notch.
6. Rings and the Great Ring (10.2), tesserae and slab warnings (seen only).
7. **Sound fronts** (9.2).
8. The ball, or its last-known marker; the aim line.
9. **You:** a black head disc (radius 0.16 tile, white outline) inside a thick white U, the hip yoke (radius 0.28 tile, 2 px), opening toward your facing. Marked: the U has a 50 degree gap on one side. Protected: the U is drawn in outline only. The touch stick ring.
10. **The Stone Face:**
    - full drawing if its tile is seen or lit;
    - otherwise its eyes only, while it sees you;
    - the echo ghost;
    - the level 5 gathering outline.
11. **Terror brackets:** four step-fret brackets (`FRET` motifs, `groove`) in the view's corners. Band 0 to 4 by the Stone Face's path distance to you (`DF`): over 20, 20 or less, 14, 9, 5. Each band adds one stair to every bracket and moves it one fret unit inward. Hysteresis is 1 tile and the minimum hold 0.6 s. It is a change of shape, never of brightness. `terror {band}` fires on change. aria "The Stone Face is near." on entering band 4, at most once per 10 s.
12. Edge markers (ball, courts), and the level 3 turn clock.
13. The side bands in the gutters (cached blit, as now).

**Ink:** #fff (you, the ball, open eyes, claimed rings, aim line), #e6e6e6 (seen carving, fronts, the Stone Face's features), #b8b8b8 (light edge, ghost, markers, the sleeping Great Ring), #8c8c8c (memory, mosaic seams), #000. Nothing darker than #8c8c8c carries information. The ink values live in one `INK` object: if the owner's display mushes the memory lines, raise memory to #b8b8b8 in one place.

### 16.3 HUD (exact)

- `Level <b>n</b>/5`, then the score.
- Then `Rings` followed by one `.dot` per side ring (filled = claimed). In the finale the label becomes `Silence` and the dots show the rings still sounding.
- Then the attempt dots, as now, with `aria-label="n left"`.
- When marked: `<i class="yk"></i><span class="sr">Marked</span>` (a small U glyph in CSS with a gap).
- The pause button.

---

## 17. Text (added to TEXT; no em or en dash; plain register)

```js
echo: 'Echo',
echoDesc: 'Strike the ' + OLLI + ' to see the dark. The Stone Face hears every knock.',
echoNote: 'A tense chase in the dark. No gore.',
echoHint: 'Arrows or the mouse to walk. Space or click to strike. Hold Space to aim.',
echoTouch: 'Drag anywhere to walk. Tap to strike. Drag a second finger to aim.',
echoLv: ['The stone face', 'Fallen tesserae', 'The turning face', 'The moving stones', 'The gathered face'],
echoTw: ['Every knock lights the stone around it. Every knock is heard.',
         'Pieces of its mosaic come loose. If one is touched, it hears.',
         'It turns on a rhythm. While it faces, it cannot move. While it moves, it cannot see.',
         'Some stones slide open and shut. Your memory of them may be wrong.',
         'It gathers where the loudest knock was. Watch for its outline.'],
temper: ['It listens.', 'It watches.', 'It waits.'],
law: 'The Stone Face. If you can see its eyes, it can see you.',
firstCourt: 'A lit court. Strike the ' + OLLI + ' through its stone ring.',
reach: 'The ' + OLLI + ' is out of reach.',
claimed: 'Ring claimed. This court is safe ground.',
ringStone: 'The ' + OLLI + ' struck stone.',
sees: 'The Stone Face sees you.',
lostYou: 'The Stone Face lost you.',
wakes: 'The Stone Face wakes.',
near: 'The Stone Face is near.',
corners: 'Turn corners. Corners slow the Stone Face.',
plays: 'It plays the ' + OLLI + ' back.',
waits: 'It will not enter a claimed court.',
marked: 'The Stone Face touched you. Once more and it turns you back.',
turned: 'The Stone Face turned you back.',
greatOpen: 'Every ring is claimed. The Great Ring is open. The rings will fall silent one by one.',
silentOne: 'A ring fell silent.',
silentAll: 'The rings fell silent.',
letPass: 'The Stone Face lets you pass.',
unseen: 'Unseen.',
tessera: 'A tessera clicked. It heard that.',
echoDone: 'The labyrinth lets you pass.',
closeup: 'Close-up',
rings: 'Rings', silence: 'Silence', markedSr: 'Marked'
```

- Kept and shared: `soft` ("Too soft. Strike it through."), `paused`, `resume`, `restart`, `close`, `about`, `back`, `clear`, `replay`, `other`, `best`, `noBest`, `over` ("Rest now. The court will wait."), `level`, `of`, `score`, `calm`, `assist`.
- **Level start:** "Level 2 of 5. Fallen tesserae. It watches." for 2.6 s (level 1: 4.5 s, with the hint appended). It is followed by `echoTw[L]` for 3.4 s.
- **First-time captions** (once per session each, in this teaching order on level 1): `echoTw[0]` on the first strike, `firstCourt` on first seeing a court, `law` on the first eyes, `corners` on the first Rush, `waits` on the first Wait, `plays` on the first Play.
- **Failure lines:** `turned` and `silentAll`, followed by " 2 left." as now. Then the existing 0.8 s beat (skipped under reduced motion).
- **Clear:** `letPass`, then "Level clear. +n", with `unseen` appended when earned.

---

## 18. onSound hooks (the owner makes all audio in Ableton; the game never makes sound)

- The game calls `ZTH_GAME.onSound(name, data)`. `data` is **one reused object**, so the host must copy what it needs during the call.
- Positional events carry `pan` (-1 to 1, from screen x within the view) and `dist` (0 to 1, the path distance from you divided by 24, capped).
- Shared hooks are unchanged: `pause`, `resume`, `level-clear`, `run-end`. New shared hook: `nation-card {id, where}` (where is title, card, about or result), for an optional quiet cue.

| Name | Data |
|---|---|
| `beat` | `{n, period: 0.5}` every 0.5 s of play, the Stone Face's glide cycle, so music can lock to it |
| `pat` | `{pan, dist}` |
| `strike` | `{pan}` |
| `aim` | when precise aim starts |
| `bounce` | `{v: 0 to 1, pan, dist}` |
| `ball-rest` | when the ball stops |
| `ring-hit` | `{pan, dist, great}` a miss on stone |
| `ring-soft` | |
| `ring-claim` | `{n, of}` |
| `safe-enter`, `safe-leave` | |
| `great-open` | `{pan, dist}` |
| `ring-silent` | `{left}` |
| `rings-fell` | all silent |
| `great-pass` | |
| `terror` | `{band: 0 to 4}` on change only |
| `face-wake`, `face-step`, `face-turn`, `face-listen`, `face-hear`, `face-search` | `{pan, dist}` |
| `face-eyes` | `{step: 1 to 3}` |
| `face-rush`, `face-lost`, `face-cut`, `face-wait` | |
| `face-play`, `face-return-strike` | `{pan, dist}` |
| `face-rest` | eyes close after the last pass |
| `marked`, `caught`, `closeup` | |
| `tessera-drop`, `tessera-click` | `{pan, dist}` (level 2) |
| `turn-tell`, `turn` | `{still}` (level 3) |
| `stone-warn`, `stone-move` | `{pan, dist, open}` (level 4) |
| `gather-tell`, `gather` | `{pan, dist}` (level 5) |

`face-step` fires at most 4 per second.

---

## 19. Nations of today (never on the hunter)

### 19.1 The rule

Nations appear only on calm, static, solid panels: the **title herald**, the **between-level card**, **About**, and the **result of a won run**. They never appear:
- during play, on the HUD or the canvas;
- on the pause screen, or at a failure beat;
- on the result of a lost run;
- near, on or named with the Stone Face or any trial;
- as collectibles, objects, enemies, scores, rewards, seeds or level names.

The game loop is stopped whenever a card shows. Cards are framed by a plain 1.5 px #b8b8b8 rule, **never by the step-fret**: that ornament is Mesoamerican and Southwest, and it must not be imposed on Arctic, Pacific or other nations.

### 19.2 Data, loading, validation

- **Contract** (from the parallel data job): `{"nations":[{"id","name","also":[...],"pronounce":null|{"text","source_url"},"lands","countries":[...],"official_url","facts":[{"text","kind","as_of","source":{"title","publisher","url","accessed"},"evidence"}]}]}`. Optional fields used if present: top-level `"updated"` (YYYY-MM-DD) and per-nation `"region"` (asked of the data team). `evidence` is never shown.
- **Source:**
  - `opts.nations` as an array (the host has already loaded it), or a URL string.
  - Otherwise `'nations.json'` resolved against the game file.
  - It is requested **only inside `open()`**, with XMLHttpRequest and a 3000 ms timeout, and only if the resolved URL's origin equals `location.origin`.
  - The request is aborted in `teardown()`, and a response that arrives after `close()` is ignored.
  - Responses over 512 KB are refused.
- **There is no list in code and no fallback data.** If loading fails or nothing validates, the herald is hidden, cards are skipped, and About says: "The nations list could not load. Nothing is shown rather than something unchecked."
- **Validation per entry** (failures are dropped, never repaired):
  - `id` matches `^[a-z0-9-]{1,64}$`; `name` is 1 to 80 characters; `lands` is 1 to 200; `countries` is an array of 1 to 6 strings of up to 60.
  - `also`: up to 6 strings of up to 80.
  - `official_url`: https only, or the button is omitted.
  - `pronounce`: shown only if `text` is 1 to 80 characters and `source_url` is https; otherwise ignored.
  - Each fact needs:
    - `text` of 1 to 300 characters;
    - `source.url` https;
    - `source.publisher` of 1 to 120 characters, and a `source.title` of up to 200;
    - `source.accessed` in YYYY-MM-DD form and not after tomorrow.
  - Each fact may have an optional `kind` (up to 24 characters, shown as given) and an optional `as_of` (YYYY, YYYY-MM or YYYY-MM-DD).
  - A nation with no valid fact is dropped. At most 600 nations are kept.
- **Safety:**
  - All strings are inserted with `textContent`, never `innerHTML`.
  - Links get `target="_blank" rel="noopener noreferrer"`.
  - As a last guard, U+2013 and U+2014 in data become ", ".
- **Facts are never edited, shortened or paraphrased.** Names show exactly as given: the card name style overrides the panel's `text-transform` and `letter-spacing` to `none` and `normal`, so self-names, casing and diacritics are kept.

### 19.3 Rotation (renews daily, the same for everyone, every nation gets turns)

- **P** is a permutation of the valid nations: a Fisher-Yates shuffle with `rng(hashStr(updated || 'nations'))`, then interleaved round-robin by `region` (or by first country if there is no region), so no region dominates.
- **d** = whole days from 2026-01-01 to today's local date. N = number of nations.
- **Herald** shows P[(6d) mod N]. Transition card k (1 to 4) shows P[(6d + k) mod N]. Next and Previous step by 1. Everyone sees the same nations on the same day, and every nation comes round within N / 6 days.
- **Fact index** = (d + k + seen[id]) mod facts.length. `seen` is stored per id in `localStorage` under `zth_olli_seen` inside try/catch, capped at 600 ids. If storage fails, the fact still changes daily.
- None of this touches game seeds and none of it uses Math.random.

### 19.4 Where and how they appear

**Card anatomy** (the same component everywhere):

```
INDIGENOUS NATIONS TODAY                 13 px, letter-spaced label, #b8b8b8 (our label, not a name)
{name}                                   24 px, #fff, no text-transform
Also known as {also, joined by ", "}     15 px #e6e6e6, omitted if empty
Say it: {pronounce.text}  Pronunciation from {host of source_url}   only when sourced, link
{lands}. {countries joined by ", "}.     15 px
{KIND}  {fact.text}                      16 px; the kind as a small label
As of {as_of}.                           only when present
Source: {publisher}, {title}. Checked {accessed}.     link to source.url; always visible
Checked over a year ago.                 only when accessed is more than 365 days before today
```

1. **Title herald** (under the settings row, so the game controls come first in focus order):
   - Buttons: **Previous**, **Next**, **Pause** (`aria-pressed`; reads Play when paused), **Nation's site**.
   - It auto-advances every 14 s with a 150 ms opacity fade out and in. It is a cut under reduced motion, and under reduced motion it does not auto-advance at all.
   - Auto-advance also pauses while the pointer is over the herald or focus is inside it. The Pause control meets WCAG 2.2.2.
   - The region is `aria-live="off"` while advancing on its own, and `polite` after Next or Previous, which announce "{name}. {lands}."
   - A last line: "List updated {updated or newest accessed date}. {N} nations."
2. **Between levels** (both modes; skipped if `opts.nationCards === false` or there is no data):
   - After the level-clear beat, a solid panel shows "Level n clear. Score {score}." then the card.
   - Buttons: **Continue** (focused), **Another fact**, **Nation's site**, **Close**.
   - There is no timer and no auto-advance. Reading time belongs to the reader.
   - The polite live region reads once: "Indigenous nations today. {name}. {fact} Source: {publisher}. Checked {accessed}."
   - The next level's name, trial and temperament appear only after Continue, as the in-game caption. A nation and the hunter's trial never share a screen.
3. **About:** an "Indigenous nations today" section with the full list in alphabetical order (`localeCompare`), each name a button that opens its card in place (with Back). Then the dataset line, the method line and, if `opts.contact` is given, "To correct or remove an entry, write to {contact}." If `opts.nationsPage` is given, a link to the full list with every source.
4. **Result of a won run:** "Nations you met this run" followed by their names, each a button opening the card. There is nothing on the result of a lost run.

Each card shown emits `nation-card {id, where}` and increments `seen[id]`.

---

## 20. About text and TERMS (exact)

**About lines, in order** (lines 1 to 3 unchanged; old line 4 about Ahuizotl removed):

1. "Ōllamalīztli is the Nahuatl name for the Mesoamerican ballgame, played for more than three thousand years from Mexico to Central America, with ballcourts as far north as present-day Arizona."
2. "Ulama, its descendant, is still played today in Sinaloa, Mexico."
3. "The step-fret, xicalcoliuhqui in Nahuatl, is carved and woven by many peoples, from Mitla in Oaxaca to the Pueblos of the Southwest, each with its own names."
4. "The Stone Face in Echo is an original design made for this game. It draws on the stone masks of Teotihuacan, which were not made to be worn and whose eyes and teeth were once inlaid with shell and bone, and on the obsidian and pyrite that Mesoamerican artists used for shining pupils. It stands for no god, no person and no living tradition. It keeps the labyrinth, and the trial is to pass it."
5. "Xāyacatl is a Nahuatl word for face and for mask."
6. "Ocote, the resinous pine that lights the courts, takes its name from the Nahuatl ocotl."
7. "Mask making is a living art in Mexico today, from the dance masks of Guerrero to the carved wooden masks of the Parachicos of Chiapa de Corzo, which UNESCO added to its list of intangible cultural heritage in 2010. The Stone Face copies none of them."
8. "Indigenous nations today: each card shows one fact with its source and the date it was checked. Facts come from each nation's own published sources where possible, and from public records otherwise. Corrections are welcome."
9. "Sources: INAH; Saint Louis Art Museum; Karl Taube, The Iconography of Mirrors at Teotihuacan; UNESCO; Molina 1571 and Karttunen 1992 through the Online Nahuatl Dictionary, Wired Humanities Projects, University of Oregon."
10. "Sound: David Garcia." (the owner confirms this wording before release)

Then the nations section (19.4).

**TERMS** (remove `ahuizotl`, `chinampa`, `cacao`; add):

```js
xayacatl: ['xāyacatl', 'face; mask', 'Molina 1571 f. 158r; Karttunen 1992 p. 322; Online Nahuatl Dictionary'],
ocotl: ['ocotl', 'pine, fatwood, a pine torch', 'Online Nahuatl Dictionary, entry ocotl']
```

`tlachtemalacatl` stays, with its existing note that an independent source is still pending (DESIGN.md).

---

## 21. Scoring, failure, results

### 21.1 Points

| Event | Points |
|---|---|
| Side ring claimed | 1000 x level |
| Great Ring pass | 2500 x level |
| Silence time left at the pass | 20 per second (the whole remaining silence clock) |
| Make it play | +150, at most 3 per level |
| Time | 10 per second under par |
| **Unseen** (its notice never reached 1 this level) | +500 x level, label "Unseen." |
| Clean level (never marked or turned back) | x1.5 on that level's total |
| Attempts left at the end of a won run | 2000 each |

**Par** = 2.2 x route / walk. The route is the path length from the Entry through each side court (in greedy nearest order, mouth to mouth through the court) to the Great Ring, computed at generation. Stealth, speed and leaving sanctuaries are all rewarded, so hiding in a claimed court costs points.

### 21.2 Failure and results

- Three attempts per run, as in Drop.
- Failure lines: "The Stone Face turned you back." and "The rings fell silent."
- The result screen is unchanged in structure: Replay this court, New court, Other mode, Close. A won Echo run reads "The labyrinth lets you pass."; a lost one reads "Rest now. The court will wait."
- The best score is stored as `zth_olli_best_echo` in try/catch. Assist runs are not saved as best.

---

## 22. Accessibility

- **Shell unchanged:** dialog role, focus trap (nation links and buttons are inside it), returned focus, `inert` siblings, Escape rules, keys with Ctrl, Meta or Alt ignored, 44 px buttons, a visible focus ring.
- **aria-live, events only, never per frame:**
  - level start with the trial and temperament;
  - "The Stone Face wakes.";
  - "The Stone Face sees you." (at most once per 8 s) and "The Stone Face lost you.";
  - "The Stone Face is near." (at most once per 10 s);
  - ring claimed with rings left;
  - marked;
  - turned back with attempts left;
  - Great Ring open;
  - each ring falling silent with rings left;
  - pass and clear;
  - nation cards;
  - result.

  At least 2 s pass between messages about the Stone Face.
- **Reduced motion:**
  - Calm on by default, Close-up off, no camera lookahead;
  - text and herald fades become cuts, and the herald does not auto-advance;
  - the ball's rolling arc and the tessera rotation are static.

  Motion that carries information stays: the sound fronts, eighth-step turns and the gathering steps are already discrete or slow lines.
- **No flashing:**
  - knock light holds at least 0.5 s and extends rather than relights;
  - the eyes have a 0.5 s minimum hold either way, with hysteresis, at a line-of-sight boundary;
  - terror bands hold at least 0.6 s.

  No area changes brightness more than twice per second. Every warning is a shape change: slab to face, closed lid to open eye, pupil steps, the mouth opening, bracket steps, tick bars, dotted memory.
- **Not by grey alone:**
  - seen walls are a double line, remembered walls a single line, remembered slabs dotted;
  - claimed rings are filled with a floor disc, unclaimed rings are outlines;
  - marked shows as a gap in the yoke, protected as an outline yoke;
  - your sound fronts are lines, you-only fronts are hollow ticks.
- **Motor:** two inputs, aim snap, corner slide, a floating stick anywhere on the view, tap anywhere to strike, no chords, Calm pace, Assist.
- **Content:** "A tense chase in the dark. No gore." sits on the mode button, and the Close-up switch is on the pause screen.
- **Honest limit:** a visual stealth chase cannot be fully played by screen reader yet. Everything outside play (title, nations, About, results) is fully accessible. The positional onSound hooks (`face-step`, `face-turn`, `terror`, `bounce` with pan and dist) give the owner what he needs to build an audio layer that could make Echo playable by ear. Drop stays the more accessible mode, and the title never claims otherwise.

---

## 23. Bots and test targets

### 23.1 Harness

- Dev hooks: `API._tick(n, bot)`, `API._inp`, and a new `API._echo()` returning a read-only view: you, ball, face {x, y, f, st, m, ramp}, grid, zone, slabs, rings, tesserae, timers.
- Every target runs headless in node over **500 seeds per level** (levels started directly with `API._lv(L)`), and is rechecked in the browser with `rec_game.py`.
- **Reaction delay:** each bot perceives the world through a ring buffer of snapshots delayed by R steps. The targets are given for **0 ms** (R = 0) and **120 ms** (R = 14 steps, 116.7 ms).
- **Bots:**
  - **Idle:** stands at the Entry with the ball.
  - **Naive:** dribbles the shortest path to the next court, strikes when snap-aligned, ignores the Stone Face, and walks to the Great Ring in the finale.
  - **Good:** knows the map; avoids the Stone Face's cone and path; waits out Listen in the dark (standing still); flees into stepped corridors when its notice reaches step 1; uses Make it play when it is in Rush within 3 tiles; shelters in claimed courts; in the finale, times the patrol or decoys with a strike and recovers the ball.
  - **Shot:** takes Great Ring shots with 60 ms of timing noise.
  - **Solver:** perfect information, 0 ms, no Assist; searches strategies per seed.

### 23.2 Targets (normal pace, no Assist; "clear" = the level cleared within 3 attempts)

| Target | L1 | L2 | L3 | L4 | L5 |
|---|---|---|---|---|---|
| Good bot clear, 0 ms | >= 97% | >= 93% | >= 88% | >= 82% | >= 72% |
| Good bot clear, 120 ms | >= 93% | >= 88% | >= 80% | >= 72% | >= 62% |
| Gap between 0 ms and 120 ms | <= 12 points | <= 12 | <= 12 | <= 12 | <= 12 |
| Good bot, times turned back per cleared level (mean), 0 ms | <= 0.15 | <= 0.25 | <= 0.35 | <= 0.50 | <= 0.70 |
| Good bot, times turned back per cleared level, 120 ms | <= 0.30 | <= 0.40 | <= 0.55 | <= 0.70 | <= 0.95 |
| Good bot, chases escaped with no contact, 0 ms | >= 75% | >= 70% | >= 62% | >= 55% | >= 50% |
| Good bot, chases escaped with no contact, 120 ms | >= 65% | >= 60% | >= 52% | >= 45% | >= 40% |
| Naive bot clear, 0 ms | 25 to 50% | 15 to 40% | 10 to 30% | 5 to 25% | <= 15% |
| Naive bot clear, 120 ms | 20 to 45% | 10 to 35% | 5 to 25% | <= 20% | <= 12% |
| Naive bot, contacts per level attempt (either delay) | >= 0.8 | >= 1.0 | >= 1.1 | >= 1.2 | >= 1.3 |
| Shot bot, Great Ring pass per attempt, 0 ms | >= 95% | >= 70% | >= 65% | >= 65% | >= 55% |
| Shot bot, Great Ring pass per attempt, 120 ms | >= 90% | >= 60% | >= 55% | >= 55% | >= 45% |
| Good bot median level time, 0 ms | 70 to 120 s | 80 to 135 s | 95 to 155 s | 105 to 175 s | 120 to 200 s |
| Solver: seeds cleared | 100% | 100% | 100% | 100% | 100% |

More targets:
- **Idle bot:** the first full notice comes after 20 to 60 s on level 1 (median), never before 15 s.
- **Chases:** median 8 to 16 s; at most 2% over 40 s; none over 90 s (the ramp, corner learning and loop reversal end them).
- **Human playtest:**
  - Level 1 cleared without losing an attempt by about 70% of first-time players.
  - The full run completed by 25 to 35% (Calm: about 50%).
  - First tests at 390 x 844 portrait and landscape, and on the owner's display.

### 23.3 Hard asserts (every bot run, every tick; any failure fails the build test)

- No contact unless notice reached 1 in this chase after a fill of at least Tn (Calm x1.4, Assist x1.5), with the eyes drawn for that whole fill.
- No contact on a safe-ground tile, through a wall, during protection, or in Wait. The first contact is always a mark, never a turn-back.
- The Stone Face never wakes, returns, gathers or is placed within 6 path tiles of you or on a tile in your sight.
- Patrol glide speed and investigate speed are below your walk on every level. The level 3 blind move is exempt, because it cannot see.
- Every lit tile stays lit at least 0.5 s once lit; no tile goes from dark to lit to dark to lit within 1.0 s.
- The eyes never toggle twice within 0.5 s.
- No `NaN` in positions; the facing is always one of the 8 vectors.
- No per-frame allocation in the dev build's allocation counter during play.

### 23.4 Generation and determinism

- 500 seeds x 5 levels: median tries 1, 99th percentile at most 5, fallback at most 0.5%, and every produced board (fallback included) passes V1 to V7 and V9. Generation takes at most 8 ms per level at 4x CPU slowdown.
- **Determinism:** the same court code and the same recorded input tape give the same hash of (you, ball, face, m, rings, score) at every level end, in Chrome, Firefox and Safari. A grep gate fails the build if `Math.sin`, `Math.cos`, `Math.atan2`, `Math.pow`, `Math.exp`, `Math.log` or `Math.random` appear inside the Echo logic block (marked `/*L*/ ... /*L*/`), except `Math.random` in `start()` for New court.
- Teardown mid-level: 0 listeners, 0 rAF, the style removed, `inert` removed, focus returned, the nations request aborted (dev counter).

---

## 24. Feasibility (ES5, Canvas2D, one file)

### 24.1 Reused as is

The shell, API, panels, focus trap, seeds and codes, `mix`/`rng`/`enc`/`dec`/`today`, the fixed-step loop and `beat` flow, `cap`/`say`/`fail`/`clearLevel`/`result`, `groove`, `line`, `motif`, `band`, `drawBand`, `ball`, `gateArt`, `chev`, `bfs` and `nb` (generalized to w and h), `deg`, `repair` (unmirrored), Drop's `cpt`/`cseg` (generalized to any body and boxes), and the HUD and caption machinery.

### 24.2 Per frame at 390 x 844 at 2x, 4x CPU slowdown (target 60 fps; script time at or under 8 ms median, 12 ms at the 95th percentile)

- **Walls:** about 17 x 35 window tiles. One groove path (two strokes) and one memory path, with direct `moveTo`/`lineTo` from the grid and no point arrays.
- **Visibility:** not per frame. 128 rays x at most 12 tiles, only on a tile change, a slab change or a claim (about 5 per second while walking).
- **Knock light:** one ray-chain pass per merged knock (at most a few per second).
- **Waves:** BFS on emission only (at most 999 tiles). Drawing checks window tiles x active fronts, at most about 4800 cheap checks.
- **The Stone Face:** one LOS supercover line per step; `DT` rebuilt on a target change; `DF` rebuilt on its own tile change; at most about 200 path operations to draw, and the mosaic is skipped below 48 px.
- **Allocation:** none per frame. The sound-data object, the wave pool, the tesserae (Float32Array(3 x 14)), the junction list (Int16Array(64)) and the mosaic seams (Float32Array) are allocated per level.

### 24.3 Size

| Part | Minified KB |
|---|---|
| Generator: rooms, carve with fret zones, join, braid, cap, slabs, validation, pillar fallback | 5.5 |
| You: movement, collision, corner slide, dribble, strike, aim, snap | 3.0 |
| Ball physics, knocks, ring pass tests, Great Ring motions | 3.0 |
| Visibility, knock light, memory, lit courts | 2.0 |
| Waves, hearing, echo ghost | 1.8 |
| Stone Face AI: states, notice, rush, corners, ramp, loop reversal, play, wait, return, listen, temperament | 5.0 |
| Trials: tesserae, turning, stones, gathering | 2.8 |
| Drawing: walls, edge, courts, torches, rings, you, fronts, brackets, markers, turn clock | 4.0 |
| Stone Face art: outline, band, eyes, nose, mouth, mosaic, edge and back, ghost, close-up, gathering | 2.5 |
| Input: stick, second-finger aim, mouse walk, keyboard plant | 1.2 |
| Text, terms, About | 2.2 |
| Nations: load, validate, rotate, herald, card, list, CSS | 4.0 |
| **New total** | **about 37** |

- Run removed is about 16.5 KB, so the shell plus Drop is about 29.5 KB. Projected file: **about 64 to 67 KB minified, about 25 KB gzipped**, under the 70 KB ceiling.
- **Build gate:** the build fails over 72 000 bytes of minified JS and prints the size every run.
- **Cut order if over:**
  1. the Close-up (0.4 KB);
  2. the About all-nations list (1.2 KB; the herald still has Next and Previous);
  3. the echo ghost (0.4 KB);
  4. keyboard precision aim (0.4 KB; tap aim and snap remain);
  5. the second-finger aim stick (0.4 KB; the flick remains).

### 24.4 Build order

1. Generator and validator with the 500-seed sweep.
2. Movement, ball, dribble, strike, ring pass.
3. Visibility, knock light, memory, waves.
4. Stone Face core states, notice and eyes, then contact rules.
5. Level 1 end to end, with the good and naive bots.
6. Finale and Great Ring variants.
7. Trials 2, 3, 4, 5.
8. Stone Face art and the close-up.
9. Nations layer.
10. Tuning against section 23.
11. Recorded clip with `rec_game.py` for the owner.

---

## 25. Fixes for every fatal flaw the judges named

| Flaw (judge) | Fix in this design |
|---|---|
| Echo: no anti-loop counter on stepped corridors (1) | Chase ramp (11.6), corner learning (11.7), loop reversal (11.8). Frets stay an escape but not an infinite one. Chase-length targets in 23.2. |
| Echo: Play fires the ball away, making a fetch (1) | Play returns the ball toward your last claimed court at 5.5 tiles/s (about 7 tiles at most), 11.9. |
| Echo: drag-from-ball aim on phones; gesture conflict with hold-to-walk on a 9 px ball (1, 3) | No touching the ball. A floating stick anywhere, tap anywhere to strike, a second-finger aim stick or flick, and ring and Stone Face aim snap (6.4, 15). |
| Echo: sanctuary hiding (1, 2) | Wait shortens by level (4.0 to 2.5 s) and then it leaves; the finale silences sanctuaries one by one; par and the Unseen bonus reward leaving (10.3, 10.4, 21.1). |
| Echo: the transition panel shows the next trial with the nation card (2, 3) | The trial is named only in the in-game caption after Continue (19.4). |
| Echo: Lock widens pupils to a thin rim, a skull read (2) | Pupils **shrink** in three hard steps (0.034 to 0.018), and shell whites are always filled (11.1, 11.5). |
| Echo: herald pauses only on hover or focus (1, 2, 3) | A real Pause button, aria-live off during auto-advance, no auto-advance under reduced motion (19.4). |
| Echo: level 5 mosaic must not read as shattering (2) | It gathers at the destination in four steps and is simply gone from the origin; it never breaks (12.5). |
| Echo: ear spools contradict the research (3) | Drilled holes on rectangular ear tabs, with no ornament (11.1). The hearing tell is the Listen sweep. |
| Echo: no deterministic generator fallback (3) | The pillar-field fallback after 30 tries, always valid (14.2). |
| Echo: level 4 runs two hunter AIs (3) | Level 4 is the moving stones, with one Stone Face (12.4). |
| Echo: knock-lit tiles could flicker on the lifted-black display (3) | A 0.5 s minimum hold, extension rather than relight, a lit-to-memory change of shape rather than to black, one `INK` constant to raise memory grey, and a check on the owner's display (7.1, 16.2). |
| Mask: empty eye sockets read as a skull (1, 2) | Closed eyes are lid lines; open eyes are always filled; the ghost has no eyes (3, 11.1). |
| Mask: a one-to-one DbD mapping (1, 2, 3) | No generators, skill bars, pallets, windows, hooks or exit levers. Ball-native verbs and an inverted perception model (2). |
| Mask: 720-ray clip per frame, heaviest render (1, 3) | Per-tile visibility recomputed on a tile change only, with no clip polygon (8.1, 24.2). |
| Mask: pause screen shows a nation over the canvas (2) | No nations on the pause screen (19.1). |
| Mask, Echo: "mosaic comes apart" reads as broken (2, 3) | Lost tesserae are bare stone, loose tesserae are small and aged, and gathering never scatters (11.1, 12.2, 12.5). |
| Dark Court: grid-locked Pac-Man movement (1, 2) | Free 8-way and analog movement with a corner slide (6.1). |
| Dark Court: slit eyes plus cords at the back, Xipe Totec attributes (2) | No slit eyes (the pupils shrink, the almond stays whole); the back has no cords (3, 11.2). |
| Dark Court: a black body column implies a wearer (1, 2, 3) | No body of any kind (3). |
| Dark Court: the stock stealth kit (heartbeat, stamina, torch toggle) (1, 2) | None of these. Terror is the step-fret brackets; light comes from your own knocks. |
| Dark Court: too many verbs and overlays on phone tiles (1, 2, 3) | Two inputs; one terror signal; no hatch, no breath arc, no heartbeat rings. |
| Dark Court: Startle full screen and on by default (1, 2) | The Close-up is not full screen, is static and small, is off under Calm and reduced motion, and has a switch (11.11). |
| Dark Court: trig from whole-degree facing (3) | 8 literal unit vectors and dot-product cones; no trig in logic (5, 11.3). |
| Dark Court: the defensive "It is not evil" caption (1, 3) | Not used. The framing lives in what it does and in About. |
| Fret: a ball rolling a grid maze is Pac-Man (1, 2) | You are a ballplayer with a free body; the ball is a separate physical object. |
| Fret: an embedded fallback nations list (1, 2, 3) | No nation data in code, ever (19.2). |
| Fret: the face in temple walls and sealing rooms, a haunted-temple trope (2) | No faces in walls, no sealing rooms, no traps that close behind you. |
| Fret: lines softening during rotation (3) | Nothing rotates. Turns are eighth-step cuts. |
| Fret: hollow ring pupils near Tlaloc's ringed eyes (2) | Pupils are always solid discs; ring shapes never appear on the face (3). |

---

## 26. Top risks

1. **Cultural misreading** (a frightening Mexican mask read as a demonized god or the cursed-artifact trope).
   - Mitigations: guardian and trial framing in every string; the exclusion list; an original geometry in one `FACE` object; About naming its sources and saying it stands for nothing real; Mexican institutions cited first; advisor review before wider release (section 27).
2. **Nations next to a horror mode feeling like tokenism.**
   - Mitigations: the strict placement rule, a plain frame, links to each nation's own site, a removal path, and `opts.nationCards = false` to move them to the title and About only if an advisor asks.
3. **Phone readability** of memory lines, fronts and a 39 px face on 26 px tiles. Mitigations: the level of detail below 48 px, one terror signal, the `INK` constant, and early tests at 390 x 844 and on the owner's display.
4. **Dribble feel** (the ball snagging at corners). Mitigations: the control spring, corner slide, wall touches counted as pats, and an early playtest. If it misfires, raise the spring to 8 and the control radius to 0.85.
5. **Fairness of a faster hunter in the dark.** Mitigations: the eyes law, the notice floor, two touches, safe ground, the hard asserts and both reaction-delay targets. Expect two tuning passes.
6. **Size creep.** Mitigations: the 72 KB gate and the cut order.
7. **Determinism drift.** Mitigations: no trig in logic, the grep gate, cross-engine tape hashes.
8. **Data honesty.** "Live" means the JSON is refreshed and every card shows its checked date; stale facts are labelled; unsourced facts are dropped, never shown.

---

## 27. Questions for a community advisor (add to DESIGN.md section 12)

1. Is a stone guardian face, framed as a trial and never as evil or a god, acceptable to Nahua, Mexican and wider Indigenous audiences? Does any element (the inlaid eyes, the shell teeth shown when it hunts, the mosaic, the ear tabs, the brow) come too close to a sacred or specific mask?
2. Should the step-fret band sit on the Stone Face's brow, or should the shared ornament stay off the guardian? (One data change.)
3. Are xāyacatl and ocotl welcome in visible text, and with or without vowel length marks?
4. Are nation cards between the levels of a tense mode respectful, or should they live only on the title, About and result screens?
5. Should About name living mask makers and dance communities, with their consent, and can recognition or support flow back to them?
6. Who should review each nation fact, how should a removal request be handled, and how should cards be ordered?
7. Is the top-down ring jutting from the alley wall, with the ball passing along the alley, a fair stylization of ring mounting (already flagged in DESIGN.md)?

---

## 28. Sources

Marking: **[read]** means fetched and read in the research pass; **[index]** means seen only through a search summary, and must not be quoted in game text until opened.

- [read] Online Nahuatl Dictionary, Wired Humanities Projects, University of Oregon, **xayacatl**: "face; mask". Molina 1571, pt. 2, f. 158r, "cara o rostro, caratula o maxcara"; Karttunen 1992, p. 322, "face; mask"; Florentine Codex xaiacatl. https://nahuatl.wired-humanities.org/content/xayacatl
- [read in the concept passes, fetched 2026-10-08] Same dictionary, **ocotl**: "pine, especially high in pitch; fatwood; a torch". https://nahuatl.wired-humanities.org/content/ocotl
- [read] Saint Louis Art Museum, Teotihuacan mask: not designed to be worn by individuals; drilled hollows held shell and bone inlays for eyes and teeth. https://www.slam.org/collection/objects/36955/
- [read] Karl Taube, "The Iconography of Mirrors at Teotihuacan" ([1992] 2018): pyrite, mica and obsidian represent the shining pupil; mirror stones used for eyes across Mesoamerica. https://www.mesoweb.org/publications/Works1/Taube[1992]2018a.pdf
- [read] INAH, Boletín 257, 8 May 2024: dance masks of Guerrero. https://inah.gob.mx/images/boletines/2024/257/Boletin%20257.pdf
- [read] UNESCO, Parachicos in the traditional January feast of Chiapa de Corzo (Representative List, 2010). https://ich.unesco.org/en/RL/parachicos-in-the-traditional-january-feast-of-chiapa-de-corzo-00399
- [read] INAH, Templo Mayor Museum, stone masks in offerings (consulted for what **not** to use: funerary placement). https://lugares.inah.gob.mx/en/node/5284
- [read] World History Encyclopedia, the Xiuhtecuhtli mask (consulted for what not to resemble). https://www.worldhistory.org/article/641/the-mask-of-xiuhtecuhtli/
- [index] The Met, Teotihuacan stone masks 310647 and 312736 (an idealized face type; probably not worn). Not quoted.
- [index] MNA, Malinaltepec mask infographic; Smarthistory, the mosaic skull and Olmec masks; British Museum deity masks. Consulted only for the exclusion list.
- [read] W3C, Understanding WCAG 2.2 SC 2.2.2 Pause, Stop, Hide. https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html
- Carried over from DESIGN.md unchanged: ulama today, the ballgame, rubber and morning glory, the step-fret.

**Kept out of game text pending verification:** that stone yokes are carved versions of protective gear (Met, index only); that the Mexica believed antiquities were made by gods or giants (López Luján, unread); any claim about the source of turquoise; the court ring mounting (advisor).
