# /nations: the herald of names. Final buildable spec

Written 2026-10-10 for zotheos.org, worktree `C:\ZOTHEOS-Web-nations`, branch `feat/nations`, against the tree at
`1b53a81`. It takes the winning concept (the herald: a ceremony of naming), grafts the best of the atlas and the
ledger concepts, and fixes every flaw the three judges found. Where this document and `ARCHITECTURE.md` differ,
this document wins; section 0.3 lists each difference.

Writing rule for this document and for every string it specifies: no em dash, no en dash. Ranges read "4 to 12".
Dates in reading copy read "8 Oct 2026"; ISO dates live only in `datetime` attributes and JSON.

---

## 0. Ground truth, measured on 2026-10-10

### 0.1 The data (`data/nations/nations.json`, version 1, generated 2026-10-08)

| Measure | Value |
|---|---|
| Nations, facts, regions, countries | 450, 1,260, 15, 99 |
| Unique source URLs, publishers | 742, 372 |
| Official sites, sourced pronunciations | 190, 11 |
| Cross-border nations (more than one country), `also_search` carriers | 99, 3 (`huni-kuin-br-pe`, `qom-ar-py`, `yupik-chukotka`) |
| Facts per nation | 3: 333 nations, 2: 98, 4: 10, 1: 5, 5: 4 |
| Fact kinds | language 268, land 201, governance 200, today 180, culture 178, population 106, history 72, achievement 55 |
| Fact `status` | `verified` on all 1,260; `checked` = 2026-10-08 on all; `source.accessed` 2026-10-08 (1,080) or 2026-10-09 (180) |
| Facts with `as_of` null | 571 |
| Longest name, lands, fact | 54 characters (`Confederated Tribes of the Umatilla Indian Reservation`), 222, 198 |
| Tiers by ARCHITECTURE 2.3 | 154 A, 296 B, 0 C before overrides |
| Duplicate display name | `Samoans` twice (`samoans-american-samoa` in `alaska-hawaii-pacific-us`, `samoans-samoa` in `oceania`); lands and countries disambiguate |
| Named individual | Bhuri Bai in two of the three `in-bhil` facts (`in-bhil-78bae6a7` achievement, `in-bhil-c69ec23b` culture) |
| Dashes U+2013 or U+2014 anywhere visible | 0 |
| Reserved-id collisions (section 3.3) | 0; every id matches `^[a-z0-9]+(-[a-z0-9]+)*$`, longest 48 |
| Per-region shard, minified, publishable facts only | 18 to 46 KB raw, 5 to 13 KB gzipped (oceania the largest) |

Code points outside ASCII, by role (the fonts gate in section 11 is built from these, then re-measured on every build):

- Names: 35, in Latin-1, Latin Extended-A and B, IPA (ə ɫ ɬ), Spacing Modifier (ʷ), five combining marks
  (U+0302, U+0313, U+0328, U+0331, plus U+0328 in `Tłı̨chǫ`), Greek θ, Latin Extended Additional (ṉ ẽ), U+2019.
  Thirteen are missing from the upright Instrument Serif files: ǂ ǫ ə ɫ ɬ ʷ U+0302 U+0313 U+0328 U+0331 θ ṉ ẽ.
  **Ten names** therefore render whole in the fallback serif: ǂKhomani, Unangax̂, Mẽbêngôkre, Haíɫzaqv, Nisg̱a’a Nation,
  Sḵwx̱wú7mesh Úxwumixw, səlilwətaɬ, Tłı̨chǫ, xʷməθkʷəy̓əm, Aṉangu.
- Other names and pronunciations: 90, adding Cyrillic (35 letters), Cherokee (ᏣᎳᎩ), Canadian Syllabics (9 code
  points), click letters ǀ ǁ ǂ, ʻ ʼ ˊ ⁿ, middle dot. Sixty-one are missing from DM Sans.
- Lands and facts: 61; nineteen missing from DM Sans (ǂ ǫ ɫ ɬ ʉ ʔ ʷ ʻ, four combining marks, θ, ḷ ṉ ṟ ṯ ạ ẽ). Five
  `lands` lines and 31 facts need the reading fallback.
- Source titles and publishers: 103, adding Devanagari (18 code points, NFDIN Nepal) and more Cyrillic (RAIPON);
  68 missing from DM Sans. These appear on nation pages and the sources page, so a Devanagari face is required.
- Our mono labels: the region label `Alaska, Hawaiʻi and the US Pacific` carries U+02BB, which JetBrains Mono lacks
  (it has U+02BC). Section 11.2 gives it a mono fallback rather than dropping the okina.

Brand font metrics (fontTools, `OS/2.sxHeight` over `head.unitsPerEm`): Instrument Serif 0.510, DM Sans 0.526,
JetBrains Mono 0.550. The build measures the Noto faces the same way and derives `size-adjust` from the ratio.

### 0.2 The tools and the site, as they are

- `tools/csp_sync.py`: `PAGES = ("index.html", "download.html")`; `page_for_source()` maps a header source to a page;
  every inline `<script>` without `src` is hashed (JSON and speculationrules blocks included); only `script-src` is
  rewritten. Section 16.2 extends it to page groups.
- `tools/lint_copy.py`: bans U+2014 only; default files are the two root pages. Section 16.3 adds U+2013 and the
  nations pages.
- `tools/fonts_check.py`: exactly one `<style id="zth-fonts">` per page, identical across pages; every `.woff2` in
  `static/fonts/` must be named by the block; manifest `tools/fonts.sha256`; immutable cache rule for
  `/static/fonts/(.*)`; the preload must be a file the block uses. Section 16.4 extends it.
- `vercel.json`: `cleanUrls: true`, `trailingSlash: false`; hash-only `script-src` on `/`, `/index`, `/index.html`;
  `script-src 'none'` on `/download`, `/download.html`; `connect-src https://formspree.io` on the landing only.
- `data/nations/tools/nations_refresh.py`: states `verified | stale | unreachable`; writes `status` and `checked`
  on **every** outcome (lines 411 to 412) and never writes `source.accessed`. Flags: `--file --report-dir --limit
  --dry-run --host-interval --timeout --retries --run-date --ignore-robots`. User agent
  `ZOTHEOS-nations-verifier/1 (+https://zotheos.org)`. The only run so far: `--dry-run --limit 40` on 2026-10-10,
  40 of 742 URLs, 99 facts, 98 verified, 1 unreachable (minorityrights.org, HTTP 403).
- `data/nations/tools/validate.py`: `TOP_KEYS`, `NATION_KEYS`, `FACT_KEYS`, `SOURCE_KEYS` fixed sets; unknown keys
  are warnings; banned terms; rank words; AU personal-name pattern; dashes.
- `game/index.src.html`: caps at 524,288 response bytes and 600 nations (`natValid`), reads a same-origin URL by
  `XMLHttpRequest`, has `opts.nationsPage` and `TEXT.fullList` hooks. The game is not linked from the site.
- `index.html` anchors: first-paint theme and motion script at lines 28 to 46; `speculationrules` at 50; `zth-fonts`
  block from 60; tokens at 244 to 345; the Obsidian mono override block at 4141 to 4190 (`:root:not([data-theme])`
  resolves the ink ladder to `#FFFFFF / #C8C8C8 / #A3A3A3 / #8A8A8A / #4D4D4D`, `--rule rgba(255,255,255,0.16)`,
  `--surface #000000`); the Still rule at 5516; `.ap-opt` at 5449; header nav at 7187 (six links plus Menu); Menu
  sheet at 7201 (items `--i:0` to `--i:12`); day chip at 7181; footer columns at 8498 to 8522; the only `mailto:` at
  8539 (`contact@zotheos.org`); Roots and gratitude at 8543; the only Formspree form at 8427.
- No `.vercelignore` and no `.github/` exist. Today a merge of `feat/nations` would deploy `data/` and `game/`.
- Python 3.10.9 with `fonttools 4.63.0`, `brotli` and `pypdf` installed in the user site (not visible under `-I`);
  the build pins them in `tools/requirements-nations.txt` anyway.

### 0.3 Where this spec changes ARCHITECTURE.md

| ARCHITECTURE says | This spec says | Why |
|---|---|---|
| 2.1: one contract file per region under `data/nations/regions/` | One file, `nations.json`, in the shape validate.py checks; sidecars beside it | That is what exists; the shape stays for round 3 |
| 3.1: verifier `tools/nations_verify.py` updates `accessed` | `data/nations/tools/nations_refresh.py` is the verifier; it gains one additive field, `last_verified` (section 9.2) | `checked` is overwritten on failure, so no honest grace window exists without it |
| 3.3: states ok, grace, stale, review, human, removed | Tool states stay `verified`, `stale`, `unreachable`; the build derives the display states (section 9.1) | No tool rewrite |
| 3.5: two lanes, lane 1 direct commit | Pull-request mode only, until the owner decides (section 18) | Open decision 3 |
| 4.3, 7.1: files under `nations/api/` | Hub at `nations.html`; data under `static/nations/` | The task fixes these paths |
| 5.1 and the concept: names in the display serif, italic allowed | Names **upright**, never italic, never uppercased | BC Indigenous content guide: never italicize Indigenous names or terms; combining marks sit better upright |
| 7.3: a country map at launch | No map at launch; the region and country lists are the controls | Decoration deferred; hover fill broke the hover-neutral law |
| 8.3: credit "Map: Natural Earth" | Omitted until a map exists | Honesty |
| 9.1 "Safer still: no named individuals at launch" (advisory) | Applied: the two Bhuri Bai facts ship hidden under `overrides.json` pending the owner's decision | Hide first, ask second |

---

## 1. The idea in one paragraph

`/nations` opens on a flat black ground and names one nation at a time. Our region label appears first, small and
grey in mono. Then the nation's own name arrives large and upright, in the brand serif when the brand serif carries
every letter and whole in a self-hosted Noto serif when it does not, with every diacritic, click letter, syllabic and
combining mark exactly as the nation writes it. When the name has fully arrived, one hairline draws beneath it. Then,
in order: the other names it is known by, the pronunciation if and only if a source gives one, the lands, one checked
fact, and the receipt (publisher, year, the date the fact was last checked). The card dwells long enough to read,
fades, and the next nation is named. Everyone sees the same fifteen nations on a given day, one per region (the Daily
Ring); after that each device walks on alone and never repeats a nation inside a region until the region is
exhausted. Below the herald: today's ring as a list, a search that forgives missing accents but never alters a name,
the regions and countries, honest coverage, how the checking works, and the promise that corrections from nations
come first. Nothing on this page speaks. Nothing on this page scores. Every fact shows where it came from.

---

## 2. Decisions carried from the judging

From the winner (the herald), kept: the first-screen ceremony; our words never larger than the name; no fret, border
or box near a nation; the whole-name font rule decided at build and shipped in the shard; opacity-only fades and an
`inline-size` hairline that cannot blur at 1.25 scale; hash-only CSP; one shard fetched then two prefetched; the
live region filled only on user events; pause on hover, focus, hidden tab and off-screen.

Grafted from the ledger concept: `last_verified` and the human lane; the verification states `no-check`, `partial`,
`ok`, `overdue`; a verification page with "What a check cannot tell you"; the credits roll call; the For nations copy
"Your word outranks any registry here" and the line that no advisory circle exists yet; the name rule (a failed name
check never hides a nation); the same-origin scan of built output; the removed-nation handling (plain 404).

Grafted from the atlas concept: upright names with the reasoning "a name is a quotation, not our phrase"; the fold
table written once in Python and emitted to JavaScript with a parity test; no fuzzy matching; `also_search` searched
and never displayed; `countries.json` with ISO 3166 short names and the "present-day countries" line; country pages;
`nations_build.py --check`; `nations_links.py`; `.vercelignore` in stage 1; size budgets; the type sample page;
`dir="auto"` on every name element; results as plain links, not a combobox.

Flaws fixed (each with its section): italic names (11.1); the landing CSP widening and day-chip fetch (20: dropped);
hostname as pronunciation credit (4.2, 8.2); ring dots as a progress meter (4.3: position only, display only); no
verification page (9); controls not reading as controls at first paint (5.5); `/nations/index` header edge (16.1:
the hub is `nations.html`, never `nations/index.html`); inline CSS on 450 pages (12.3: one hashed stylesheet);
publishable rule dropping 403 hosts after the first run (9.2); missing `countries.json` (3.2); two-clock first card
(5.5); phone dot arithmetic (4.3); Devanagari in source titles (11.2); vendored font size stated (11.3); named
individual asserted absent (0.1, 3.2 overrides); advisory circle disclosure (10.3); `also_search` handling (7.1);
sample run presented as a full check (9.3); hidden-facts table naming nations (9.4: counts by default); the tombstone
page (8.4: 404); the correction mail body asking for a name for the log (10.2: removed); "Edited by" naming (10.1).

---

## 3. Files and URLs

### 3.1 Layout in the worktree

