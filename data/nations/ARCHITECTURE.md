# Nations: system architecture

Compiled 2026-10-08 for zotheos.org (static site on Vercel, repo `C:\ZOTHEOS-Web`).
One data spine feeds three surfaces: the **game** (Ollamaliztli title herald, level cards, credits), the
**learning hub** (`/nations`), and the **news shelf** (headlines from Indigenous-led newsrooms).

Writing rule for this document and every string it specifies: no em dash, no en dash. Ranges are written "4 to 12".

---

## 0. Key decisions (read this first)

1. **The nation's own name leads, always.** Every card shows the name as the nation publishes it, with its
   diacritics and letters intact. Exonyms are secondary, in smaller type, and a name the nation rejects is never
   shown, even as "also". Grounding: UNDRIP Article 13(1) affirms the right of Indigenous peoples "to designate and
   retain their own names for communities, places and persons" (source in section 12).
2. **Source files follow the contract exactly.** Everything else (verification state, overrides, coverage,
   relations) lives in sidecar files, so the regional authors' JSON never changes shape.
3. **Constant verification is real, not theater.** A build-time tool re-fetches every cited page weekly, checks that
   the stored evidence phrase still appears after normalization, updates `accessed` on success, and hides any fact
   that fails. Hiding is automatic and immediate; restoring needs a human. Every fact in the hub shows the date it
   was last checked.
4. **The site makes zero third-party requests.** Pages load only same-origin JSON, fonts and images. Sources and
   headlines are plain links that leave the site only when a person clicks them.
5. **Rotation has two layers.** A shared **Daily Ring** (seeded by date, the same for everyone that day) and a
   per-device **Personal Walk** (a keyed permutation plus a local cursor), so every visit shows nations not yet seen
   on that device, and regions take turns so no part of the world is drowned out by list size.
6. **No synthesized speech of names, ever.** Pronunciation appears only when a source gives it, credited, and only
   as text. Recorded audio comes later, only from a nation's own published audio or with its written permission.
7. **The herald is DOM text, not canvas text,** so screen readers can read it, `lang` can be set, and per-glyph font
   fallback works. Names get their own self-hosted font stack with a build gate that fails on any missing glyph.
8. **Nations are never game objects.** No nation appears on a fail or "caught" screen, next to the antagonist, as a
   collectible, a level name, a difficulty, a score, or a reward. Knowledge about peoples earns no points.
9. **News is headlines only** (title, outlet, date, link), fetched at build time from outlets that state on their own
   pages that they are Indigenous-owned, Indigenous-run or Indigenous-led. Nine feeds pass today (section 6).
10. **Nations can take anything down, no reason needed.** Hide first, ask second. Acknowledge every correction within
    72 hours; act on a nation's own request within 72 hours (target 24).
11. **No territorial boundaries are drawn.** The map shows countries and regions only. Even Native Land Digital, the
    best-known territory map, says its maps "are not official sources".
12. **Honest scale.** The UN estimates 476 million Indigenous people in 90 countries representing 5,000 different
    cultures. We start near 350 entries, publish our coverage against cited denominators, and say where we are thin.

---

## 1. Principles and grounding

| Principle | What it means in the build | Grounding |
|---|---|---|
| Own names | Lead with the self-published name; never "correct" a spelling; never swap a letter for a lookalike the font has | UNDRIP Art. 13(1) |
| Self-identification | Include peoples who identify as Indigenous even where a state denies the term; never gate inclusion on state recognition | UNDRIP Art. 33(1): the right "to determine their own identity or membership" |
| Cultural control | No sacred, ceremonial or restricted knowledge; traditional games and designs are the peoples' heritage, so we credit and never claim them | UNDRIP Art. 31(1) names "sports and traditional games" among protected heritage |
| Data authority | The nation's own word outranks any registry; nations can correct or remove; we do not offer the dataset for bulk reuse at launch | CARE Principles for Indigenous Data Governance (GIDA), "people and purpose-oriented" |
| Still here | Present tense, living peoples, strengths first; history only as context for today | Respect rules in the brief |
| Honest metrics | Every count has an `as_of` year and a source; every coverage number shows its denominator and that denominator's source | ZOTHEOS "no theater" rule |

---

## 2. Data

### 2.1 The contract (source files, exact shape)

One file per region: `data/nations/regions/<region>.json`, UTF-8, valid JSON:

```json
{ "region": "<key>", "compiled": "2026-10-08", "nations": [
  { "id": "ascii-kebab-unique-with-region-hint",
    "name": "self-published name with correct diacritics",
    "also": ["other common names incl. exonyms, neutral"],
    "pronounce": null,
    "lands": "present-day places and countries, plain words",
    "countries": ["US"],
    "official_url": "https://... or null",
    "name_source_url": "https://...",
    "facts": [ { "text": "max 200 chars, own words, no em or en dash",
                 "kind": "today|language|governance|land|culture|history|achievement|population",
                 "as_of": "2026 or null",
                 "source": { "title": "", "publisher": "", "url": "", "accessed": "2026-10-08" },
                 "evidence": "4 to 12 words copied verbatim from the source page" } ] } ] }
```

`pronounce` is either `null` or `{ "text": "...", "source_url": "..." }`.

Rules the linter enforces (section 9.2 has the full list): ids unique across all regions and never reused; `kind`
in the enum; `countries` valid ISO 3166-1 alpha-2; every URL `https://`; no `wikipedia.org` (or any wiki mirror) in
`source.url`, `name_source_url` or `pronounce.source_url`; `text` at most 200 characters with no U+2014 or U+2013;
`evidence` 4 to 12 words; `as_of` required when `text` contains a digit that is a count, percentage or status year.

### 2.2 Sidecar files (everything that is not the contract)