```
nations.html                                    the hub, served at /nations (cleanUrls). Never emit nations/index.html.
nations/<id>.html                     x 450     one nation, served at /nations/<id>
nations/region/<key>.html             x 15      one region, served at /nations/region/<key>
nations/in/<iso2>.html                x 99      one present-day country, served at /nations/in/<iso2> (lowercase)
nations/{about,sources,coverage,credits,verification,for-nations,changes}.html
static/nations/index.json                       data version, build date, regions, shard names, counts (section 15.1)
static/nations/<region>.<hash8>.json  x 15      herald shards, publishable facts only, immutable
static/nations/search.json                      search index, loaded on first focus
static/nations/status.json                      verification status (section 9.3)
static/nations/coverage.json                    coverage table
static/nations/news.json                        headlines; `{"shelf": false, "items": []}` while the shelf is hidden
static/nations/nations.<hash8>.css              the one stylesheet for every nations page
static/fonts/zn-*.<hash8>.woff2                 Noto subsets (section 11.3)
data/nations/nations.json                       source of truth (shape unchanged)
data/nations/regions.json                       NEW  display names, order, merge_into
data/nations/countries.json                     NEW  ISO 3166-1 alpha-2 -> short English name, all 99 codes
data/nations/overrides.json                     NEW  hide, takedown, rename, drop_also; applied last
data/nations/pronounce_publishers.json          NEW  pronunciation source host -> publisher name (11 entries)
data/nations/site.json                          NEW  contact, repo_public, check_mode, hidden_table_names_nations
data/nations/changes.json                       NEW  the public change log (empty at launch)
data/nations/redirects.json                     NEW  old id -> new id (empty at launch)
data/nations/verify/human.json                  NEW  human-lane records (empty at launch)
data/nations/verify/history.json                NEW  past runs (seeded with the 2026-10-10 sample run)
data/news/sources.json, data/news/flags.json    NEW  outlet registry; {"shelf_visible": false}
tools/nations_build.py                          data -> pages, shards, css, sitemap entries; runs the gates
tools/nations_fonts.py                          subsets the Noto faces; writes the names font block
tools/nations_lint.py                           data rules, glyph gate, banned terms, labels, no speechSynthesis
tools/nations_links.py                          every href resolves; every external link is https and cited
tools/nations_fold.py                           the search fold table (Python source of truth)
tools/nations_report_summary.py                 one-line summary of refresh_report.json for the PR title
tools/news_fetch.py                             feeds -> static/nations/news.json
tools/nations/templates/*.html                  hub, nation, region, country, about, sources, coverage, credits,
                                                verification, for-nations, changes
tools/nations/partials/{head,header,footer,fonts-brand.css,fonts-names.css,bootstrap.js,appearance.js,herald.js,tokens.css}
tools/fonts-src/                                vendored Noto TTFs with each OFL.txt (about 9 MB, never deployed)
tools/requirements-nations.txt                  fonttools, brotli, pypdf, pinned with hashes
.github/workflows/nations-refresh.yml           weekly re-check, pull-request mode
.github/workflows/news-refresh.yml              headlines; workflow_dispatch only until the shelf flag flips
.vercelignore                                   data/ tools/ game/ docs/ .github/ *.md
sitemap.xml                                     gains every indexable nations page between two comment markers
```

`cleanUrls: true` serves `nations.html` at `/nations` and `nations/<id>.html` at `/nations/<id>`. The build never
writes `nations/index.html`, so `/nations` has exactly one source file and the `/nations/(.*)` header entry never
reaches the hub. `trailingSlash: false` redirects `/nations/` to `/nations`. The first preview deploy confirms
`/nations` resolves; if Vercel prefers the directory, the fallback is documented in section 24, risk 1.

### 3.2 Sidecars, exact shapes

`regions.json` (display names are plain geography; no region is named after one people):

```json
{ "order": ["alaska-hawaii-pacific-us", "us-west-pacific", "us-plains-midwest", "us-east-southeast",
            "mx-north-us-southwest", "canada", "mx-central-south", "central-america-caribbean",
            "caribbean-guianas", "andes", "amazon-lowland-sa", "arctic-europe-russia", "africa", "asia", "oceania"],
  "regions": {
    "alaska-hawaii-pacific-us":  {"display": "Alaska, Hawaiʻi and the US Pacific", "merge_into": null},
    "us-west-pacific":           {"display": "US West and Pacific Northwest", "merge_into": null},
    "us-plains-midwest":         {"display": "US Plains and Midwest", "merge_into": null},
    "us-east-southeast":         {"display": "US East and Southeast", "merge_into": null},
    "mx-north-us-southwest":     {"display": "Northern Mexico and the US Southwest", "merge_into": null},
    "canada":                    {"display": "Canada", "merge_into": null},
    "mx-central-south":          {"display": "Central and Southern Mexico", "merge_into": null},
    "central-america-caribbean": {"display": "Central America", "merge_into": null},
    "caribbean-guianas":         {"display": "The Caribbean, Trinidad and the Guianas", "merge_into": null},
    "andes":                     {"display": "The Andes", "merge_into": null},
    "amazon-lowland-sa":         {"display": "Amazonia and lowland South America", "merge_into": null},
    "arctic-europe-russia":      {"display": "The Arctic, northern Europe and Russia", "merge_into": null},
    "africa":                    {"display": "Africa", "merge_into": null},
    "asia":                      {"display": "Asia", "merge_into": null},
    "oceania":                   {"display": "Oceania, Aotearoa and Australia", "merge_into": null} } }
```

The build fails on a region key in the data that has no entry, and on an entry no nation uses. The okina in
Hawaiʻi is the state's own spelling; section 11.2 gives the mono label a glyph for it. Herald order follows `order`;
list sections sort by display name.

`countries.json`: `{"AO": "Angola", "AR": "Argentina", "AS": "American Samoa", ... "ZW": "Zimbabwe"}` for exactly
the 99 codes in the data (ISO 3166-1 short English names; `TW` reads `Taiwan`, `PR` `Puerto Rico`, `GL`
`Greenland`, `GF` `French Guiana`, `NC` `New Caledonia`, `PF` `French Polynesia`, `CK` `Cook Islands`, `NU` `Niue`,
`TK` `Tokelau`). The build fails on a missing code and on an unused entry. The page says these are present-day
countries listed by ISO names; it never calls a country a nation's country.

`overrides.json`, applied last, every entry dated and with a requester class (`nation`, `reader`, `editor`):

```json
{ "hide_fact": [
    {"fact": "in-bhil-78bae6a7", "reason": "named-individual-review", "by": "editor", "date": "2026-10-10"},
    {"fact": "in-bhil-c69ec23b", "reason": "named-individual-review", "by": "editor", "date": "2026-10-10"} ],
  "hide_nation": [], "takedown": [], "rename": [], "drop_also": [] }
```

The two launch entries apply ARCHITECTURE 9.1. Bhil keeps its third fact (`in-bhil-af418789`), so it stays tier B
and its page reads `2 facts are under review.` Deleting the two entries publishes them; that is open decision 6.

`pronounce_publishers.json`: `{"tkemlups.ca": "Tk’emlúps te Secwépemc", "ktunaxa.org": "Ktunaxa Nation", ...}` for
the 11 hosts. When a pronunciation's host equals the nation's `official_url` host, the credit reads
`Pronunciation: <Name>, on its own site`. A host with no entry fails the build; a bare hostname never ships as a
credit.

`site.json`: `{"contact": "contact@zotheos.org", "repo_public": null, "check_mode": "pull-request",
"hidden_table_names_nations": false}`. The build reads `contact` into every `mailto:`; `repo_public` gates any link to
a pull request or issue (none while null); `hidden_table_names_nations` keeps the verification page's hidden list to
counts per publisher (section 9.4).

`changes.json`: `[{"date": "2026-10-10", "kind": "correction|name|removal|restoration|new|check", "nation": "<id> or
null", "text": "one plain sentence", "from": "nation|reader|editor|check"}]`. A removal at a nation's request has
`nation: null` and the fixed text `Removed at a nation's request.` No personal data, ever.

`verify/human.json`: `{"<fact id>": {"date": "2026-10-12", "by": "editor", "note": "read in a browser"}}`. A record
under 90 days old makes a fact publishable with the receipt `Checked by a person on 12 Oct 2026`.

`verify/history.json`: `[{"run_date": "2026-10-10", "sample": true, "urls_checked": 40, "urls_total": 742,
"facts_checked": 99, "verified": 98, "stale": 0, "unreachable": 1, "published": null}]`, newest first, 52 kept.

### 3.3 Reserved ids and the game boundary

`nations_lint.py` refuses a nation id in: `index`, `region`, `in`, `api`, `static`, `about`, `sources`, `coverage`,
`credits`, `verification`, `for-nations`, `changes`, `news`, `search`, `today`, `region`. Zero collisions today.

No nations page links to the game. The game's About screen may later link to `/nations` through its existing
`opts.nationsPage`; the game's hunter screens never link here. `static/nations/game.json` (the shape `natValid`
accepts) is specified in section 15.4 and **not emitted at launch**: the game is unlinked and its two caps
(524,288 bytes, 600 nations) are below the full dataset (about 599 KB raw). The build keeps a `--game-json` flag,
off by default, and the finding stays in the risk table.

---

## 4. The hub, section by section

Order on the page: header; the herald (first screen); the lede line; Today's ring; Find a nation; By region; By
country; Where we are; How this is made (with the verification panel); Corrections come first; footer. On the
owner's window (1600 x 993 at 1.25, so 1280 x 794 CSS px) the herald and its controls fit the first screen; nothing
of ours sits above a nation's name except the eyebrow and the header.

### 4.1 Header

The landing's header, reproduced from `partials/header.html`, with these differences, all by omission:

- The Appearance popover keeps Theme (Obsidian mono, Maya Blue cosmic, Codex parchment, Skeleton obsidian) and
  Motion (Living, Calm, Still). The Effect intensity row and Replay intro are omitted (no aurora, rain, grain,
  embers or intro here). The same keys are read and written (`zotheos_landing_theme`, `zotheos_motion`), so a choice
  carries across the site. `partials/appearance.js` (about 2 KB, inline, identical on every nations page) handles
  the radios, saves the keys and shows `Your system asks for reduced motion` when the OS floor applies; the popover
  itself is declarative (`popovertarget`), as on the landing.
- The day chip and its popover are omitted. The hub makes no request the visitor did not ask for and adds no
  calendar; the landing keeps the chip.
- The wordmark links to `/`.
- Nav: `Today`, `Find`, `Regions`, `Coverage`, `About`, `For nations`. Under 1024 px the links fold into the Menu
  sheet, which also carries Sources, Credits, Verification, Changes and, at its foot, the Appearance control, exactly
  as the landing's sheet carries `.header-left`.
- `nations_lint.py` compares the partial's Appearance popover markup (Theme and Motion rows) against `index.html`
  and fails on drift, so the two never diverge silently.

### 4.2 The herald

Markup of the one card. The app re-renders it per nation with `textContent`; it never uses `innerHTML`.

```html
<section class="herald" id="today" aria-labelledby="heraldLabel">
  <h1 class="hr-eyebrow" id="heraldLabel">
    <svg class="fret" viewBox="0 0 10 10" aria-hidden="true" focusable="false"><use href="#fret-mini"/></svg>
    Indigenous nations today
  </h1>
  <div class="hr-stage" id="heraldStage" data-state="in">
    <article class="hr-card" id="heraldCard">
      <p class="hr-region">Canada</p>
      <h2 class="hr-name" dir="auto" data-size="xl" data-face="brand" data-script="latn">Secwépemc</h2>
      <span class="hr-line" aria-hidden="true"></span>
      <p class="hr-also"><span class="hr-k">Also known as</span> Shuswap</p>
      <p class="hr-say"><span class="hr-k">Say it</span> suh-Wep-muhc
        <a href="https://tkemlups.ca/language-culture/" rel="noopener noreferrer" target="_blank">Pronunciation: Tk’emlúps te Secwépemc<span class="sr-only"> (opens in a new tab)</span></a></p>
      <p class="hr-lands"><span class="hr-k">Lands</span> Secwepemcúl’ecw, a large territory in the interior of British Columbia, Canada ...</p>
      <p class="hr-fact">The Shuswap Nation Tribal Council brings together nine Secwépemc communities in the Southern Interior of British Columbia.</p>
      <p class="hr-receipt">
        <a href="https://shuswapnation.org/about/bands/" rel="noopener noreferrer" target="_blank">Source: Shuswap Nation Tribal Council<span class="sr-only"> (opens in a new tab)</span></a>
        <span class="hr-dot" aria-hidden="true">&middot;</span> As of 2026
        <span class="hr-dot" aria-hidden="true">&middot;</span> Checked <time datetime="2026-10-08">8 Oct 2026</time>
      </p>
      <p class="hr-more">
        <a href="/nations/secwepemc-bc-ca">Open this nation</a>
        <a href="https://shuswapnation.org/" rel="noopener noreferrer" target="_blank">Nation's own site<span class="sr-only"> (opens in a new tab)</span></a>
      </p>
    </article>
  </div>
  <div class="hr-controls" role="group" aria-label="Herald controls">
    <button type="button" class="hr-btn" id="hrPrev">Previous</button>
    <button type="button" class="hr-btn" id="hrPause" aria-pressed="false">Pause</button>
    <button type="button" class="hr-btn" id="hrNext">Next</button>
    <span class="hr-ring" id="hrRing" aria-hidden="true"></span>
    <p class="hr-status" id="hrStatus">1 of 15 in today's ring <span aria-hidden="true">&middot;</span> 450 nations <span aria-hidden="true">&middot;</span> Last check 8 Oct 2026</p>
  </div>
  <p class="hr-lede">One nation at a time, named as it names itself, with one checked fact and its source.</p>
  <div class="sr-only" aria-live="polite" id="heraldLive"></div>
</section>
```

Rules the markup carries:

- The card has no border, no box and no fret. Its only ornament is `.hr-line`, one hairline under the name. The
  fret opens our eyebrow and our footer label; it never frames a nation and never touches a name (the fret is
  Mesoamerican and Southwestern; it is not imposed on Arctic, Pacific or African nations).
- `h1` is the eyebrow, 11 px mono. The nation's name is `h2`, the largest text on the page. Nothing of ours is ever
  larger than the name.
- The name is **upright** (`font-style: normal`), `font-synthesis: none`, `text-transform: none`, `letter-spacing:
  normal`, `hyphens: manual`, `overflow-wrap: normal`, `text-wrap: balance`, `dir="auto"`. `lang` is set only when a
  sourced language tag exists in a sidecar (`data/nations/lang.json`, later); today none does, which is honest: the
  page language is English and the name is quoted.
- `Also known as` shows at most two `also` entries; `also_search` entries never render. `Say it` renders only when
  `pronounce` exists and its text passed its last check; the credit is the publisher from
  `pronounce_publishers.json`, never a hostname.
- The receipt is part of the card at every width; nothing collapses it on phones. `Checked by a person on <date>`
  replaces `Checked <date>` when a human-lane record applies.
- The static first card is rendered at build (the build-date ring's first nation), so a visitor with JavaScript off,
  or on a slow connection, sees a complete named card at first paint. With JavaScript off, `html.no-js` hides the
  controls and the status line reads `This page shows one nation. Every nation has its own page under By region.`
- The live region is present and empty at load. It is filled only on a user event (Previous, Next, the first card
  after load when focus is inside the herald). Auto-advances update the visible card and announce nothing.

### 4.3 Controls and the ring marks

- `Previous`, `Pause` (label `Resume` while pressed, `aria-pressed="true"`), `Next`: the landing's `.ap-opt`
  grammar (mono 11 px uppercase, 0.16 em tracking, 1 px rim at 0.55 alpha, 44 px tall, pill radius, chosen state in
  ink). Text labels, never icons alone. They are visible and in ink from the first frame; they are not part of the
  fade-in. `Next` carries the default ink rim so the way forward reads as a control at first paint.
- The ring marks: fifteen 4 px codex dots in a `<span aria-hidden="true">`, the current one filled, the others 1 px
  rings. They mark position only. They are not buttons, they do not fill as nations are named, nothing persists
  beyond the day, and the status line carries the meaning in text (`4 of 15 in today's ring`). Grouped in threes of
  five with a 6 px gap, as `.maya-num` groups fives.
- Keyboard: `Left` and `Right` act as Previous and Next while focus is inside `.hr-controls`; `Space` and `Enter`
  on the buttons as usual. The herald never captures keys when focus is elsewhere.
- Focus stays on the button after a press; the live region speaks (`Nation: <name>. Lands: <lands>. <fact>`). The
  card's links come after the controls in tab order, so a keyboard user reaches them without the card advancing
  (focus inside pauses).
- In Still (and under the OS reduced-motion floor) the Pause button is hidden and the status line reads
  `Press Next for the next nation.`

### 4.4 Today's ring

Heading (h2, serif italic): `Today's ring`. Lede: `Fifteen nations, one from each region, the same for everyone
today. Tomorrow the ring turns.` A list of fifteen rows in ring order: the name (serif upright, 24 px, white,
`dir="auto"`), the region display name (mono, grey), the first eight words of the lands in grey. Each row links to
`/nations/<id>`. With JavaScript off the build-date ring renders statically with the note `Ring for 8 Oct 2026`, so
it never claims to be today's.

### 4.5 Find a nation

A `div[role="search"]` with a visible label `Find a nation`, an `input[type="search"]` (`autocomplete="off"`,
`spellcheck="false"`, `enterkeyhint="search"`, 44 px tall, 1 px rim at 0.55 alpha), placeholder
`Name, other name, place or country`, helper `Accents are optional: Maori finds Māori, Dine finds Diné. Names always
show as the nation writes them.` No `<form>`: there is nothing to submit to and the CSP has `form-action 'none'`.

`search.json` loads on first focus (one request). Matching is section 7.1. Results render as a list of links under
the field, up to 24, `Show all` for the rest. A row: name (serif upright 22 px), then one line `Also known as <entry>`
when the match came through `also` (never through `also_search`), then `<Region display> · <lands, 90 characters>`
in mono grey. The status line (`aria-live="polite"`, debounced 300 ms) says `12 nations match`, `1 nation matches`,
or `No nation matches yet. Try another spelling, a place, or browse by region.` Keyboard: `ArrowDown` from the field
moves focus to the first result; `ArrowUp` from the first result returns; `Escape` clears. With JavaScript off the
block carries `hidden`, which the app removes, and a line reads `Search needs JavaScript. The region lists below hold
every nation.`

### 4.6 By region and By country

`By region`: fifteen real links in two columns (one on phones), each a row of the display name (DM Sans 17 px), the
count in mono (`41 nations`), and the countries of the region in grey. Sorted by display name. Lede: `Regions are
plain geography for finding your way. No region is named after one people. Cross-border nations appear under every
country they name.` No map at launch; the list is the control.

`By country`: 99 links in four columns at 1280 (two on phones), `Canada 40` style, alphabetical by display name.
Note under the heading: `Present-day countries, listed by ISO 3166 names. Many nations live across more than one.`

### 4.7 Where we are

Heading `Where we are`. One paragraph from `coverage.json`: `450 nations, 1,260 checked facts, 15 regions, 99
countries. The United Nations estimates 476 million Indigenous people in 90 countries and about 5,000 distinct
cultures, so this list is a beginning. Thin regions are listed first on the coverage page.` The UN sentence links to
the UN background page named in ARCHITECTURE 12. Link: `See the coverage table`.

### 4.8 How this is made, with the verification panel

Four lines, DM Sans:

- `Every fact is written from a published page and carries that page's publisher, a link, and the date a tool or a
  person last found the supporting words on it.`
- `A tool re-reads every cited page weekly. Changes from a check go live after review. A fact whose words are gone
  is hidden until a person restores it.`
- `Drafts were compiled with AI assistance, then checked against sources by a tool and by people.`
- `This page makes no request to any other site. Sources open only when you choose to follow them.`

Then the panel, four values in a single row (2 x 2 on phones), labels in mono 11 px, values in Instrument Serif
upright 28 px, no box, no rim, one hairline above (the panel is about us, so it sits below the names and is drawn
quietly):

```
LAST CHECK          SOURCES REACHED       FACTS VERIFIED        HIDDEN OR WAITING
8 Oct 2026          none yet              1,260                 0 hidden, 0 waiting for a person
compiled            a sample run of 40 of 742 pages was made on 10 Oct 2026
```

Its states and sentences are in section 9.3. Link: `What was checked, and what a check cannot tell you` to
`/nations/verification`.

### 4.9 Corrections come first

Heading `Corrections come first`. Text: `If you belong to a nation listed here, or speak for one, your word outranks
every source on this page. Ask and we hide first and ask second, within 72 hours. Readers who find an error are
welcome to write too.` Action: `Write to contact@zotheos.org` as a `mailto:` with subject `Nations correction` and
the body template of section 10.2. Link: `How a nation corrects, adds or removes anything here` to
`/nations/for-nations`. Nothing is invented: no form, no new address until the owner creates one; the landing's
Formspree form stays on the landing and out of every nations CSP.

### 4.10 Footer

The landing footer's structure: brand, the three link columns (Council, Proof, Release, unchanged copy with
`Indigenous nations today` added to Release), the privacy details, then `Roots and gratitude` verbatim from the
landing with the one added sentence of section 20, then the nations credit block (section 10.1), then the epigraph.

---

## 5. The herald choreography

### 5.1 Living (default)

| t (ms) | element | change | duration | ease |
|---|---|---|---|---|
| 0 | stage | black; controls already visible | | |
| 0 | `.hr-region` | opacity 0 to 1 | 300 | `--ease-out` |
| 200 | `.hr-name` | opacity 0 to 1 | 900 | `--ease-out` |
| 1100 | `.hr-line` | `inline-size` 0 to 100% of the name box | 500 | `--ease-ceremony` |
| 1250 | `.hr-also` | opacity 0 to 1 | 400 | `--ease-out` |
| 1450 | `.hr-say` (if sourced) | opacity 0 to 1 | 400 | `--ease-out` |
| 1650 | `.hr-lands` | opacity 0 to 1 | 400 | `--ease-out` |
| 1950 | `.hr-fact` | opacity 0 to 1 | 500 | `--ease-out` |
| 2350 | `.hr-receipt`, `.hr-more` | opacity 0 to 1 | 400 | `--ease-out` |
| 2750 | build complete | | | |
| 2750 + dwell | whole card | opacity 1 to 0 | 450 | `--ease-ceremony` |
| + 400 | black | | | |

When a card has no `also` or no `say`, the later beats move up by that beat's offset, so the fact never waits on an
empty line. Dwell = `clamp(4500 + 55 * factChars, 7000, 14000)` ms from build complete: a 60-character fact dwells
7.8 s, the longest fact (198) 14 s. One nation occupies 11 to 18 s.

Only opacity and the line's `inline-size` animate. No transform, no filter, no letter-spacing, no colour. The line is
an element of fixed `block-size: 1px` whose `inline-size` grows, never `scaleX`, so it stays crisp at the owner's
1.25 scale. Brightness on screen changes at most twice a second.

### 5.2 Calm