| File | Written by | Purpose |
|---|---|---|
| `data/nations/regions.json` | editors | Region registry: key, display name (plain geography), sort order, `merge_into` for small regions (2.6) |
| `data/nations/universe.json` | editors | Per-country denominators for coverage, each with its own source, `as_of` and evidence (2.5) |
| `data/nations/relations.json` | editors, later | Optional links between entries: `member_of` (a nation within a confederacy or a wider people), `same_people_across` (one people, several states). Never required, never used to merge entries |
| `data/nations/overrides.json` | editors, nations | `hide`, `takedown`, `rename`, `pin_name`, `drop_also` actions by nation id or fact id, with reason code, date, and requester class (`nation`, `reader`, `editor`). Applied last, so it always wins |
| `data/nations/verify/state.json` | verifier | Per-fact and per-nation check state (3.3) |
| `data/nations/verify/http_cache.json` | verifier | ETag and Last-Modified per URL for polite conditional requests |
| `data/nations/consent/` | editors | Written permissions (recorded pronunciation, any image). Empty at launch: text only |
| `data/nations/i18n/<lang>.json` | translators, later | Reviewed translations of fact text keyed by fact id (Spanish first) |
| `data/news/sources.json` | editors | Outlet registry with the outlet's own leadership statement and evidence (6.2) |

**Fact id** (stable, computed, never stored in the source file): `f_` plus the first 10 hex characters of
`sha1(nation_id + "|" + source.url + "|" + evidence)`. Rewording `text` keeps the id; changing the source or the
evidence makes a new fact that must pass verification before it shows.

**Id policy.** Ids come from the self-published name, transliterated to ASCII, plus a region or country hint where
needed (`dine-navajo-nation-us` style is fine only if the nation itself uses both names). Ids are permanent. If a
nation asks for an id change (for example because it contains an imposed name), the old id goes into
`nations/redirects.json` for links, and nowhere visible.

### 2.3 Tiers (computed at build, never typed by hand)

| Tier | Requirement | Where it can appear |
|---|---|---|
| **A, self-published** | `official_url` set, `name_source_url` on the nation's own domain, at least 2 publishable facts, at least 1 from the nation's own site or government | Herald, level cards, Daily Ring, hub, credits roll call |
| **B, sourced** | Name from a priority 1 or 2 source; at least 1 publishable fact | Herald, level cards, hub, credits roll call |
| **C, listed** | Name verified from a registry or representative body; no publishable fact yet | Hub (with "Facts in progress"), credits roll call. Not the herald, because a card with no fact reads as a label |
| **Hidden** | Override, takedown, or name check in review with no prior verified name | Nowhere |

"Publishable" means the fact's state is `ok`, `grace` or `human` (3.3).

### 2.4 Source priority (from the brief, enforced by a domain list)

1. The nation's own site, government or representative body.
2. National registries and statistics offices (US BIA in the Federal Register, Statistics Canada and CIRNAC, INPI and
   INEGI, IBGE and FUNAI, AIATSIS, Te Puni Kōkiri and Te Taura Whiri, the Sámi Parliaments, Taiwan's Council of
   Indigenous Peoples).
3. UN bodies (UNPFII, UNESCO, OHCHR), IWGIA *The Indigenous World*, Cultural Survival, Minority Rights Group, ACHPR.
4. Museums and universities (Smithsonian NMAI, national museums, peer-reviewed work).

`tools/nations_lint.py` keeps a domain-to-priority map. A fact from an unmapped domain fails lint until an editor
classifies the domain. Wikipedia is allowed only as a finding aid and is blocked as a citation.

### 2.5 Growing from about 350 to thousands

**The size of the task, cited.** The UN estimates "476 million indigenous peoples in the world living across 90
countries" who "represent 5,000 different cultures" (UN, International Day of the World's Indigenous Peoples,
background page). The World Bank gives 476.6 million, "6.2 percent of the global population", while the same UN page
says "less than 5 per cent". The hub shows one figure with its source and year and notes that sources differ.

**Denominators per country** go in `universe.json`, each with its own source. Verified this session:

| Country | Denominator | Source (fetched 2026-10-08) |
|---|---|---|
| United States | 575 federally recognized Tribal entities (Alaska Native entities listed separately) | Federal Register notice 2026-01899, 30 Jan 2026, via govinfo.gov |
| Canada | 3 constitutionally recognized groups; more than 1.8 million people, 5% of the population (2021) | CIRNAC "Indigenous peoples and communities" |

To confirm from the primary page before entering (seen only in secondary reports this session): Brazil, 391
peoples and 295 languages (IBGE Census 2022 release of 24 Oct 2025); Taiwan, 16 officially recognized peoples
(Council of Indigenous Peoples), with Pingpu peoples seeking recognition; Mexico, 68 peoples in INPI accounts versus
70 in INPI's updated national catalogue (resolve before use).

**A denominator is a planning number, not a definition of who counts.** State lists reflect state recognition.
Every coverage page says so, and state-recognized, unrecognized and self-identified nations are listed with the same
dignity as federally recognized ones.

**What one entry is.** List the entity that speaks for itself: a nation, tribe, iwi, First Nation, pueblo, people,
or representative body with its own governing voice. A people spread across many nations (for example one listed
per community by a registry) may have both a people-level entry and community entries, linked in `relations.json`.
Never merge two entries a nation would want kept apart, and never split one it presents as one.

**Authoring at scale.** `tools/nations_author.py <url>` fetches a page, shows its text, accepts a fact and an
evidence phrase, refuses the fact unless the phrase is found in the fetched text (same normalization as the
verifier), lints it, and appends it. Drafting help from an AI model is allowed only on top of a fetched page and is
labeled in the credits ("Compiled with AI assistance, checked against sources by a tool every week and by people").
Every new fact or nation arrives as a pull request.

**Throughput math.** 5,000 entries at 3 facts each is 15,000 facts and roughly 8,000 unique source URLs (many facts
share a page). Section 3.5 sizes the verifier for that.

### 2.6 Coverage tracking

`nations/api/coverage.json` (built) and the page `/nations/coverage` report, per region and per country: listed,
tier A, tier B, tier C, with pronunciation, facts stale or in review, last full verification date, and the
denominator with its source. Thin regions are shown first, as the work queue, not hidden.

A region joins the herald's round robin only when it has at least 8 publishable nations; until then it rides with
the region named in its `merge_into` (for example a small sub-region of Africa merges into its neighbor), so a short
list does not repeat the same three names to every visitor.

**Proposed region keys** (the build accepts any key declared in `regions.json`; align with keys already used by the
regional compilers, for example `andes`): `north-america`, `mexico-central-america`, `caribbean`, `andes`,
`amazonia`, `southern-cone`, `arctic`, `sapmi-northern-europe`, `russia-central-asia`, `east-asia`, `south-asia`,
`southeast-asia`, `pacific`, `australia`, `aotearoa`, `africa-north-sahel`, `africa-west-central`, `africa-east`,
`africa-southern`. Display names are plain geography ("North America"), never a name from one people applied to all.

Cross-border peoples (Sámi, Inuit, Haudenosaunee, Tohono O'odham, Kumeyaay, Aymara, Mapuche, Wayuu, Maasai and many
more) use the `countries` array and appear under every listed country in the hub.

---

## 3. Constant verification

### 3.1 What runs

`tools/nations_verify.py` (Python 3.10, stdlib plus pinned `pypdf` for PDF sources):

1. Load all region files and sidecars. Group facts by `source.url` so each page is fetched once per run.
2. Fetch politely (3.2). Extract visible text (HTML: drop `script`, `style`, `noscript`, comments; PDF: pypdf text,
   then join words hyphenated across line breaks, as in the UNDRIP PDF where "genera -" and "tions" are split).
3. Normalize page text and evidence the same way (3.4) and test containment.
4. Check names: `name_source_url` must still contain `name` after normalization.
5. Check pronunciation: `pronounce.source_url` must still contain `pronounce.text` after normalization.
6. Check `official_url` liveness (status only; no content claim).
7. Write `state.json`, update `accessed` to the run date for every fact that passed (the only field the tool ever
   edits in a source file, written back with stable key order, 2-space indent, `ensure_ascii=False`).
8. Write `verify/report.md` (counts, new failures, recoveries, unreachable hosts) for the pull request body.

### 3.2 Polite fetching

- Honest user agent: `ZOTHEOS-NationsVerifier/1.0 (+https://zotheos.org/nations/about)` and a `From:` header with a
  project role address (to be created, for example `nations@` on the zotheos.org domain). No browser spoofing and no
  stealth or fingerprint-resistant fetchers: if a site blocks bots, that is its choice, and the fact moves to the
  human lane (3.3).
- Obey `robots.txt` (RFC 9309, "Crawlers MUST try to parse each line of the robots.txt file"). Cache per run.
- One request at a time per host, at least 3 seconds apart; up to 8 hosts in parallel; honor `Retry-After`; at
  most 2 retries; 20 s timeout; 8 MB cap; conditional GET with stored ETag and Last-Modified. A 304 counts as a pass
  for every fact on that page (the page did not change since it passed).
- Redirects: same registrable domain is followed; a redirect to another site is not followed and puts the fact in
  `review` (a moved page is a human decision).

### 3.3 States

| State | Meaning | Shown? | Next step |
|---|---|---|---|
| `ok` | Evidence found this run (or 304 after a pass) | Yes, "Checked <accessed>" | none |
| `grace` | Transient failure (timeout, 5xx, 429, DNS) and last pass under 14 days ago | Yes, unchanged | Retry next run; becomes `stale` after 14 days |
| `stale` | Evidence missing, 404 or 410, grace expired, robots disallow | **No** | Editor finds the new phrase or a new source; restore by PR |
| `review` | Cross-site redirect, name or pronunciation check failed, near-match found | **No** for facts and pronunciation; see name rule below | Human decision |
| `human` | Source blocks automated fetching; a person checked the phrase in a browser on a date | Yes, "Checked by a person on <date>" | Expires after 90 days |
| `removed` | Takedown or editor removal | Never | Id is blocked from re-entry by lint |

**Name rule.** A failed name check never hides a nation (hiding a people because a web page changed would be a kind
of erasure). The last verified name stays, the nation goes to `review`, and an editor checks whether the nation
renamed itself. A nation's own request always overrides.

**Near-match helper.** When exact containment fails, the tool searches for the best 4 to 12 word window with high
token overlap and puts it in the report as a suggested replacement phrase. A suggestion never restores a fact by
itself.

### 3.4 Normalization (both sides, identical)

```
html.unescape -> NFKC
remove U+00AD, U+200B..U+200D, U+FEFF
map for matching only: U+2018 U+2019 U+201B U+02BB U+02BC U+2032 -> '   and   U+201C U+201D U+201E U+2033 -> "
map U+2010..U+2015 and U+2212 -> -
PDF only: join "word -<newline>word" and "word-<newline>word" hyphenation
collapse whitespace, trim, casefold
pass 1: exact substring        -> ok
pass 2: same after NFKD with combining marks stripped -> ok, with note "diacritics differ on page"
```

The mappings exist only inside the matcher. Displayed text is never altered (an okina, U+02BB, stays an okina).

### 3.5 The scheduled job

`.github/workflows/nations-refresh.yml` on the site repo:

```yaml
name: nations-refresh
on:
  schedule:
    - cron: "17 9 * * 1"     # Mondays 09:17 UTC, off the top of the hour
  workflow_dispatch: {}
permissions:
  contents: write
  pull-requests: write
concurrency: { group: nations-refresh, cancel-in-progress: false }
jobs:
  refresh:
    runs-on: ubuntu-latest
    timeout-minutes: 240
    steps:
      - uses: actions/checkout@<pinned-sha>
      - uses: actions/setup-python@<pinned-sha>
        with: { python-version: "3.10" }
      - run: pip install --require-hashes -r tools/requirements-nations.txt
      - run: python tools/nations_verify.py --run-date "$(date -u +%F)"
      - run: python tools/nations_lint.py && python tools/nations_build.py
      - run: python tools/nations_publish_lanes.py   # splits changes into the two lanes below
```

**Two lanes.**