Background effects rest; the page still moves (the landing's own definition). The herald is content, so it still
advances. Two beats: region and name as in Living (0 and 200 ms), the line drawn with the name; then every remaining
line together at 1100 ms over 400 ms. Out 300 ms, black 300 ms. Dwell unchanged.

### 5.3 Still, and the OS reduced-motion floor

No transitions, no auto-advance. Every change is an instant swap, including the line. Next and Previous move the
card. Pause is hidden. The status line reads `Press Next for the next nation.` The bootstrap sets
`html[data-motion="still"]` before first paint when the OS asks for reduced motion (the landing's rule), and the
landing's Still rule (`animation: none !important; transition: none !important` on every element) is in the nations
stylesheet, so the first card never moves.

### 5.4 Pause conditions

The herald pauses while any holds: the pointer is over `.herald`; focus is inside `.herald`; `document.hidden`;
the stage is less than 60 percent visible (IntersectionObserver); Pause is pressed. Pausing stops the dwell clock
and leaves the card fully visible. Resuming continues from the remaining dwell, never mid-fade, and never restarts
the cycle. This satisfies WCAG 2.2.2: the herald starts automatically, lasts more than five seconds and sits beside
other content, so it has visible Pause and Next, pauses on hover and focus, and pauses when hidden.

### 5.5 The first card: one clock

The static card ships with `data-state="in"`, and `html[data-motion="living"] .hr-stage[data-state="in"] .hr-*`
carry CSS animations with the delays above, so the first ceremony plays before the app runs. The app owns one clock:
on load it reads `animationend` of `.hr-receipt` (or, if that already fired, the stage's `data-built="1"` set by
CSS via `animation-fill-mode` and checked with `getAnimations()`), then starts the dwell timer. The app never
interrupts a ceremony in progress. If the static first nation is today's first unseen ring nation on this device
(the common case), the walk continues from it without a repeat; otherwise the ring begins after the first card fades.
There is no second JavaScript clock racing the CSS one.

### 5.6 Fonts and the reveal

Before a card's name begins its fade, the app awaits `document.fonts.load()` for the exact face and the exact name
string (and for `ZN Sans` with the fact text when `fc` says so), capped at 600 ms. The `ZN *` faces use
`font-display: block`; the brand faces keep `swap` as on the landing. A name is never shown half in a system face and
then swapped. Under Still the same wait applies before the instant swap.

---

## 6. Renewal: the Daily Ring and the Personal Walk

### 6.1 Shared ring

`seed = fnv1a32(localDateISO + "|" + dataVersion)`. For each herald region in `regions.json` order, pick
`i = permute(seed, regionIndex) mod count` among tier A and B nations. Fifteen nations today; every region has at
least 16 publishable nations, so `merge_into` stays unused until round 3. The ring is the same for everyone with the
same local date and data version, and the ring list (4.4) shows it in order. Fact choice on a ring card prefers
kinds `today` and `achievement`; otherwise `facts[(dayNumber + fnv1a32(id)) mod facts.length]`, so the fact on a
card renews daily (the owner's "a fact that always renews").

### 6.2 Personal walk

```
key   32-bit from crypto.getRandomValues, stored as zth_nations_key
c     cursor, zth_nations_cursor
seen  per-day bitmask of ring nations named on this device, zth_nations_ring_<date> (yesterday's key deleted)

R  = herald regions in an order seeded by key
r  = R[c mod |R|]
k  = floor(c / |R|)
n  = r.count
i  = feistel4(k mod n, n, key ^ fnv1a32(r.key) ^ dataMajor)   // 4 rounds, cycle-walk until i < n
card = shard(r)[i]
f  = (floor(k / n) + fnv1a32(card.id)) mod card.facts.length     // the next cycle shows the next fact
c  = c + 1 after the card has fully shown
```

Order of play: ring nations not yet named on this device today, in ring order; then the walk. `Previous` walks a
session history array of cards actually shown, not `c - 1`. Every storage read and write is wrapped in `try/catch`;
if storage fails, the key lives for the session and the cursor starts at a random point, so the ceremony still
varies. Nothing leaves the device.

### 6.3 What renews, and when

Daily: the ring turns at the visitor's local midnight. Weekly: the verifier changes `last_verified` dates and hides
stale facts; the data version changes; shard names change (content hash), so caches are never stale. Per visit: the
walk continues from the cursor, so a returning device meets new nations until a region is exhausted (Asia, the
largest, takes 53 cards).

---

## 7. Search and browse

### 7.1 The fold table (one source, two languages)

`tools/nations_fold.py` defines the table; the build emits the same table into `herald.js` as a literal, and
`nations_lint.py` runs 1,200 strings (every name, `also`, `also_search`, lands and region name) through both and
fails on any difference.

```
fold(s) = NFKD(s) -> drop Mn (combining marks) -> casefold
          -> drop  ' ʻ ʼ ’ ` ˊ · ‧ ʔ ǀ ǁ ǂ 7   (apostrophe-like marks, dots, glottal and click letters; the digit 7 only when it stands between letters)
          -> map   ł->l ø->o æ->ae œ->oe ß->ss ŋ->ng ɨ->i ə->e ʉ->u ɬ->l ɫ->l ɓ->b ɗ->d θ->th ⁿ->n
          -> collapse whitespace, split into tokens
```

Matching is token-prefix on folded tokens, ranked name, then `also` and `also_search`, then lands, then country and
region display names. No fuzzy matching: a wrong near-match on a people's name is worse than no match. Cyrillic,
syllabics and Cherokee tokens are kept as they are and found by paste or through the Latin `also`. Displayed strings
are never folded. `also_search` entries (imposed or official exonyms kept for retrieval) are searched and never
displayed anywhere.

### 7.2 Region, country and A to Z

`/nations/region/<key>`: every nation in the region, alphabetical by self-published name (folded for sort only),
each as a card (name, `Also known as` first entry, lands, one fact with its receipt, `Open this nation`), cards
separated by a hairline, never boxed. `/nations/in/<iso2>`: the same for every nation listing that country. The hub
carries no A to Z list (the region pages are the no-JavaScript way in and keep the hub under its size budget).

---

## 8. The nation page, region page and country page

### 8.1 Nation page (`/nations/<id>`), fully rendered at build

1. Region display name (mono eyebrow). Name as `h1` (serif upright, `clamp(48px, 7vw, 112px)` at `xl` down to
   `clamp(24px, 2.6vw, 40px)` at `xs`, `dir="auto"`, `text-wrap: balance`, never hyphenated). `Also known as` list.
   `Say it: <text>` with `Pronunciation: <publisher>` only when sourced and verified.
2. `Visit the nation's own site` as the first link when `official_url` exists (190 nations). For the others the
   line is absent; nothing says "no site".
3. `Lands` paragraph. `Countries` as links to `/nations/in/<iso2>` by display name; a code never shows.
4. `Facts`: every publishable fact, newest `as_of` first, undated after dated, stable by fact id. Each is an
   `article`: kind label (mono, uppercase, plain text, no box), the text (DM Sans 17 px, white), then one mono
   receipt: `As of 2024 · Source: <publisher>, <title> · Checked 8 Oct 2026` (publisher and title together form
   the link; `As of` omitted when null; `Checked by a person on <date>` for the human lane; `Our tool could not reach
   the page on <date>` appended for a fact in grace).
5. Count lines when facts are not shown: `1 fact is being re-checked.` or `<n> facts are being re-checked.` for
   stale and expired facts; `<n> facts are under review.` for editor holds such as the Bhil entries. Never their
   content, source or reason.
6. Tier C: `Facts in progress. This entry lists the nation by its own name while facts are compiled and checked.`
7. `Suggest a correction` (`mailto:`, subject `Nations correction: <id>`), then `For nations: how to correct, add or
   remove anything here`.
8. Credit line: `Names, lands and facts are written from the sources shown. Corrections from nations come first.`

`<title>`: `<Name> | Indigenous nations today`. Description: `<Name>: <lands>. <first fact>` cut at 155 characters
on a word. `<link rel="canonical" href="https://zotheos.org/nations/<id>">`. Codex dots beside the Facts heading
count the shown facts (1 to 5), `aria-hidden`, with the numeral in text.

### 8.2 Pronunciation credit

`Pronunciation: <publisher>` from `pronounce_publishers.json`; `Pronunciation: <Name>, on its own site` when the
host is the nation's `official_url` host. A missing entry fails the build. A pronunciation whose text failed its last
check is not shown, and the page says nothing about it.

### 8.3 Region and country pages

`<title>`: `<Region display> | Indigenous nations today` and `<Country> | Indigenous nations today`. Eyebrow, `h1`
(serif italic, our words), lede `<count> nations of <display>, each with its own name first and checked facts with
sources.` (country: `<count> nations list <Country> among their present-day countries.`), then the cards (7.2).
A hairline opens the list once with the fret; no fret near a card.

### 8.4 Removed and renamed nations

A nation removed at its own request leaves every page, shard, the search index, the ring, the sitemap and the credits;
its id goes to the lint block list; `/nations/<old id>` is a plain 404 (no tombstone page: the id itself names the
nation). The change log shows only `Removed at a nation's request.` A renamed id goes to `redirects.json`, and the
build writes a `redirects` entry in `vercel.json` (308) from the old path to the new, nowhere visible.

---

## 9. Verification you can see

### 9.1 Display states, derived at build from the tool's three states

| Tool state and facts | Display state | Shown? | Receipt |
|---|---|---|---|
| `verified` | ok | yes | `Checked <last_verified>` |
| `unreachable`, `last_verified` within 14 days | grace | yes | `Checked <last_verified>` plus `Our tool could not reach the page on <checked>` |
| `unreachable`, `human.json` record under 90 days | human | yes | `Checked by a person on <human date>` |
| `unreachable`, grace expired, no human record | waiting | no | counted in `<n> facts are being re-checked.` |
| `stale` | hidden | no | counted in `<n> facts are being re-checked.` |
| `overrides.json` hide_fact | review | no | counted in `<n> facts are under review.` |

Name rule (ARCHITECTURE 3.3): a failed name check never hides a nation. The last verified name stays, the entry is
listed on the verification page under `Waiting for a person`, and an editor decides. A nation's own request always
overrides.

### 9.2 `last_verified`: one additive field

`nations_refresh.py` gains one line: on a `verified` outcome it writes `f["last_verified"] = args.run_date`; on any
other outcome it leaves `last_verified` untouched (while still writing `status` and `checked` as today).
`validate.py` adds `last_verified` to `FACT_KEYS` as optional and requires it to be a date not after `checked`.
Migration, once, by `tools/nations_build.py --seed-last-verified` before the first full run: every fact whose
`status` is `verified` and has no `last_verified` gets `last_verified = checked` (2026-10-08 today). Without this
field the grace window cannot be computed, because `checked` is overwritten on a failed attempt. With it, the hosts
that refuse the tool (minorityrights.org with 37 facts, whc.unesco.org with 21, some iwgia.org pages; roughly 5 to 7
percent of facts) stay visible for 14 days after the first full run, with the honest "could not reach" line, while a
person checks them into `human.json`.

### 9.3 `static/nations/status.json` and the panel states

```json
{ "built": "2026-10-10", "data_version": 1, "nations": 450, "facts_shown": 1258, "facts_review": 2,
  "facts_rechecking": 0, "last_full_check": null,
  "last_run": {"date": "2026-10-10", "sample": true, "urls_checked": 40, "urls_total": 742,
               "facts_checked": 99, "verified": 98, "stale": 0, "unreachable": 1},
  "compiled": "2026-10-08", "check_mode": "pull-request", "news_gathered": null }
```

| State | Condition | Panel sentence |
|---|---|---|
| `no-check` | `last_full_check` null | `No full check has been published yet. Every fact shows the date its supporting words were found when it was compiled.` |
| `partial` | last run `sample: true` | adds `A sample run of <n> of <m> pages was made on <date>.` |
| `ok` | last full check 14 days or newer | `Last check <date>. <n> of <m> source pages reached. Changes from a check go live after review.` |
| `overdue` | last full check older than 14 days | adds `Verification is overdue. The last published check ran on <date>. Facts stay shown with their last checked date.` |

The browser computes `overdue` from `status.json` at load; with JavaScript off the build writes the sentence when the
build date itself is already past 14 days. The status line under the herald shows `Last check <last_full_check>` or,
in `no-check`, `Compiled 8 Oct 2026`. The word "live" never appears on these pages.

### 9.4 The verification page (`/nations/verification`)

`<title>`: `Verification | Indigenous nations today`. Eyebrow `VERIFICATION`; lede `Every fact here was checked
against its source page by a tool, on the date shown. This page is the record of those checks.` Sections, each opened
by the fret and a mono label:

1. `THIS CHECK`: run date, mode, pages reached of total, facts checked of total, verified, hidden, waiting, duration,
   and one sentence written by the build from the numbers. For the sample run: `A sample run on 10 Oct 2026 reached
   40 of 742 source pages and found the cited words on 98 of the 99 facts it could test. One page refused the tool
   and waits for a person. No full check has been published yet.`
2. `WHAT IS HIDDEN AND WHY`: by default counts per publisher and reason (`site.json.hidden_table_names_nations`
   false): `minorityrights.org: 37 facts waiting for a person (HTTP 403)`. Reasons are fixed strings: `The cited
   words are no longer on the page`, `The page is gone (404 or 410)`, `The page now redirects to another site`,
   `The page could not be reached (HTTP <code>)`, `robots.txt disallows the page`. Nation names appear here only
   when the owner flips the flag; fact text never. Empty state: `Nothing is hidden. Every published fact passed its
   last check.`
3. `WAITING FOR A PERSON`: hosts, fact counts, what the tool saw, and `Checked by a person on <date>, expires <date>`
   where a record exists.
4. `PAST CHECKS`: the last 12 runs from `history.json` (date, pages reached of total, verified, hidden, waiting,
   published date, `sample run, nothing written` for dry runs). A link to the pull request appears only when
   `site.json.repo_public` is true.
5. `HOW A CHECK WORKS`: plain sentences: the user agent string, robots.txt obeyed, one request per host every three
   seconds, no browser spoofing, text extraction, the normalization steps (quotes, dashes, soft hyphens, whitespace,
   case; PDF hyphenation joined), exact match then diacritics-insensitive match, and the rule that nothing hidden is
   ever restored by the tool alone.
6. `WHAT A CHECK CANNOT TELL YOU`: `A pass means the cited words are still on the cited page. It does not mean the
   page is right, complete or current, and it does not mean we read the words the way the nation would. Corrections
   from nations come first.`
7. `WHAT THE DATES MEAN BEFORE THE FIRST FULL CHECK`: `Checked 8 Oct 2026 on a fact means the date its supporting
   words were found on the cited page while the fact was compiled. After the first full check, it means the date the
   weekly tool last found them.`

Tables carry `<caption>` and header `scope`; under 640 px rows stack with the header text repeated per cell
(`data-label` and `::before`).

---

## 10. Credits, corrections, For nations, Changes, About, Coverage

### 10.1 Credits (`/nations/credits`) and the credit block on every page

Roll call: every published nation by self-published name, alphabetical within region, each a link; 450 names in one
type size, no tiers shown. Publishers: nations' own sites first, then the priority groups of ARCHITECTURE 2.4, each
linking to its anchor on the sources page. People: `Compiled and edited by ZOTHEOS. Founder: David Garcia.` (the
landing already publishes the founder's name); other people only when they ask to be named (open decision 7). Then:

- `Compiled with AI assistance from published sources, checked against those sources by a tool every week and by
  people. Corrections and removal requests from any nation are honored.`
- `Global figures: United Nations, World Bank.`
- `Fonts: Instrument Serif, DM Sans and JetBrains Mono, with Noto Serif, Noto Sans, Noto Sans Mono, Noto Sans
  Cherokee, Noto Sans Canadian Aboriginal, Noto Sans Devanagari and Noto Sans Tifinagh for letters the brand faces
  lack. All self-hosted under the SIL Open Font License. No letter in a name is ever changed to fit a font.`
- `Verifier: ZOTHEOS-nations-verifier, Python, run weekly through GitHub Actions.`

The footer credit block on every nations page: `Nations: names, lands and facts as each nation publishes them, and
from the public sources named on every card. Full list at zotheos.org/nations/sources.` plus the AI line, the fonts
line, `This site makes no request to any other site. Sources open only when you follow them.` and `Last check
<date>` (or `Compiled <date>` in `no-check`). `Map: Natural Earth (public domain)` joins only when a map ships.

### 10.2 Corrections path

The only address the site publishes is `contact@zotheos.org` (index.html line 8539); the Formspree form is the
landing's waitlist and is never used here. One constant in `site.json` changes every link when the owner creates a
role address. Decoded body of the fact-level link (`Suggest a correction`):

```
mailto:contact@zotheos.org
?subject=Nations correction: <nation id> <fact id>
&body=Nation: <name> (<id>)
Fact: <fact id>
What is wrong:

A source that shows the correction (address of the page), optional:

If you write for the nation, say so and we act within 72 hours.
```

No field asks for a name: the change log carries no personal data (ARCHITECTURE 7.1). The hub-level link has subject
`Nations correction` and the body without the fact lines. The For nations link has subject `For nations: <name>`.

### 10.3 For nations (`/nations/for-nations`)

`h1`: `Your word comes first.` Lede: `Your word outranks any registry here. If you speak for a nation listed on this
site, you can correct any line, remove the pronunciation or any other name, add a fact from your own site, send an
official pronunciation in writing, or remove the whole entry. No reason is required. We hide within 72 hours and aim
for 24. Write to contact@zotheos.org with the subject "For nations".` Then: `Pronunciation: we show written
pronunciation only when it comes from a source we can cite, and we never generate speech. A recording of your own,
with your written permission, can be added later and removed on request.` Then: `We are not yet advised by an
Indigenous advisory circle. Until that circle exists, the rules on this site apply, and this page says so.` Then a
takedown model line: `A takedown needs no form. One message is enough; if authority is unclear we hide while we
confirm.`

### 10.4 Changes, About, Sources, Coverage

`/nations/changes`: entries from `changes.json`, newest first; the build appends one entry per merged weekly check
(`Weekly check: <n> facts hidden, <n> restored by review.`). Empty state: `No corrections or removals yet.`

`/nations/about`: `h1` `How this list is made.` The method; the user agent; source rules in plain words (nations'
own pages first, no Wikipedia as a citation); the rotation (`The ring is seeded by the date, the same for everyone.
The walk is seeded by a key kept only in your browser.`); the AI assistance disclosure; the no-third-party line
(`Open your browser's network panel on any page here: every request goes to zotheos.org.`); the typeface note (`Some
names appear in a second typeface because the brand face lacks their letters. The letters are never changed.`); the
honest scale paragraph with the UN and World Bank figures, their sources and dates; the advisory circle line; and
`#type`, a type sample of every script in use (one name per face, one `also` in Cyrillic, syllabics and Cherokee, a
Devanagari title) for hardware eyeballing after each build. The game is not mentioned.

`/nations/sources`: every publisher grouped by priority (ARCHITECTURE 2.4), each with fact count, page count, last
checked date and state words (`all pages reached`, `2 pages waiting for a person`); under each, every URL as a link
with fact count and checked date. 742 URLs; the page is long and that is correct. Unmapped domains last under `Not yet
classified`. Long URLs wrap with `overflow-wrap: anywhere`.

`/nations/coverage`: per region and country: listed, tier A, B, C, with pronunciation, facts re-checking, last full
check, and the denominator with its source where `universe.json` has one (US 575 federally recognized entities,
Federal Register 30 Jan 2026; Canada, CIRNAC); otherwise `denominator not yet confirmed from a primary source`. Thin
regions first. The paragraph `A denominator is a planning number, not a definition of who counts.` is required.

---

## 11. Typography for every script

### 11.1 Faces and roles

| Role | Stack | Style |
|---|---|---|
| Names (herald `h2`, nation `h1`, list names, search results) | `'Instrument Serif', 'ZN Serif', 'ZN Cherokee', 'ZN Syllabics', 'ZN Tifinagh', serif` | **upright**, weight 400, `font-synthesis: none` |
| Our display sentences (section `h2`, page `h1` on our pages) | `'Instrument Serif'` | italic, as on the landing |
| Reading (also, say, lands, facts, ledes, receipts' publisher and title) | `'DM Sans', 'ZN Sans', 'ZN Devanagari', 'ZN Cherokee', 'ZN Syllabics', 'ZN Tifinagh', system-ui, sans-serif` | per-glyph fallback is fine in running text; whole-line rule below |
| Labels and receipts' dates and keys | `'JetBrains Mono', 'ZN Mono', ui-monospace, monospace` | our words; ASCII plus the code points in `regions.json` display names |

Names are upright because an Indigenous name or term is never italicized (BC Indigenous content guide), because a
name is a quotation rather than our phrase, and because stacked combining marks sit correctly upright. Italic stays
the voice of our own headings. Nothing uppercases a name; click letters and case-bearing orthographies would lose
meaning. The digit 7 in `Sḵwx̱wú7mesh` is a letter of that orthography and stays a 7. U+2019 stays U+2019; U+02BB
stays U+02BB. The build never swaps a character to suit a font: the gate fails instead.

### 11.2 The whole-name rule, and the whole-line rule

The build decides per string and ships the decision in the shard (`fc`, `sc`, `sz`), so the browser does no coverage
logic:

- If every code point of the name is in the upright Instrument Serif cmap and the name contains no combining mark
  (category Mn): `data-face="brand"`.
- Otherwise `data-face="names"` and the whole name renders in `ZN Serif` (upright Noto Serif), with `size-adjust` in
  its `@font-face` from the measured `sxHeight` ratio (Instrument Serif 0.510 over Noto Serif's measured value) so
  x-heights match in lists where both faces meet. Ten names today.
- If the name contains any Cherokee, Syllabics or Tifinagh code point: `data-script` is `cher`, `cans` or `tfng`,
  the whole name renders in that script's face, `line-height` rises to 1.14. A synthetic slant on a syllabary is
  never acceptable; `font-synthesis: none` on every name element.
- `also`, `say`, `lands` and fact lines get the same test against DM Sans: when any glyph of a line needs the
  fallback, the whole line uses `ZN Sans` (`data-face="names"` on the `p`), so a Salish word never changes face
  mid-word. Devanagari and Cyrillic in source titles fall through `unicode-range` glyph by glyph, which is correct for
  a Latin title containing a Devanagari name.
- The glyph gate (11.4) checks each grapheme cluster, not each code point: every code point of a cluster (base plus
  marks) must come from one face in the element's stack.
- Mono labels: `ZN Mono` is a Noto Sans Mono subset of exactly the label code points JetBrains Mono lacks (today
  U+02BB for Hawaiʻi; under 2 KB), so our labels stay monospaced and the state's spelling stays.

### 11.3 Files, subsetting, licensing

Vendored under `tools/fonts-src/` (never deployed; about 9 MB in git once), each with its `OFL.txt`:

| Family | Release and file | Serves |
|---|---|---|
| Noto Serif | NotoSerif-v2.015, `full`-less: `unhinted/variable-ttf/NotoSerif[wdth,wght].ttf` | ZN Serif: Latin Extended, IPA, Spacing Modifier, Combining marks, Greek, Cyrillic, Latin Extended Additional and D |
| Noto Sans | NotoSans-v2.015, `full/variable-ttf/NotoSans[wdth,wght].ttf` | ZN Sans: the same blocks for reading text |
| Noto Sans Mono | current release, `full/variable-ttf/NotoSansMono[wdth,wght].ttf` | ZN Mono: label fallback glyphs |
| Noto Sans Canadian Aboriginal | v2.004, `full/variable-ttf/NotoSansCanadianAboriginal[wght].ttf` | ZN Syllabics: U+1400 to 167F, U+18B0 to 18FF (UCAS Extended-A U+11AB0 to 11ABF is not in this file; the gate tests the file) |
| Noto Sans Cherokee | v2.001, `full/variable-ttf/NotoSansCherokee[wght].ttf` | ZN Cherokee: U+13A0 to 13F4 (lowercase U+13F8 to 13FD and U+AB70 to ABBF are not in this file; the gate tests the file) |
| Noto Sans Devanagari | current release, `full/variable-ttf/NotoSansDevanagari[wdth,wght].ttf` | ZN Devanagari: source titles |
| Noto Sans Tifinagh | v2.006, `full/ttf/NotoSansTifinagh-Regular.ttf` (base face only; a regional variant is added when a nation publishes in it) | ZN Tifinagh: reserved for round 3 Amazigh endonyms; shipped now, about 2 KB |

`tools/nations_fonts.py` (fontTools, `pyftsubset --layout-features='*' --flavor=woff2 --unicodes=... --name-IDs='*'`):

1. Collect every code point in published strings by role (names: name, also, pronounce text; reading: lands, facts,
   titles, publishers, our copy on nations pages; labels: ours plus `regions.json` display names).
2. Read the brand faces' cmaps from `static/fonts/*.woff2` (needs `brotli`).
3. Names fallback set: every code point used in names, plus Basic Latin, Latin-1, Latin Extended-A and B, IPA
   Extensions, Spacing Modifier Letters, Combining Diacritical Marks, Latin Extended Additional, Greek and Coptic,
   Cyrillic, General Punctuation U+2018 to U+201F, so a whole-name fallback always has every letter it needs.
   Reading fallback set: the same plus the reading code points. Script faces: their whole blocks.
4. Keep layout features so mark positioning (`mark`, `mkmk`, `ccmp`) survives. Keep name records (OFL requires the
   copyright and license notices to travel with a Modified Version; Noto declares no Reserved Font Name, so the
   family names may stay).
5. Name each output by content hash: `static/fonts/zn-serif.<hash8>.woff2`, `zn-sans.<hash8>.woff2`,
   `zn-mono.<hash8>.woff2`, `zn-cherokee.<hash8>.woff2`, `zn-syllabics.<hash8>.woff2`, `zn-devanagari.<hash8>.woff2`,
   `zn-tifinagh.<hash8>.woff2`. Delete the previous hashed file when the hash changes (a changed file must have a new
   name; `fonts_check.py` already enforces it).
6. Write `partials/fonts-names.css`: one `<style id="zth-fonts-names">` block with one `@font-face` per file,
   `unicode-range` generated from each subset's actual cmap, `font-display: block`, `size-adjust` from the measured
   ratios, `font-weight` ranges as the variable files allow.
7. Append each family's copyright line to `static/fonts/OFL.txt` if missing; run `fonts_check.py --record`.

Subsetting a Noto font is a Modified Version under the OFL 1.1; webfont use is distribution. The license text stays
beside the files, the name records stay in the files, and the credits name the families.

### 11.4 The gate (`tools/nations_lint.py`, fails the build)

For every published string, by role, every grapheme cluster must be covered whole by one face in the role's stack
(brand face union fallback faces, cmap read with fontTools, and the code point must also be inside that face's
declared `unicode-range`). Also: every label string in templates and in `herald.js`'s `TEXT` object is ASCII or a
code point present in `regions.json` display names; a `data-face="brand"` name contains no combining mark; every
`data-face="names"` name has every code point in `ZN Serif` (the fallback never itself falls back); no
`text-transform` rule reaches a name selector; `speechSynthesis` and `SpeechSynthesisUtterance` appear nowhere in
`nations/`, `nations.html` or `game/`. A miss reports `nation <id>: U+1E35 in name has no face in the names stack`
and stops the build. The fix is adding a face or a block to the subsetting rules, never editing the name.

### 11.5 Size classes

The build measures each name in grapheme clusters:

| `data-size` | clusters | herald | nation page `h1` |
|---|---|---|---|
| `xl` | up to 10 | `clamp(56px, 9vw, 128px)` | `clamp(48px, 7vw, 112px)` |
| `l` | 11 to 18 | `clamp(48px, 7vw, 104px)` | `clamp(40px, 5.6vw, 88px)` |
| `m` | 19 to 30 | `clamp(38px, 5vw, 76px)` | `clamp(34px, 4.2vw, 64px)` |
| `s` | 31 to 44 | `clamp(30px, 3.6vw, 56px)` | `clamp(28px, 3.2vw, 48px)` |
| `xs` | 45 and more | `clamp(26px, 3vw, 44px)` | `clamp(24px, 2.6vw, 40px)` |

Line height 1.04 for `brand`, 1.12 for `names`, 1.14 for script faces. `max-inline-size: min(100%, 26ch)`. The
longest name today (54 clusters) sets at 44 px on the owner's window and 26 px on a phone, three lines, balanced. A
round-3 name over 60 clusters raises a lint warning.

### 11.6 Other type

Region label and keys: mono 11 px, weight 500, 0.2 em tracking, uppercase, `--ink-3`. `Also known as`, `Say it`,
`Lands`: DM Sans 17 px, `--ink-2`. Fact: DM Sans `clamp(18px, 1.4vw, 22px)`, line-height 1.5, `--ink`, measure 58ch.
Receipt: mono 11 px, `--ink-2`, link underlined 1 px with 0.25 em offset, the date in `--ink-3`. Status line: mono
11 px, `--ink-4` (`#8A8A8A`, 6.6:1 on black, the floor). Section `h2`: Instrument Serif italic at `--fs-h2`; ledes
at `--fs-read`.

---

## 12. Tokens, colour, the lifted display

### 12.1 Tokens reused

`partials/tokens.css` carries, by name and value, the landing's `:root` tokens the nations pages use (`--serif`,
`--sans`, `--mono`, `--ease-out`, `--ease-ceremony`, `--dur-1`, `--dur-2`, `--dur-3`, `--fs-h2`, `--lh-h2`,
`--fs-read`, `--lh-read`, `--fs-label`, `--fw-label`, `--tr-label`, `--sp-1` to `--sp-10`, `--col-max`,
`--measure`, `--line-alpha-min`, `--ink` to `--ink-5`, `--rule`, `--rule-soft`, `--surface`, `--bg-floor`,
`--cochineal`), the `:root:not([data-theme])` Obsidian mono block (`#000000` floor, `#FFFFFF / #C8C8C8 / #A3A3A3 /
#8A8A8A / #4D4D4D`, `--rule rgba(255,255,255,0.16)`, `--surface #000000`, `--cochineal #FFFFFF`), and the three
`html[data-theme]` blocks (maya, codex, skeleton). `nations_lint.py` parses `--name: value;` pairs from `index.html`
and fails when any copied value drifts, so the nations pages can never diverge from the landing's themes without
touching `index.html`. `color-scheme: dark` in mono and the dark themes, `light` in codex.

### 12.2 Colour law

No hue anywhere on the nations pages in mono. Colour only for meaning: the focus ring (ink), the current ring dot
(ink), the chosen Appearance option (ink). Hover is neutral: `--ink-3` to `--ink-2` on links, the rim from 0.34 to
0.55 alpha on pills. Lines are `rgba(255,255,255,0.55)` or brighter where they must read as drawn (the name line, the
search rim, the control rims); `--rule` (0.16) only for the page's structural separators, as the landing uses it. In
the colour themes everything resolves through tokens; the fret and dots take `currentColor`.

### 12.3 Lifted-black law and one stylesheet

Flat `#000` ground. No vignette, no grain, no body fill under text, no dim gradient, no blur, no glow, no scale, no
sheen, no chrome rim on the card. The only fades are opacity on white text over black, which lifts cleanly: the
v*6+10 copy shows grey text on near-black, nothing pooled. The acceptance check lifts the stage at the fifty percent
point of a name fade and confirms the hairline at 0.55 alpha and the text at 0.5 alpha both stay crisp.

All nations pages share one external stylesheet, `static/nations/nations.<hash8>.css` (about 14 KB, immutable),
so an edit does not rewrite 450 files and the browser caches it once. The two font blocks stay inline on every page
(`zth-fonts` byte-identical to the landing; `zth-fonts-names` identical across nations pages) so font requests start
before the stylesheet arrives, the reason the landing gives. No `style=""` attributes anywhere; state goes through
classes and `data-` attributes. `style-src 'self' 'unsafe-inline'` as on the landing.

---

## 13. Layouts

### 13.1 Owner's window (1600 x 993 at 1.25, so 1280 x 794 CSS px)

Header 72 px. The herald stage fills `min(100svh - 72px, 760px)` as one centred column of `max-inline-size: 920px`,
left-aligned text (names read better ragged right than centred when they wrap). The name at `l` is 90 px. Controls
sit on the stage's bottom edge, the ring marks to the right of the buttons, the status line beneath, the lede under
that. The controls are visible without scrolling at 794 px. Below the fold: ring list and search side by side (7/5
columns), regions and countries in two columns, coverage and method in two columns, corrections, footer.

### 13.2 Phone (390 x 844 at 3)

Header: Menu left, wordmark centred; Appearance moves to the Menu sheet's foot as on the landing. The stage is
`100svh - 64px` with 16 px gutters. Name at `l` is 48 px; `xs` is 26 px; `text-wrap: balance` holds three lines at
most for every name in the data. Fact 18 px. Receipt wraps to two lines. Controls become a full-width row of three
equal pills, 48 px tall; the fifteen ring marks sit under them in one row (15 x 4 px dots with 6 px gaps and two
group gaps = about 150 px; they are display only, so no hit-area arithmetic applies); status and lede below. Sections
stack in one column. No horizontal page scroll at any width; the ring list and search never become carousels.

### 13.3 Between

640 to 1024 px: the stage keeps one column; ring list and search stack; regions in two columns from 720 px; the
header folds the nav into Menu under 1024 px as the landing does.

---

## 14. Accessibility

- Landmarks: `header`, `main`, `nav aria-label="Nations"`, `footer`; skip link to `#main`; one `h1` per page;
  headings in order (hub outline: Indigenous nations today > Today's ring > Find a nation > By region > By country >
  Where we are > How this is made > Corrections come first).
- The herald meets WCAG 2.2.2 by visible Pause and Next, pause on hover, focus and hidden tab, no auto-advance in
  Still or under `prefers-reduced-motion`, and resume where it paused. 2.3.3: all motion stops under reduced motion.
- One `aria-live="polite"` region, present and empty at load, filled only on Previous, Next and the first card when
  focus is inside the herald: `Nation: <name>. Lands: <lands>. <fact>`. No `also` list and no respelling read aloud.
- Names are DOM text with `dir="auto"`; `lang` only when sourced. Pronunciation is text with a credit; no page ever
  calls speech synthesis (the gate fails the build if it appears). No audio element on any nations page.
- Contrast: lowest text `#8A8A8A` on `#000` (6.6:1); lines at 0.55 alpha or more for anything that must be seen
  (3:1 or more); focus ring 2 px ink, 2 px offset, pill radius on pills. The build checks the four theme ladders
  against WCAG AA with a small contrast function.
- Targets: every control at least 44 x 44 CSS px (2.5.5).
- Search: labelled input, live count, results as links, arrow hand-off, Escape clears; no ARIA combobox.
- External links: visible publisher name, `rel="noopener noreferrer"`, a visually hidden `(opens in a new tab)`;
  the site sends `Referrer-Policy: no-referrer`.
- Tables: captions, header scope, stacked rows under 640 px.
- `theme-color #000000`; page titles as in section 21.

---

## 15. Data loading, caching, failure

### 15.1 Files the browser reads

| File | Size today | Cache-Control |
|---|---|---|
| inline `<script type="application/json" id="heraldIndex">` in `nations.html` | under 3 KB | with the page; hashed by csp_sync like every inline script |
| `static/nations/index.json` (same content, for tooling and the game later) | under 3 KB | `public, max-age=300, must-revalidate` |
| `static/nations/<region>.<hash8>.json` | 5 to 13 KB gzipped | `public, max-age=31536000, immutable` |
| `static/nations/search.json` | about 25 KB gzipped | `public, max-age=3600, must-revalidate` |
| `static/nations/status.json`, `coverage.json`, `news.json` | small | `public, max-age=300, must-revalidate` |
| `static/nations/nations.<hash8>.css` | about 14 KB | `public, max-age=31536000, immutable` |

The index is inline in the hub so the page and the shard names it carries always ship together: a visitor can never
hold a page that names shards a later deploy removed. Shards hold at most 100 nations; a region past 100 splits into
`<region>-1`, `<region>-2` and the index carries `shardSize`. Round 3's 600 nations fit.

Index shape: `{"v": 1, "built": "2026-10-10", "major": 1, "shardSize": 100, "regions": [{"k": "canada", "d":
"Canada", "n": 35, "ab": 35, "s": ["canada.3f9a1c2e.json"]}], "nations": 450, "lastCheck": null, "compiled":
"2026-10-08"}`.

Card shape in a shard (short keys; no evidence, no raw URLs beyond the ones shown):

```json
{"id":"secwepemc-bc-ca","n":"Secwépemc","a":["Shuswap"],"s":{"t":"suh-Wep-muhc","u":"https://tkemlups.ca/language-culture/","p":"Tk’emlúps te Secwépemc"},
 "l":"Secwepemcúl’ecw, a large territory ...","o":"https://shuswapnation.org/","r":"canada","sz":"xl","fc":"brand","sc":"latn","t":"A",
 "f":[{"t":"...","k":"today","y":"2026","p":"Shuswap Nation Tribal Council","u":"https://shuswapnation.org/about/bands/","d":"2026-10-08","h":false,"g":false}]}
```

`sz`, `fc`, `sc` are the build's typographic decisions; `h` true means `Checked by a person on <d>`; `g` true means
the grace line is appended.

### 15.2 Sequence

1. HTML paints with the static first card; its CSS ceremony begins; controls are visible.
2. The inline app reads the inline index, computes today's ring, and fetches the shard for the first unseen ring
   nation (`fetch`, same origin, `credentials: 'omit'`, 4 s `AbortController` timeout).
3. Shards for the next two ring nations prefetch during the first dwell, one at a time, never more than one request
   in flight.
4. On any fetch failure the herald keeps the static card and the status line reads `More nations could not load.
   Every nation still has its own page under By region.` Nothing is invented.
5. `search.json` loads only on first focus of the search field. `status.json` loads once, after the first dwell, to
   compute `overdue`.

### 15.3 Validation in the browser

Though the data is first-party, the app validates each card as the game does (id pattern, string lengths, `https`
URLs, dates not in the future, same-origin shard URL) and drops what fails. Strings are set with `textContent`. As a
last guard, U+2013 and U+2014 in data become a comma and a space.

### 15.4 `game.json` (specified, not emitted at launch)

Shape the game's `natValid` accepts: `{"updated": "<date>", "nations": [{"id", "name", "also", "pronounce":
{"text", "source_url"}, "lands", "countries": [display names], "official_url", "region": display name, "facts":
[{"text", "kind", "as_of", "source": {"title", "publisher", "url", "accessed": last_verified}}]}]}`, publishable
facts only. Before it can be served: the game's caps move from 524,288 bytes to 1,048,576 and from 600 to 1,200
nations, the host page gets `connect-src 'self'`, and the build asserts the same `generated` value and fact id set
as the shards. Off by default (`--game-json`); the game stays unlinked.

---

## 16. CSP, headers and the three site tools

### 16.1 `vercel.json` entries (added; existing entries untouched)

```json
{ "source": "/nations",
  "headers": [{ "key": "Content-Security-Policy",
    "value": "default-src 'none'; base-uri 'none'; object-src 'none'; script-src 'sha256-<bootstrap>' 'sha256-<appearance>' 'sha256-<herald>' 'sha256-<index-json>'; script-src-attr 'none'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self'; form-action 'none'; frame-src 'none'; worker-src 'none'; manifest-src 'none'; frame-ancestors 'none'" }] },
{ "source": "/nations.html", "headers": [ same as /nations ] },
{ "source": "/nations/(.*)",
  "headers": [{ "key": "Content-Security-Policy",
    "value": "default-src 'none'; base-uri 'none'; object-src 'none'; script-src 'sha256-<bootstrap>' 'sha256-<appearance>'; script-src-attr 'none'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'none'; form-action 'none'; frame-src 'none'; worker-src 'none'; manifest-src 'none'; frame-ancestors 'none'" }] },
{ "source": "/static/nations/(.*)\\.([0-9a-f]{8})\\.(json|css)",
  "headers": [{ "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }] },
{ "source": "/static/nations/(index|status|coverage|news)\\.json",
  "headers": [{ "key": "Cache-Control", "value": "public, max-age=300, must-revalidate" }] },
{ "source": "/static/nations/search\\.json",
  "headers": [{ "key": "Cache-Control", "value": "public, max-age=3600, must-revalidate" }] }
```

Notes: `connect-src 'self'` only on the hub, the only nations page that fetches; `'none'` on every other nations
page. No `formspree.io` under `/nations`. `mailto:` is navigation, not a form, so `form-action 'none'` holds. The
hub is `nations.html`, so `/nations/(.*)` never serves it and the `/nations/index` edge does not exist. The
`/nations/(.*)` policy also lands on nothing else: shards live under `/static/`. The three cache patterns are
disjoint. Each built page carries the same policy in its `<meta http-equiv="Content-Security-Policy">`. The JSON
index block is `type="application/json"`, not executed, but `csp_sync.py` hashes every inline script body, so its
hash is in the hub's list; that keeps one rule: every inline script body on the site is named in the policy. The
index changes weekly, so one hub hash changes weekly; the build runs `csp_sync.py` so policy and page ship together.

### 16.2 Extending `tools/csp_sync.py`

`PAGES` becomes a table of groups:

```python
GROUPS = [
    {"name": "index.html",     "files": ["index.html"],    "sources": ["/", "/index", "/index.html"]},
    {"name": "download.html",  "files": ["download.html"], "sources": ["/download", "/download.html"]},
    {"name": "nations hub",    "files": ["nations.html"],  "sources": ["/nations", "/nations.html"], "strict": True},
    {"name": "nations pages",  "files": glob("nations/**/*.html"), "sources": ["/nations/(.*)"], "strict": True},
]
```

Behaviour: every file in a group is hashed; a group's files must produce the same hash set, or `--check` reports
`nations/<file>.html: inline scripts differ from the group` and exits 1 (generated pages come from one template, so
this holds by construction and catches a template edit that touched only some pages). The meta CSP of every file in
the group and the `script-src` of every header entry whose source is in the group's list are rewritten to the group's
hash list, exactly as today; other directives untouched. For `strict` groups a second check requires the whole meta
policy of every file to equal the header policy byte for byte (not only `script-src`). A group whose files are
missing is skipped, so the landing repo without a nations build still passes. `page_for_source()` becomes a lookup
over `GROUPS`. CRLF handling, html.parser hashing, `'none'` for a page with no inline script and canonical JSON
formatting stay as they are. `tools/release.py check` keeps calling `csp_sync.py --check` unchanged.

### 16.3 Extending `tools/lint_copy.py`

`DASH` becomes the set `{"\u2014", "\u2013"}`; `JS_ESC` covers `\u2013` and `\u{2013}`; the CSS `content:` check
covers `\2013`; the default file list adds `nations.html` and `nations/**/*.html`. Code comments stay exempt. The
summary line reads `no em or en dash in visible copy`.

### 16.4 Extending `tools/fonts_check.py`

- `PAGES` gains `nations.html` and every built `nations/**/*.html`. The `zth-fonts` block must be identical across
  all pages (the landing's block pasted verbatim into the nations templates).
- Second block: every nations page carries exactly one `<style id="zth-fonts-names">`, identical across nations
  pages, forbidden on `index.html` and `download.html`; every `url(...)` in it exists under `static/fonts/`, is
  `.woff2`, is in the manifest, uses `font-display: block` or `swap`, and no third-party host appears.
- A file counts as used when either block names it; the orphan rule then also verifies the build's delete step.
- Preload: each page's preload must be a file a block on that page uses; nations pages preload
  `instrument-serif-latin.woff2` (upright, the names face), the landing keeps the italic.
- `font-src 'self'` exact, on every meta and header, unchanged.

### 16.5 `tools/nations_links.py`

Every internal `href` and `src` in `nations.html` and `nations/` resolves to a built file, a landing anchor that
exists in `index.html`, or a `static/` file. Every external `href` is `https:`, appears in `nations.json` (source
URLs, official sites, pronunciation sources) or in a three-entry allowlist (the UN background page, the World Bank
page, the GitHub repository when `repo_public` is true); `formspree.io` is never allowed; every external anchor has
`rel="noopener noreferrer"`. Every `mailto:` uses `site.json.contact`.

### 16.6 `.vercelignore` and the sitemap

`.vercelignore`: `data/`, `tools/`, `game/`, `docs/`, `.github/`, `*.md`. The first preview confirms
`/data/nations/nations.json` and `/game/index.html` return 404. `sitemap.xml` keeps its existing entries and gains,
between `<!-- nations:start -->` and `<!-- nations:end -->`, every indexable nations page (`/nations`, 450 nation
pages, 15 region pages, 99 country pages, the seven support pages); `robots.txt` is unchanged.

---

## 17. Build tooling

### 17.1 `python tools/nations_build.py` (deterministic; `py -3.10` on the owner's machine)

1. Run `data/nations/tools/validate.py`. Load `nations.json`, `regions.json`, `countries.json`,
   `pronounce_publishers.json`, `site.json`, `changes.json`, `verify/human.json`, `verify/history.json`,
   `data/news/flags.json`; apply `overrides.json` last.
2. Derive display states (9.1), tiers (ARCHITECTURE 2.3), the ring for the build date, typographic decisions (11.2,
   11.5), folded search keys (7.1).
3. Render pages from the templates with a small substitution function: every value through `html.escape(quote=True)`;
   URLs pass only when they match `^https://[^\s"<>]+$`; no template engine, stdlib only.
4. Write `static/nations/*.json` with sorted keys, `ensure_ascii=False`, minified; name shards and the stylesheet by
   the first eight hex characters of `sha256` of their bytes; delete superseded hashed files.
5. Write `status.json` and `coverage.json`; append the sitemap block; write a `redirects` entry per
   `redirects.json` row.
6. Run `tools/nations_fonts.py`, then `tools/fonts_check.py --record`.
7. Run `tools/csp_sync.py`.
8. Run the gates: `tools/nations_lint.py` (glyphs, fold parity, labels, tokens drift, header partial drift, reserved
   ids, banned terms, no speechSynthesis), `tools/lint_copy.py` on all pages, `tools/fonts_check.py`,
   `tools/csp_sync.py --check`, `tools/nations_links.py`, a scan of `nations.html` and `nations/` for U+2014,
   U+2013, `speechSynthesis`, `http://`, `googleapis`, `formspree` (all zero), and size budgets (hub under 60 KB
   gzipped, nation page under 12 KB gzipped, `herald.js` under 16 KB unminified, stylesheet under 14 KB).
9. Print a summary: pages, shards and sizes, fonts and sizes, hidden and review counts, tier counts, whole-name
   fallbacks.

Output is byte-stable for the same input (no timestamps beyond the data's own dates and the build date from
`--build-date`, defaulting to the newest `checked` date), so a re-run with no data change produces no diff.
`--check` builds into a temporary directory and diffs against the committed output, exiting 1 on any difference, so
the committed build is always the build of the committed data; CI runs it. `--seed-last-verified` is the one-time
migration of 9.2. A failed gate writes nothing to the tree.

### 17.2 The app and the templates

- `bootstrap.js`: the landing's first-paint theme and motion script verbatim (lines 28 to 46), one hash shared by
  every page on the site.
- `appearance.js`: about 2 KB, the Theme and Motion radios, saved under the landing's keys, the reduced-motion note.
- `herald.js`: about 12 KB unminified, plain ES2017. Modules: index parse, ring, walk (`fnv1a32`, `feistel4`), shard
  fetch with timeout, card render (`textContent` only), choreography (class toggles and `animationend`), pause
  conditions, ring marks, live region, search with the emitted fold table, status (`overdue`). Strings in one `TEXT`
  object at the top for lint.
- Templates: `hub`, `nation`, `region`, `country`, `about`, `sources`, `coverage`, `credits`, `verification`,
  `for-nations`, `changes`. Partials: `head` (meta CSP placeholder, both font blocks, the stylesheet link, the
  preload), `header`, `footer`, `tokens.css`.

Run locally: `py -3.10 tools\nations_build.py`, then `py -3.10 -m http.server 8000` and open
`http://localhost:8000/nations.html` (the local server has no cleanUrls; `--local-links` emits `.html` suffixes into
a scratch build only).

---

## 18. The weekly job, pull-request mode

`.github/workflows/nations-refresh.yml`. Scheduled workflows run only on the default branch (`main`), so the file
does nothing until `feat/nations` merges.

```yaml
name: nations-refresh
on:
  schedule:
    - cron: "17 9 * * 1"        # Mondays 09:17 UTC, off the top of the hour
  workflow_dispatch:
    inputs:
      limit:
        description: "URLs to check this run (0 = all)"
        default: "0"
permissions:
  contents: write
  pull-requests: write
concurrency:
  group: nations-refresh
  cancel-in-progress: false
jobs:
  refresh:
    runs-on: ubuntu-latest
    timeout-minutes: 240
    steps:
      - uses: actions/checkout@<pinned full SHA>
      - uses: actions/setup-python@<pinned full SHA>
        with:
          python-version: "3.10"
      - run: pip install --require-hashes -r tools/requirements-nations.txt
      - name: Re-check every cited source
        run: python data/nations/tools/nations_refresh.py --file data/nations/nations.json --run-date "$(date -u +%F)" --host-interval 3 --limit "${{ inputs.limit || 0 }}" --report-dir data/nations/tools
      - run: python data/nations/tools/validate.py
      - run: python tools/nations_history.py --append data/nations/tools/refresh_report.json
      - run: python tools/nations_build.py
      - name: Open a pull request if anything changed
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          d="$(date -u +%F)"; b="nations/refresh-$d"
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git checkout -b "$b"
          git add data/nations nations nations.html static/nations static/fonts tools/fonts.sha256 vercel.json sitemap.xml
          if git diff --cached --quiet; then echo "No change this week"; exit 0; fi
          git commit -m "nations: weekly check $d" -m "$(python tools/nations_report_summary.py data/nations/tools/refresh_report.json)"
          git push -u origin "$b"
          gh pr create --base main --head "$b" --title "Nations re-check $d: $(python tools/nations_report_summary.py --short data/nations/tools/refresh_report.json)" --body-file data/nations/tools/refresh_report.md --label nations-refresh
```

What the owner does once: enable "Allow GitHub Actions to create and approve pull requests" in the repository's
Actions settings; pin the two action SHAs; create the `nations-refresh` label. Vercel's Git integration builds a
preview for the branch; merging deploys production.

Honest consequence, stated on the panel and the verification page: in pull-request mode a fact whose words vanished
stays on the site until the pull request is merged (`Changes from a check go live after review.`). The overdue
sentence appears at 14 days, so a forgotten pull request is visible on the page. If the owner later allows lane 1
(direct commit for hide-only changes), the step gains a branch: hide-only diffs push to `main`, everything else
opens the PR (ARCHITECTURE 3.5). GitHub facts designed around: schedules are delayed under load and run only on the
default branch; a public repository disables schedules after 60 days without activity (merging the weekly PR is
activity; `workflow_dispatch` stays available; the overdue sentence tells the truth). Polite fetching as the tool
does: the honest user agent, robots.txt obeyed, one request per host every three seconds, 20 s timeout, two retries,
never `--ignore-robots`, no stealth fetcher; 742 URLs take roughly 40 to 60 minutes.

---

## 19. The news shelf: built, hidden

`tools/news_fetch.py` and `data/news/sources.json` are built and tested in stage 8. `data/news/flags.json` holds
`{"shelf_visible": false}`. While false: the hub template emits no shelf markup, the build writes
`static/nations/news.json` as `{"shelf": false, "gathered": null, "items": [], "outlets": []}` (no outlet name
ships), no page links a shelf, and `.github/workflows/news-refresh.yml` carries `workflow_dispatch` only (no outlet
is polled before the owner decides who signs the courtesy letters). Flipping the flag and rebuilding ships it:
eyebrow `FROM INDIGENOUS-LED NEWSROOMS`, a headline list (title as a link, outlet, date, `lang` from the feed), round
robin by region, the line `Headlines gathered <date, time UTC>`, the outlet list beneath, and `No headline source yet
for: <regions>`. Hairlines only, no images, no logos. The fetcher keeps title, outlet, date and link; strips tags;
caps titles at 160 characters; drops items dated more than a day ahead; keeps only https links whose host is on that
outlet's allowlist; turns U+2014 and U+2013 in a headline into a spaced hyphen without changing a word; dedupes by
canonical link; 30-day window; at most 10 per outlet. The nine passing feeds of ARCHITECTURE 6.3 go in
`sources.json` with their leadership evidence; the three still missing an evidence phrase stay `"enabled": false`.

---

## 20. The landing tie-in (minimal; no script changes, so no hash changes)

Three markup touches on `index.html` in the worktree, each checked by `csp_sync.py --check`, `lint_copy.py` and
`fonts_check.py`:

1. Header nav (line 7187 to 7195): `<a href="/nations" data-nav-section="nations">Nations</a>` before `FAQ`. The
   header nav is six mono links plus Menu; the acceptance check confirms one line at 1280 and 1024 CSS px. If the
   seventh link wraps on the owner's hardware, it is removed from the header and Nations stays in the Menu sheet and
   the footer (the owner's call, open decision 5).
2. Menu sheet (`#navSheet`, after `--i:12`): `<li style="--i:13"><a href="/nations"><span class="ns-num"
   aria-hidden="true"><span class="maya-num"><span class="b"></span><span class="b"></span><span class="d"></span><span class="d"></span><span class="d"></span></span></span><span class="ns-name">Nations</span></a></li>`
   (thirteen in codex dots: two bars and three dots).
3. Footer, Release column (line 8515): `<a href="/nations">Indigenous nations today</a>` after `Download status`.
   And one sentence appended to the `#roots` paragraph: `That work has a first page: <a href="/nations">Indigenous
   nations today</a>, their own names first, every fact with its source and the date it was checked.`

Dropped from the winning concept: the day-chip "Named today" fetch and the `connect-src 'self'` widening of the
landing's policy. The landing makes no new request and its CSP is untouched.

---

## 21. Exact copy

Titles: hub `Indigenous nations today | ZOTHEOS`; nation `<Name> | Indigenous nations today`; region and country
`<Display> | Indigenous nations today`; `Where we are`, `Sources`, `How this is made`, `Credits`, `Verification`,
`For nations`, `Corrections and removals`, each `| Indigenous nations today`. Hub description: `One nation named at a
time, as it names itself, with one checked fact and its source. 450 nations, 1,260 facts, re-checked weekly.`
(counts filled by the build).

Card keys and controls: `Also known as`, `Say it`, `Pronunciation: <publisher>`, `Pronunciation: <Name>, on its own
site`, `Lands`, `Countries`, `Source: <publisher>`, `As of <year>`, `Checked <date>`, `Checked by a person on
<date>`, `Our tool could not reach the page on <date>`, `Open this nation`, `Nation's own site`, `Visit the nation's
own site`, `Previous`, `Pause`, `Resume`, `Next`, `Today's ring`, `<n> of 15 in today's ring`, `<count> nations`,
`Last check <date>`, `Compiled <date>`, `Press Next for the next nation.`, `More nations could not load. Every nation
still has its own page under By region.`, `This page shows one nation. Every nation has its own page under By
region.`, `Search needs JavaScript. The region lists below hold every nation.`, `Ring for <date>`, `Facts in
progress. This entry lists the nation by its own name while facts are compiled and checked.`, `1 fact is being
re-checked.`, `<n> facts are being re-checked.`, `<n> facts are under review.`, `Suggest a correction`, `Removed at a
nation's request.`, `No corrections or removals yet.`

Search: `Find a nation`; placeholder `Name, other name, place or country`; helper `Accents are optional: Maori finds
Māori, Dine finds Diné. Names always show as the nation writes them.`; `Loading the name list`; `<n> nations match`;
`1 nation matches`; `No nation matches yet. Try another spelling, a place, or browse by region.`; `Show all`.

Section headings and ledes: section 4. Verification sentences: section 9.3 and 9.4. For nations: 10.3. Credits: 10.1.
All strings in `herald.js` live in `TEXT`; lint reads it for the dash and glyph rules.

---

## 22. Stages on `feat/nations`

One commit per stage. The owner's standing instruction for this work is to commit and push; each stage commit is
pushed to `origin/feat/nations` (a feature branch; `main` is the live site and is never pushed to from here).

| Stage | Ships | Done when |
|---|---|---|
| 1 | `regions.json`, `countries.json`, `overrides.json` (the two Bhil holds), `pronounce_publishers.json`, `site.json`, `changes.json`, `redirects.json`, `verify/human.json`, `verify/history.json` (the sample run), `data/news/flags.json`; `.vercelignore`; `validate.py` gains optional `last_verified`; `nations_refresh.py` writes `last_verified` on pass; `nations_lint.py` with reserved ids, tokens drift, header drift and the glyph audit (report only) | `validate.py` passes; lint prints the ten whole-name fallbacks and the Devanagari titles; `--seed-last-verified` sets 1,260 dates |
| 2 | `tools/fonts-src/` vendored; `nations_fonts.py`; the names font block; `fonts_check.py` extension; manifest recorded | Every name, also, pronunciation, lands, fact, title and label code point is covered; the gate fails on a deliberately injected U+A78C |
| 3 | `nations_build.py` with the hub, nation, region and country templates; the stylesheet; `csp_sync.py` groups; `lint_copy.py` extension; `nations_links.py`; sitemap; `vercel.json` entries | `nations.html`, a nation page and a region page open from a local server with the CSP meta in place, JavaScript off, zero third-party requests |
| 4 | `herald.js`: ring, walk, choreography, controls, live region, search, status | The browser checks in section 23 pass in Living, Calm, Still and with storage blocked |
| 5 | About (with the type sample), sources, coverage, credits, verification, for-nations, changes | Every gate green; lifted-copy screenshots show text and lines only |
| 6 | `nations-refresh.yml`, `nations_history.py`, `nations_report_summary.py`, `requirements-nations.txt` with hashes | A dispatch on a fork opens a pull request whose body is the report |
| 7 | The landing tie-in (three touches) | `csp_sync.py --check`, `lint_copy.py`, `fonts_check.py` pass on `index.html` with its hashes unchanged |
| 8 | `news_fetch.py`, `sources.json`, `news-refresh.yml` (dispatch only), the shelf template behind the flag | The hub emits no shelf; `news.json` holds no outlet name; flipping the flag in a scratch build renders the shelf |
| 9 | Hardware verification by the owner: 1280 x 794 and 390 x 844, lifted copy, no-JS, network panel, NVDA | Findings fixed; merge decision |

---

## 23. Test plan

Unit and tool tests (`py -3.10 -m pytest tools/tests`):

- `feistel4`: for every region count in the data and for n in 1 to 300, the permutation of 0 to n-1 is a bijection;
  cycle-walking terminates.
- Ring determinism: two seeds built from the same date and version give the same fifteen ids in the same order;
  different dates differ.
- Fold parity: 1,200 strings through the Python table and the emitted JavaScript table (run with `node`) agree.
- Search cases: `Maori` finds Māori; `Dine` finds Diné; `oodham` finds Tohono O’odham and Akimel O’otham;
  `Musqueam` finds xʷməθkʷəy̓əm through `also`; `Toba` finds Qom through `also_search` and the result shows no
  `Also known as Toba` line; a Cyrillic paste finds the RAIPON entries; `Hopi` ranks Hopi before any lands match.
- Build `--check`: a second run with no data change produces no diff; changing one `also` changes exactly one shard
  name, the search index, one nation page, the inline index and the hub's hash list.
- Glyph gate: injecting U+A78C into one name fails with the nation id and the code point; injecting a combining mark
  into a `data-face="brand"` name flips it to `names`.
- `csp_sync.py --check`: editing one generated page's inline script fails the group; the `strict` whole-policy check
  fails when a meta differs from its header.
- `lint_copy.py`: a U+2013 in a built page fails; a U+2013 inside a JavaScript comment passes.
- `nations_links.py`: an external link not in the data fails; a `formspree.io` link fails; a missing
  `rel="noopener noreferrer"` fails.
- Display states: a fixture with `unreachable` and `last_verified` 10 days old is shown with the grace line; 15 days
  old is hidden and counted; a `human.json` record under 90 days shows `Checked by a person`; over 90 days hides.
- Overrides: the two Bhil holds leave the nation tier B with one fact and the page says `2 facts are under review.`
- Evidence break (ARCHITECTURE 10.4): change one evidence phrase in a local copy, run the verifier against a local
  mirror and the build: the fact leaves the shard and the page, the nation page says `1 fact is being re-checked.`,
  the verification page counts it under its publisher.

Browser checks (owner's window 1280 x 794 and phone 390 x 844, Living, Calm, Still, OS reduced motion):

- Lifted copy (v*6+10) of the stage at 0 ms, 650 ms (mid name fade), 1350 ms (line drawn) and full card: text and
  hairline only, no field, no slab.
- The longest name sets at 44 px in three lines on the owner's window and at 26 px on the phone; controls are
  visible without scrolling at 794 px; no horizontal scroll at any width; every control 44 px or more.
- Living beats match section 5.1 within 50 ms (`animationstart` logging in dev). Calm: two beats. Still: no motion,
  no auto-advance, Pause hidden. OS reduced motion with Motion set to Living reads as Still.
- Hover, focus, tab hidden and off-screen each pause the dwell and resume from the remaining time.
- Two devices on the same local date show the same fifteen ring nations in the same order; after the ring they
  differ. 200 presses of Next on one device: no repeat inside a region before the region is exhausted.
- Storage blocked (private window, storage denied): the herald works and varies.
- `document.fonts` wait: no name shows in a system face at any point (recorded at 60 fps and stepped); the ten
  fallback names render whole in one face; the type sample at `/nations/about#type` shows Nisg̱a’a with the macron
  under the g, Kanien’kehá:ka, ǂKhomani, ᐃᓄᐃᑦ-style syllabics, ᏣᎳᎩ and a Devanagari title with no tofu.
- NVDA: one announcement per Next or Previous; silence during auto-advance; the search count announces once per
  settled query.
- Network panel on the hub, a nation page and a region page: only same-origin requests; nation pages make no fetch.
- First preview deploy: `/nations` serves the hub; `/nations/` redirects; `/nations/secwepemc-bc-ca` serves the
  page; `/data/nations/nations.json` and `/game/index.html` are 404; response headers show the hub policy on
  `/nations` and the pages policy on `/nations/x`; `/static/nations/<shard>` is immutable.
- `/nations/about` does not mention the game; no nations page links to the game.
- Landing: `csp_sync.py --check`, `lint_copy.py`, `fonts_check.py`, `release.py check` pass; the header stays one
  line at 1280 and 1024 with the seventh link.
- grep of `nations.html` and `nations/` for U+2014, U+2013, `speechSynthesis`, `googleapis`, `formspree`,
  `http://`: zero.

---

## 24. Risks and mitigations

| Risk | Mitigation |
|---|---|
| 1. Vercel does not serve `nations.html` at `/nations` beside a `nations/` directory | Confirm on the first preview. Fallback: emit `nations/index.html` instead, move the hub group's sources to `/nations`, `/nations/index`, `/nations/index.html`, and exclude those three from the pages group by listing them first (Vercel applies every matching entry; the pages policy is a subset of the hub policy for `script-src` only through hashes, so the hub group must carry both hash sets in that fallback) |
| 2. Pull-request mode leaves a failed fact visible until merge | The panel says so; the overdue sentence at 14 days; lane 1 is one flag away |
| 3. Hosts that refuse the tool (about 5 to 7 percent of facts) | `last_verified` grace of 14 days from the first full run, visible and dated; the human lane; the verification page counts them |
| 4. No full check has run yet | The `no-check` and `partial` states exist so the first deploy tells the truth |
| 5. Patchy glyph fallback inside a name | Whole-name rule at build; `size-adjust` from measured x-heights; grapheme-cluster gate |
| 6. A name shows briefly in a system font | `document.fonts.load()` before the fade, `font-display: block` on ZN faces, 600 ms cap |
| 7. Synthetic italic on a syllabary or any italic on a name | Names upright everywhere; `font-synthesis: none`; lint fails on `text-transform` or `font-style: italic` reaching a name selector |
| 8. Long names on phones | Size classes to 26 px, `text-wrap: balance`, measured against the 54-character maximum |
| 9. The owner's display lifting near-black | Flat `#000`, no fills, opacity on text only, hairlines at 0.55 alpha where drawn; lifted-copy checks |
| 10. Auto-advance disturbing readers | Pause on hover, focus, hidden, off-screen; Still and reduced motion never advance; 7 s floor |
| 11. Screen reader chatter | Announcements only on user events |
| 12. CSP hash drift on 450 pages | One template, one hash set, group equality in `csp_sync --check` |
| 13. Weekly `vercel.json` churn from the inline index hash | One line per week, rewritten by the build inside the PR; accepted for the consistency the inline index buys |
| 14. `data/` and `game/` would deploy | `.vercelignore` in stage 1; first-preview 404 checks |
| 15. Scheduled workflow disabled or delayed | Weekly PR, manual dispatch, the overdue sentence from `status.json` |
| 16. Noto sources drift between builds | Vendored TTFs with recorded hashes; subsets named by content hash; manifest and orphan rules |
| 17. Dashes slipping in through data | `validate.py` refuses them; the app's last guard; `lint_copy` on every built page |
| 18. Country names carry politics | ISO 3166 short names only, labelled present-day; `countries.json` can be overridden by the advisory circle |
| 19. A near-spelling returns the wrong people | No fuzzy matching; token prefix; region and lands on every result |
| 20. The game's caps and coupling | `game.json` specified, not emitted; the game unlinked; caps raised only when it is wired |
| 21. The two Samoans entries confuse a reader | Lands and countries on every list row and result; the ring never shows both on one day (different regions can, by chance; accepted) |
| 22. Named individuals | Bhil facts held at launch under `overrides.json`; the AU personal-name warning stays in validate |
| 23. Status words read as blame | Reasons name the page's change, never the people; counts by publisher by default; nation pages say "being re-checked" or "under review" |
| 24. A nation asks for removal while a PR is open | An editor's `overrides.json` entry is always allowed on `main`; the next build drops the nation everywhere; the log shows only the fixed sentence |

---

## 25. Open decisions (owner only; the build runs without them)

1. Corrections address: `contact@zotheos.org` (the only address the site publishes) or a role address; one
   constant in `site.json`.
2. Whether the repository is public: affects the 60-day schedule rule and whether `/nations/verification` and
   `/nations/changes` may link to pull requests or issues (`site.json.repo_public`).
3. Pull request only (built) or lane 1 direct commits for hide-only changes.
4. Who signs the outlet letters; the news shelf stays behind `shelf_visible: false` until then.
5. Whether the header nav carries a seventh link `Nations` (built; removed if it wraps on the owner's hardware).
6. The two Bhil facts naming Bhuri Bai: publish (delete the two override entries) or keep held until the advisory
   circle exists.
7. Whether anyone besides the founder is named under People on the credits page.
8. Whether the hidden-facts table on the verification page may name nations (`hidden_table_names_nations`).

---

## 26. Sources this spec rests on

ARCHITECTURE.md section 12 (UNDRIP, UN and World Bank figures, GitHub schedule behaviour, WCAG 2.2.2, aria-live,
RFC 9309, CARE, Local Contexts); the research brief of 2026-10-10 (BC Indigenous content guide on upright names;
NMAI terminology; LAC supplied-title pattern; AIATSIS sensitivity and takedown model; WAI carousel tutorial; Noto
coverage listings and release files; OFL FAQ on subsetting; code points for ʻokina, saltillo, syllabics, Cherokee,
Tifinagh); and the measurements in section 0, taken from the files in this worktree on 2026-10-10.