- **Lane 1, direct commit to the default branch:** changes that only reduce what is shown or are mechanical:
  facts going `stale` or `review`, `accessed` dates, `state.json`, rebuilt outputs. Vercel's Git integration deploys
  the push. This is how "hide until re-verified" takes effect the same day without waiting for anyone.
- **Lane 2, pull request:** anything that adds or restores visible content: recovered facts, suggested phrases, name
  changes, new nations, new news sources. Vercel builds a preview for review.

**Known GitHub behaviors to design around** (from GitHub's documentation, fetched 2026-10-08):

- Scheduled runs "can be delayed during periods of high loads"; queued jobs may be dropped. Hence the odd minute,
  and the site shows the real last-run date rather than promising a day.
- "In a public repository, scheduled workflows are automatically disabled when no repository activity has occurred
  in 60 days." The weekly lane 1 commit keeps the repo active, and `nations/api/status.json` carries the last run
  date: the hub shows "Verification overdue" in plain text if it is older than 14 days.
- "Scheduled workflows will only run on the default branch."
- "events triggered by the `GITHUB_TOKEN` will not create a new workflow run". This does not affect the Vercel
  deploy (that comes from Vercel's own Git integration), but any follow-up workflow must be called directly, not
  chained on the bot's push. Confirm on the first live run that the lane 1 push produces a production deploy; if it
  does not, add a Vercel Deploy Hook as a repository secret and call it as the last step.

**Scale.** Up to about 3,000 unique URLs, every source is checked every week. Beyond that, sources are split into 4
hash buckets checked one per week, plus every failing or `grace` source every week, so each source is checked at
least every 28 days and the hub's "Checked" date stays truthful.

### 3.6 The site itself makes no third-party requests

- Hub and game load only same-origin files: `nations/api/*.json`, fonts from `static/fonts/`, and a self-hosted SVG
  map. No external images (no outlet logos, no favicons, no nation seals), no embeds, no analytics, no map tiles.
- New CSP for `/nations` and `/nations/(.*)` in `vercel.json`:
  `default-src 'none'; base-uri 'none'; object-src 'none'; script-src 'self'; script-src-attr 'none';
  style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self'; form-action 'none';
  frame-src 'none'; worker-src 'none'; frame-ancestors 'none'`.
- The game's host page (`/`, `/index`, `/index.html`) today has `connect-src https://formspree.io`; add `'self'` so
  the game can read the herald JSON with a same-origin `XMLHttpRequest` (the game is ES5, so XHR, not `fetch`).
- Source links and headlines are plain anchors with `rel="noopener noreferrer"`; the site already sends
  `Referrer-Policy: no-referrer`. A click is the reader's own navigation, never a background request.
- JSON caching: shard files are content-hashed (`<region>-<n>.<hash8>.json`) and served `immutable`; the small index
  files get `max-age=3600`.
- **Offline:** the game build embeds a verified starter pack of about 16 nations (at least one per merged region) so
  the herald works with no network. The build fails if any starter fact is not publishable, and refills the pack from
  the same region automatically.

---

## 4. Renewal: every visit shows someone new

### 4.1 Two layers

- **Daily Ring (shared).** At build time nothing is fixed; in the browser, `seed = fnv1a32(localDate + "|" + dataVersion)`
  picks one tier A or B nation per merged region (about 12 to 16 names). Everyone sees the same ring that day, which
  gives the hub a "Today" row and the credits a shared roll call.
- **Personal Walk (per device).** Each device gets a random 32-bit key once (`crypto.getRandomValues`, stored in
  `localStorage`) and a cursor `c`. Regions take turns in a seeded order; within a region, a keyed permutation of
  `0..n-1` gives the next nation. The cursor only moves forward, so a device sees every nation in a region before any
  repeat.

The herald first shows any Daily Ring nation this device has not seen today, then continues the Personal Walk.

### 4.2 Algorithm (ES5, fits the game's existing `mulberry32` and seed code)

```
R      = list of herald regions (after merge), in seeded order for this device key
r      = R[c % R.length]
k      = floor(c / R.length)                 // how many full turns this region has had
n      = r.count                              // publishable nations in region r
i      = feistelPermute(k % n, n, key ^ hash(r.key) ^ dataMajor)   // 4-round Feistel, cycle-walk to < n
shard  = floor(i / r.shardSize)               // fetch only that shard
fact   = facts[(floor(k / n) + hash(id)) % facts.length]           // next full cycle shows the next fact
c      = c + 1                                // saved after the card is shown
```

- `dataMajor` changes only when an editor wants a full reshuffle; adding nations changes `n`, which can cause a few
  repeats and is acceptable.
- Fact choice prefers a `today` or `achievement` fact on the Daily Ring; `as_of` older than 3 years on a `today` or
  `population` fact puts it in the refresh queue (still shown, with "As of 2021.").
- **Storage can fail** (private windows, blocked storage). Every read and write is wrapped in `try/catch`; without
  storage the device key comes from `crypto.getRandomValues` per session and the walk starts at a random cursor. The
  key and cursor never leave the device and are never sent anywhere.

### 4.3 What files the browser reads

| File | Size target | Contents |
|---|---|---|
| `nations/api/herald-index.json` | under 4 KB | data version, regions with `count`, `shardSize`, hashed shard names, merge map |
| `nations/api/herald/<region>-<n>.<hash>.json` | about 100 nations, under 20 KB gzipped | per nation: `id`, `name`, up to 2 `also`, verified `pronounce` text and publisher, `lands`, publishable facts as `{t, k, y, p, u, d}` (text, kind, as_of, publisher, url, checked date) |
| `nations/api/search.json` | lazy, on first focus of search | id, name, also, lands, countries, region, tier |
| `nations/api/news.json` | under 40 KB | headlines (section 6) |
| `nations/api/coverage.json`, `status.json` | small | coverage table, last verification and news run dates |

One herald card costs at most one shard request, and the shard is cached immutably.

---

## 5. Properly announcing a nation

### 5.1 The card

```
NORTH AMERICA                                  region, small caps label, plain geography

<Name as the nation publishes it>              display serif, largest text on the card
Also known as <exonym>                         smaller, only if neutral and not rejected
Say it: <pronunciation text>                   only if sourced and verified; credit below
Lands: <present-day places, countries>
<One fact in plain words.> As of 2024.
Source: <publisher>   Pronunciation: <publisher>
```

- Monochrome, white on black, matching the game. Opacity fades only: no blur, no scale, no glow, no dimming
  gradients. Hover states stay neutral (ZOTHEOS color restraint).
- The card is a DOM element in the game overlay, not drawn on the canvas.
- The name element carries `lang` only when a language tag is sourced (a future optional field in a sidecar, for
  example `mi`, `chr`, `iu`). This lets a person's own screen reader voice it as they have chosen; we still never
  synthesize speech.
- In the game the source shows as publisher text. In the hub it is a link.

### 5.2 Timing

| Surface | Sequence | Dwell |
|---|---|---|
| Title herald | name fades in 700 ms (ease-out); "also" and lands start at 450 ms, 500 ms; fact starts at 900 ms, 500 ms; all fade out together in 450 ms; 350 ms of black between cards | `clamp(3500 ms + 55 ms per fact character, 6 s, 12 s)` |
| Level card (between levels) | same fade-in; appears on level **start** or **clear** only | at least 3.2 s; skippable with Strike or Enter after 1.2 s |
| Credits roll call | pages of 6 names, each page fades in 500 ms | 2.5 s per page, paused by any input |

- Brightness never changes more than twice per second (the game's existing rule).
- **WCAG 2.2.2 (Pause, Stop, Hide):** the title herald auto-advances, lasts more than 5 s and sits beside other
  content, so it has a visible **Pause** and **Next** control, pauses on hover and focus, and pauses when the tab is
  hidden.
- **Reduced motion:** no fades (instant swaps) and **no auto-advance**; the person presses Next.

### 5.3 Screen readers

- One visually hidden `aria-live="polite"` region, present and empty at load (MDN: the attribute is set on an empty
  element that is then updated).
- It announces a card only on events: the first herald on the title screen, a press of Next, a level card. Automatic
  rotations update the visible card without announcing, so a screen reader user is not interrupted every 9 seconds.
- Announcement text: "Nation: <name>. Lands: <lands>. <fact>". No "also" list, no pronunciation text read aloud.

### 5.4 Fonts and glyphs (a hard gate)

The site's fonts cover Latin and Latin Extended only; `docs/FONTS.md` notes no glyph for U+02BC in Instrument Serif
or DM Sans and no saltillo anywhere. Nation names need far more: the okina (U+02BB), glottal stop letters (U+0294,
U+0295), IPA and Spacing Modifier letters used in Salish and other orthographies, combining marks (U+0313, U+0331 and
more), Unified Canadian Aboriginal Syllabics, the Cherokee syllabary, Tifinagh, Cyrillic.

- Names render in a dedicated stack: brand serif first, then self-hosted OFL Noto subsets, generated at build with
  `fonttools` from the exact code points used in published names.
- `tools/nations_lint.py` fails the build if any published name, "also" entry or pronunciation has a code point that
  no face in the stack covers.
- **Never substitute a character in a nation's name** to fit a font. The FONTS.md advice to use U+2019 for a Nahuatl
  glottal stop applies to our own Nahuatl terms, never to a nation's published name.

### 5.5 Pronunciation policy

- Show only when `pronounce` is non-null **and** its text is still found on its source page (3.1, step 5).
- Credit the source ("Pronunciation: <publisher>"). Prefer the nation's own site or language program.
- **No speech synthesis anywhere.** The build fails if `speechSynthesis` or `SpeechSynthesisUtterance` appears in
  the game or hub code. A wrong pronunciation spoken by a machine is a disrespect, so we would rather show nothing.
- **Future recorded audio:** only a nation's own published recording, or a recording made with the nation's written
  permission, stored in `data/nations/consent/`, self-hosted, credited as the nation wishes, played only on a tap
  (never autoplay), and removed on request.

---

## 6. News shelf

### 6.1 Shape and rules

- `tools/news_fetch.py` runs daily in `.github/workflows/news-refresh.yml` (`cron: "41 13 * * *"`, lane 1 commit).
- Keep only **title, outlet, date, link**. Discard descriptions, full content (several feeds carry full text in
  `content:encoded`), images, and authors.
- Sanitize: strip tags, decode entities, cap at 160 characters with "...", drop items dated more than 1 day in the
  future, strip tracking parameters, keep only `https` links whose host is on that outlet's own domain allowlist (a
  hijacked feed cannot point readers elsewhere), dedupe by canonical link.
- Punctuation normalization for the site's no-dash rule: U+2014 and U+2013 in a headline become a spaced hyphen.
  Words are never changed.
- Window: last 30 days, at most 10 items per outlet, interleaved round robin by region so one outlet or country does
  not fill the shelf. Headline language comes from the feed's `<language>` element and sets `lang` on the item.
- The shelf shows "Headlines gathered <date, time UTC>" from `status.json`. It never says "live".
- Headlines never become herald facts automatically. An editor may turn a story into a fact only through the normal
  source rules and evidence check.
- Tagging a headline with a nation (to show "In the news" on a nation page) is a later phase, by exact match on the
  self-published name plus country check, and reviewed by a person, because names collide with place names.

### 6.2 Inclusion test

An outlet is included when its own pages state Indigenous ownership, governance or leadership; that statement is
stored in `data/news/sources.json` with an evidence phrase and re-checked by the verifier like a fact. Advocacy
organizations that are Indigenous-led are labeled "Indigenous-led organization", not "newsroom".

### 6.3 Feeds checked on 2026-10-08

**Pass (feed returns current items and leadership is stated on the outlet's own page):**

| Outlet | Feed URL | Leadership, from its own page |
|---|---|---|
| ICT | `https://ictnews.org/feed` | About page: "Native-led"; a division of IndiJ Public Media. Stories free to republish under CC BY-NC-ND 4.0, so headline links are well within its terms |
| Native News Online | `https://nativenewsonline.net/rss` | About page: publisher Levi Rickert, Prairie Band Potawatomi citizen, is "the controlling shareholder" of Indian Country Media LLC |
| IndigiNews | `https://indiginews.com/feed` | "an independent, Indigenous-run newsroom", owned by tâpwêwin media |
| Cultural Survival | `https://www.culturalsurvival.org/rss.xml` | "an Indigenous-led NGO"; staff and board majority Indigenous. Label as organization |
| Koori Mail | `https://koorimail.com/feed/` | "100% Aboriginal owned", owned by five Bundjalung Aboriginal community organisations |
| APIB (Brazil) | `https://apiboficial.org/feed/` | National Indigenous representative organization (Articulação dos Povos Indígenas do Brasil); Portuguese. Label as organization |

**Feed passes, leadership statement still to capture from the outlet's own page** (their about pages returned 403
or 404 to the fetcher; add the evidence before launch):

| Outlet | Feed URL | Note |
|---|---|---|
| APTN News | `https://www.aptnnews.ca/feed/` | About page 403 to automated fetch; use the human lane |
| Te Ao Māori News | `https://www.teaonews.co.nz/arc/outboundfeeds/rss/?outputType=xml` | News service of Whakaata Māori; capture from its own page |
| Waatea News | `https://waateanews.com/feed/` | Channel title "Waatea News: Māori Radio Station"; many headlines in te reo Māori (set `lang="mi"`) |

**Hold (do not ship until fixed):**

| Outlet | Problem found |
|---|---|
| NITV (SBS) | Only a podcast feed found (`https://feeds.sbs.com.au/nitv-news`), newest item 7 Aug 2026; NITV says its news is delivered by "a team of Indigenous journalists". Find an article feed |
| Underscore Native News | Feed works; its own pages describe Indigenous-centered coverage but did not state Indigenous leadership |
| Indigenous Rising | Feed returned "Service unavailable" |
| Servindi (Peru) | Feed lists 2017 and 2018 items first; stale or unordered |
| Windspeaker / AMMSA | `rss.xml` newest item from 2014 |
| NRK Sápmi | No RSS address found |
| AIPP, IPRI, Mídia Índia, Cherokee Phoenix | 403, 404 or 429 to the fetcher; retry and verify by hand |

**Gaps to fill with priority:** Africa, Asia, the Arctic beyond Canada, Spanish-language Latin America, Russia and
Central Asia. The shelf shows its outlet list and says plainly which regions have no headline source yet.

**Excluded by rule (not Indigenous-led):** Amazon Watch, Survival International, Mongabay. IWGIA stays a fact
source (priority 3) but is not on the news shelf.

**Courtesy:** write to each outlet before launch to say we link headlines, ask whether they object, and record the
answer in `sources.json`. An outlet that asks to be removed is removed the same day.

---

## 7. Learning hub (`/nations`)

### 7.1 Pages

| Path | What it is |
|---|---|
| `/nations` | Today (Daily Ring), search, region list and map, news shelf, last verification date |
| `/nations/<id>` | One nation: everything verified about it, fully rendered at build (works with JavaScript off) |
| `/nations/region/<key>` | All entries in a region, alphabetical by self-published name |
| `/nations/coverage` | Honest coverage table (2.6) |
| `/nations/sources` | Every publisher and URL cited, grouped by priority, with checked dates |
| `/nations/changes` | Public log of corrections and removals (no personal data; takedowns appear only as "Removed at a nation's request", without the name) |
| `/nations/about` | Method, verifier user agent, source rules, how the rotation works, AI assistance disclosure |
| `/nations/for-nations` | How a nation corrects, removes, adds itself, or sends an official pronunciation |

### 7.2 Nation page layout

1. Name (large), "also" (small), sourced pronunciation with credit.
2. **"Visit the nation's own site"** as the first link when `official_url` exists.
3. Lands and countries.
4. Every publishable fact, newest `as_of` first, each with kind, "As of" year, publisher link, "Checked <date>"
   or "Checked by a person on <date>".
5. A count line when facts are being re-checked ("1 fact is being re-checked."), never their content.
6. "Suggest a correction" (7.4).
7. Credit line: "Names, lands and facts are written from the sources shown. Corrections from nations come first."

### 7.3 Search and map

- Search is client-side over `search.json`, loaded on first focus. Matching is diacritic-insensitive and quote
  insensitive for search only (Maori finds Māori, Dine finds Diné), while results always display the exact name.
- The map is a self-hosted SVG built from Natural Earth admin-0 countries (public domain: "No permission is needed
  to use Natural Earth"; credited anyway). Black ocean, 1 px white country outlines, the selected region filled
  solid white with black labels. No gradients, no glows, no dimming of other regions; the selection is shown by fill
  versus outline.
- The region list is the primary control (real buttons, keyboard reachable). The map mirrors it and is optional.
- **No Indigenous territory polygons.** Native Land Digital says "NLD maps are not official sources" and that it
  "does not claim to define territories"; drawing borders could misstate land claims. Nations are found by country
  and region, and by the `lands` text each entry gives.

### 7.4 Corrections and suggestions (no third-party request)

- Default: a `mailto:` link to a project role address, prefilled subject `Nations correction: <id> <fact id>` and a
  short body template. The reader's own mail client sends it.
- Second option: a link to a GitHub issue form (public; the page says so).
- The landing page already posts to Formspree. The hub does not use it by default; if a form is ever added it must
  submit only on an explicit press, disclose the processor, and stay out of the nations pages' CSP until then.
- Nations get a separate priority address on `/nations/for-nations`.

### 7.5 Learning without scoring people

The hub teaches by reading, sources and "read more from the nation" links. No quizzes about peoples, no points or
streaks for knowing facts about a culture. The game keeps its scores for the ballgame; nations stay outside scoring.

---

## 8. Governance

### 8.1 Indigenous advisory circle (future, planned now)

- 5 to 7 paid seats across regions (North America; Mexico and Central America; South America; the Pacific,
  Aotearoa and Australia; the Arctic and Sápmi; Africa; Asia). Paid, never volunteer labor.
- Powers: approve the respect and source rules; veto any content category; review new region launches; review the
  game's cultural representation, including the redesigned antagonist (8.5); decide on recorded audio and any
  future open data license.
- Until the circle exists, the interim rules here apply, and the hub says the circle is not yet formed.

### 8.2 Corrections within 72 hours

| Request | First action | Deadline |
|---|---|---|
| From a nation (any content about itself) | Hide the item at once with an `overrides.json` entry and redeploy | Done within 72 h, target 24 h |
| Harm risk from anyone (wrong name, a deceased person, sacred content, an offensive term, a safety risk) | Hide at once | Decision within 72 h |
| Factual correction from a reader | Acknowledge | Fix or reasoned reply within 72 h |
| Suggestion (new nation, new fact) | Acknowledge | Queued; normal PR review |

Every action lands in `/nations/changes` and in the repo history.

### 8.3 Takedown path

Any nation, through its government, council or an authorized office, can ask for removal of any fact, the
pronunciation, an "also" name, its news tagging, or its whole entry, with no reason required. We comply. If authority
is unclear, we hide while we confirm. A removed nation leaves the herald, hub, credits and news tagging; its id is
blocked so lint stops it from being re-added by accident; it is not listed by name anywhere, including the change log.

### 8.4 Credit lines

- **Each card:** "Source: <publisher>" and, if shown, "Pronunciation: <publisher>".
- **Game credits:** "Nations: names, lands and facts as each nation publishes them, and from the public sources
  named on every card. Full sources at zotheos.org/nations/sources." Then publishers in priority order (nations'
  own sites first), then "Global figures: United Nations, World Bank", "Map: Natural Earth (public domain)",
  "Compiled with AI assistance and checked against sources every week."
- **News shelf:** the list of outlets by name.

### 8.5 Boundary with the game

The game is being redesigned (antagonist becoming a mask, maze play closer to a chase-and-escape design). Rules that
hold whatever the redesign becomes:

- No nation card on fail, caught or game-over screens, or while the antagonist is on screen.
- The antagonist never carries a nation's name, a people's name or a real deity's name, and its mask design is put to
  the advisory circle (masks in Mesoamerican traditions can be sacred objects tied to specific beings).
- Level names and challenges stay about the ballgame and the lake city, never about a nation.

---

## 9. Risks, and what must never be done

### 9.1 Never

- Attach a nation to a villain, enemy, collectible, power-up, reward, level name, difficulty or score.
- Synthesize speech for a name, or show an unsourced pronunciation.
- Cite Wikipedia, or publish a fact whose evidence was not found in a page fetched by the tool or checked by a person.
- Draw Indigenous territorial boundaries.
- Use "extinct", "vanished", "last of", "disappeared", "primitive", "savage", "noble savage", "spirit animal",
  "legend says" about living peoples; talk about blood quantum; romanticize.
- Name or describe deceased persons for Aboriginal and Torres Strait Islander peoples (AIATSIS sensitivity notices
  warn that names and images of deceased people can cause distress and conflict with cultural prohibitions; exact
  wording to confirm, see section 12). Safer still: no named individuals in facts anywhere at launch.
- Publish sacred, ceremonial or restricted knowledge, or use a sacred calendar or symbol as a game mechanic.
- List or locate peoples in voluntary isolation. Mention them only at the level a national authority publishes, or
  leave them out.
- State contested recognition or land disputes as settled; use neutral wording with a strong source, or leave it out.
- Rank nations ("largest", "most powerful"); give population only as a neutral number with `as_of`.
- Use a nation's logo, seal or flag (sovereign symbols, often trademarks) without written permission. Text only.
- Spoof a browser or use stealth fetchers to get past a site's bot rules.
- Auto-restore hidden content without a person's review.
- Make any third-party request from the site, add analytics, or load outlet images.
- Swap characters in a name to suit a font.
- Offer the compiled data for bulk reuse or model training without the advisory circle's decision.

### 9.2 Lint gates (`tools/nations_lint.py`, run in CI and before every build)

Schema; unique and unblocked ids; ISO codes; https; domain priority map; Wikipedia block; fact length; no U+2014 or
U+2013 in any visible string; evidence word count; `as_of` heuristic; banned-term list (9.1); a flag for manual
review on any fact for `AU` that contains a capitalized personal-name pattern; glyph coverage (5.4); no
`speechSynthesis`; starter pack fully publishable; every news item host on its outlet's allowlist.

### 9.3 Risks and mitigations

| Risk | Mitigation |
|---|---|
| Source pages move or change wording | Weekly verifier, automatic hiding, near-match suggestions, PR to restore |
| Official sites block automated fetches (this session saw 403s from OHCHR, APTN, UN DESA, AIATSIS, ILO) | Human lane with dated, expiring `human` state, labeled honestly |
| JavaScript-rendered pages with no static text | Prefer a static page or PDF from the same body; otherwise human lane. No headless stealth |
| State recognition bias in denominators | Self-identification rule; coverage pages state the bias |
| Uneven coverage (lists far longer in some countries) | Region round robin, `merge_into`, thin regions first in the work queue |
| Name collisions and similar names | Region hint in ids, `official_url` uniqueness check, country check |
| Scheduled workflow disabled or delayed | Weekly commits keep activity; overdue banner from `status.json`; manual dispatch |
| Review load at thousands of entries (about 15,000 facts) | Rolling buckets, PR batching per region, advisory circle and paid reviewers as the project grows |
| Political sensitivity where states reject the term "Indigenous" | Self-identification with priority 3 sources (IWGIA, MRG), neutral wording, advisory review |
| Safety of activists and communities | No named individuals at launch; no locations finer than the nation's own published `lands` |
| A feed is hijacked or injects links | Host allowlist per outlet; titles stripped of markup; no images |
| Translation drift | Translations keyed by fact id, reviewed, hidden when the source fact is hidden |

---

## 10. Build and integration

### 10.1 Layout in `C:\ZOTHEOS-Web`

```
data/nations/regions/<region>.json        contract files (one per region)
data/nations/{regions,universe,relations,overrides}.json
data/nations/verify/{state.json,http_cache.json,report.md}
data/nations/consent/   data/nations/i18n/
data/news/sources.json
tools/nations_{lint,verify,build,author,publish_lanes}.py   tools/news_fetch.py
tools/requirements-nations.txt           pinned with hashes (pypdf, fonttools)
nations/                                 built site output (pages, app.js, api/, fonts subset, map.svg)
.github/workflows/{nations-refresh,news-refresh}.yml
```

`data/` is excluded from the Vercel deploy with `.vercelignore`; only `nations/` ships.

### 10.2 Game hook (ES5)

A small `ZTH_NATIONS` module inside the game file:

- `ZTH_NATIONS.next(function (card) { ... })` returns the next card from the Daily Ring or Personal Walk, using the
  starter pack if the XHR fails.
- `ZTH_NATIONS.mount(el)` renders a card into a DOM element in the overlay with the timings in 5.2.
- `ZTH_NATIONS.pause()`, `.resume()`, `.skip()` wire to the overlay's pause, tab-hide and keys.
- All strings in the game's `TEXT` object; region labels from `herald-index.json`.

### 10.3 Phases

| Phase | Ships | Done when |
|---|---|---|
| 0 | Contract files from the regional compilers, `regions.json`, lint | All files lint clean; glyph gate passes |
| 1 | Verifier, refresh workflow, lane split, herald in the game with starter pack | First scheduled run deploys; a forced evidence break hides a fact within one run |
| 2 | `/nations` hub, search, map, coverage, sources, about, for-nations, corrections | Pages work with JavaScript off; CSP has no third-party origin |
| 3 | News shelf with the passing feeds; outlet letters sent | Daily run green for 14 days; every outlet has an evidence-backed leadership statement |
| 4 | Advisory circle, Spanish UI and reviewed translations, recorded pronunciations with consent | Circle seated and paid; consent records in place |

### 10.4 Acceptance checks

- Change one evidence phrase on a local mirror: the next verify run marks the fact `stale`, the build drops it, the
  hub shows "1 fact is being re-checked."
- Block storage in the browser: the herald still works and still varies.
- Two devices on the same day share the Daily Ring and differ after it.
- 200 consecutive Next presses on one device show no repeat inside a region until the region is exhausted.
- Network panel on `/nations` and in the game shows only same-origin requests.
- Reduced motion: no fades, no auto-advance. Screen reader: one announcement per event.
- Search the built output for U+2014 and U+2013: zero.

---

## 11. Open questions for David

1. A role address for corrections and nations (for example on the zotheos.org domain), and whether the site repo is
   public (affects the 60-day rule and the public issue path).
2. Whether lane 1 direct commits to the default branch are acceptable, or every change should wait for a PR (safer
   for content, slower to hide failing facts).
3. Which outlets to write to first, and who signs the letters.
4. Budget and timing for the paid advisory circle.

---

## 12. Sources consulted (all fetched 2026-10-08)

Verified and quoted above:

- United Nations, International Day of the World's Indigenous Peoples, background:
  https://www.un.org/en/observances/indigenous-day/background (476 million, 90 countries, 5,000 cultures, less than
  5 per cent).
- World Bank, Indigenous Peoples: https://www.worldbank.org/en/topic/indigenouspeoples (476.6 million, 6.2 percent).
- United Nations Declaration on the Rights of Indigenous Peoples, UN DESA PDF:
  https://www.un.org/development/desa/indigenouspeoples/wp-content/uploads/sites/19/2018/11/UNDRIP_E_web.pdf
  (Articles 13, 31, 33; text extracted locally with pypdf).
- Federal Register, Indian Entities Recognized by and Eligible To Receive Services From the United States Bureau of
  Indian Affairs, 30 Jan 2026: https://www.govinfo.gov/content/pkg/FR-2026-01-30/html/2026-01899.htm (575 entities).
- CIRNAC, Indigenous peoples and communities:
  https://www.rcaanc-cirnac.gc.ca/eng/1100100013785/1529102490303 (3 groups, more than 1.8 million, 5%).
- GitHub Docs, Events that trigger workflows (schedule notes):
  https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows
- GitHub Docs, Triggering a workflow (GITHUB_TOKEN note):
  https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/triggering-a-workflow
- W3C, Understanding SC 2.2.2 Pause, Stop, Hide: https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html
- MDN, aria-live: https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-live
- IETF RFC 9309, Robots Exclusion Protocol: https://www.rfc-editor.org/rfc/rfc9309.html
- Natural Earth, Terms of use: https://www.naturalearthdata.com/about/terms-of-use/
- Native Land Digital, About: https://native-land.ca/about/
- Local Contexts, About the Labels: https://localcontexts.org/labels/about-the-labels/ (TK and BC Labels are applied
  by communities; a later option for crediting community protocols)
- GIDA, CARE Principles: https://www.gida-global.org/careprinciples ("people and purpose-oriented", complementing
  FAIR; the four principle names come from GIDA's one-pager, not fetched this session)
- Outlet pages: https://ictnews.org/about-us/ , https://nativenewsonline.net/about-us ,
  https://indiginews.com/?p=5415 , https://www.culturalsurvival.org/about ,
  https://koorimail.com/about-koori-mail/ , https://underscore.news/about-us/ , https://www.sbs.com.au/nitv/
- Feeds as listed in 6.3.

Seen only in search summaries, to confirm on the primary page before use: IBGE Census 2022 peoples and languages;
Taiwan Council of Indigenous Peoples recognized peoples; INPI peoples count (68 versus 70); AIATSIS cultural
sensitivity wording (page returned 403); ownership of Waatea News; Te Ao Māori News governance; ILO Convention 169
Article 1(2) (page returned 403).
