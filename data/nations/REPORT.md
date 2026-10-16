# Nations assembly, round 2 (2026-10-10)

Assembler report for `nations.json` / `nations.min.json`. Round 2 folds the four gap compilations
(`gap-africa`, `gap-caribbean-guianas`, `gap-pacific`, `gap-south-asia`) into the round-1 set.
Every decision below is also machine-readable in `tools/merge_overrides.json` (with its reason) and
`tools/merge_log.json` (every drop, merge, rename and field override).

## 1. Totals

| | Round 1 | Round 2 | Delta |
|---|---|---|---|
| Nations | 378 | **450** | +72 |
| Facts | 1026 | **1260** | +234 (206 on new nations, 28 added to 12 existing nations) |
| Regions | 14 | **15** | +1 (`caribbean-guianas`) |
| Countries (ISO codes) covered | | **99** | |
| Facts with status `verified` | | 1260 (100%) | |
| Nations with an official site | | 190 | |
| Nations with a sourced pronunciation | | 11 | |

Files: `nations.json` 1,134,229 bytes (2-space indent), `nations.min.json` 843,360 bytes (identical data,
checked by `validate.py`). `version` "1", `generated` "2026-10-08", `count` 450, `facts` 1260.

### Nations and facts by region

| Region key | Nations | Facts | Round 2 change |
|---|---|---|---|
| africa | 41 | 124 | +18 nations, +12 facts on 6 existing (from gap-africa) |
| alaska-hawaii-pacific-us | 21 | 58 | |
| amazon-lowland-sa | 29 | 79 | |
| andes | 22 | 56 | |
| arctic-europe-russia | 20 | 58 | |
| asia | 53 | 141 | +17 nations, +6 facts on 2 existing (from gap-south-asia) |
| canada | 35 | 105 | |
| caribbean-guianas | 16 | 48 | new region (from gap-caribbean-guianas) |
| central-america-caribbean | 26 | 68 | +2 nations (Xinka, Ch'orti', moved from the gap file by geography) |
| mx-central-south | 26 | 69 | |
| mx-north-us-southwest | 26 | 75 | |
| oceania | 46 | 131 | +19 nations, +10 facts on 4 existing (from gap-pacific) |
| us-east-southeast | 25 | 72 | |
| us-plains-midwest | 35 | 97 | |
| us-west-pacific | 29 | 79 | |

Fact kinds: language 268, land 201, governance 200, today 180, culture 178, population 106, history 72,
achievement 55.

### Region keys

The gap files carried workflow labels as region keys. ARCHITECTURE 2.6 wants plain geography in the
published data, so `merge.py` now takes a `region_map` and refuses any `gap-*` key that reaches the output:
`gap-africa` to `africa`, `gap-pacific` to `oceania`, `gap-south-asia` to `asia`,
`gap-caribbean-guianas` to `caribbean-guianas` (Caribbean islands, Trinidad, the Guianas and the Orinoco
peoples). Two nations in that file are Central American and were moved by a per-nation `region` override:
`xinka-southeast-guatemala` and `chorti-maya-guatemala-honduras` to `central-america-caribbean`.
The output contains the string `gap-` zero times.

## 2. Round-2 inputs and what survived

| Gap file | Nations in | Facts in | Verifier: supported / fixed | Respect facts: keep / edit / remove | Nation-level edits |
|---|---|---|---|---|---|
| gap-africa | 24 | 59 | 54 / 5 | 52 / 7 / 0 | 1 (Siwans name) |
| gap-caribbean-guianas | 18 | 54 | 52 / 2 | 52 / 2 / 0 | 1 (Bari also list) |
| gap-pacific | 23 | 65 | 59 / 6 | 62 / 3 / 0 | 0 |
| gap-south-asia | 19 | 57 | 53 / 4 | 52 / 4 / 1 | 0 |
| **Total** | **84** | **235** | **218 / 17** (0 unsupported, 0 unreachable) | **218 / 16 / 1** | 2 |

Of the 84 gap nations, 72 are new and 12 already existed (same id, same name and country) and were merged,
their new facts appended and duplicate (url, evidence) pairs skipped: Baka, Khoikhoi, Khwe, Mbuti, Samburu,
!Xun (africa); Garo, Santal (asia); iTaukei, Kanak, Ma'ohi, Rapa Nui (oceania). The primary region file
wins field-level ties (name, also, lands, URLs); the gap file only adds facts. This tiebreak was added in
round 2 after a first pass let `gap-pacific` (alphabetically earlier) win over `oceania` and undo the Kanak
overrides.

Of the 235 gap facts, 234 survived. The one drop:

- `gap-south-asia|lk-wanniyala-aetto|1` (respect: remove). A percentage who "wish to keep to their
  Indigenous roots" measures a people by assimilation pressure, from a rights-violations shadow report;
  deficit framing on a herald card. Wanniyala-Aetto keep 2 facts (self-name and meaning; Maduru Oya land).

## 3. Cumulative verifier and respect statistics (all 18 files)

Verifier verdicts on 1308 compiled facts: supported 1105, fixed 195 (fixed text, evidence or as_of
applied), unsupported 3, unreachable 5. Verifier name checks: 4 names flagged `ok: false` with no fix
offered (all gap-africa, see section 5); round 2 adds a merge rule that such a flag must be settled by an
override, so it can never be silently ignored again.

Respect review: facts keep 1150, edit 152, remove 6; nation level keep 406, edit 60, remove 1.

Fact-level edit decisions (one per respect edit, all recorded with a reason): use the respect text 61,
keep the verified text 78, drop 13. Round 2 alone: respect 15, verified 1, drop 0.

Final text provenance of the 1260 published facts: compiler text 1016, verifier-corrected text 183,
respect-edited text 61.

## 4. Dropped facts and nations (cumulative, 51 facts and 4 nations)

Facts: 21 assembler drops (ARCHITECTURE 9.1 ranking of peoples, one scope mismatch), 13 respect edits
left unresolved in round 1 (the verified text broke a respect rule and the fix added an unchecked claim),
8 verifier drops (3 unsupported, 5 unreachable), 6 respect removes (5 round 1, 1 round 2), 3 facts of a
removed nation.

Nations: `xingu-peoples-br` (respect remove: an organization, not a people), `ph-mangyan`, `ngapuhi-nz`,
`penobscot-nation-us-me` (zero surviving facts). All four are round-1 drops; round 2 dropped no nation.

## 5. Round-2 decisions on the 16 fact edits and the names

Rule applied: a respect edit is used only when the verifier-supported meaning is unchanged (reorder,
attribution, narrowing, removal, naming consistency). If it adds a claim the verifier did not check, the
verified text is kept. Where the reviewer cited page text the verifier had not quoted, the assembler
re-fetched the page before accepting.

Used the respect text (15): Benet (drops "raids", a removal); Hai//om (spelling consistency); Korana
(tense only: a self-name is a standing statement, and fact 1 shows living Korana communities); Toubou
(drops "of Chad" on a contested belonging question, a removal); Samburu (drops a literacy aside); Mbuti
(reframed on the evidence phrase itself, "ensuring of the involvement of the indigenous populations, Mbuti
and Efe ... in the management of the Reserve", so the peoples are no longer framed as a park "challenge");
Warao (Guyana ministry page heads the entry "WARRAUS", assembler fetch); Tareno (reorder); I-Kiribati
(Shima PDF extracted locally: "an unimwane, a senior man in the village"); Yapese (both page sentences
confirmed: "were seafaring people who sailed vast distances over the Pacific" and "Even in recent times,
canoes from Yap have sailed to the Marianas, Okinawa, and Palau"); Nauruans (the census report's own
present tense "are represented"); Bhil x2 (IGNCA names the artist; see judgment calls); Ho (removes an
unsupported creator clause; "recently devised" is on the page); Tamu ("Gurung, the Tamu language" is the
entry's own verified naming).

Kept the verified text (1): Kabyles fact 0. The lead name fell back to Kabyles this round, so the respect
text would have put an unverified name (Iqbayliyen) into a fact.

Names (verifier: the cited name source does not show the lead name):

| Nation | Compiled lead | Published lead | Why |
|---|---|---|---|
| ishelhin-morocco | Ishelhin | **Ishelhiyen** | Encyclopaedia Britannica headword "Ishelhiyen" (Also known as: Chleuh, Shluh), fetched with the project user agent, now the name source. Ishelhin first in `also`. |
| iqbayliyen-kabyles-algeria | Iqbayliyen | **Kabyles** | No fetchable page shows Iqbayliyen (Inalco EN/FR, IWGIA 2024; CNRS pages 403; the museum-digital text is a Wikipedia import). Inalco FR "Les Kabyles" is the name source. Iqbayliyen first in `also`. |
| at-mzab-algeria | At Mzab | **Mozabite** | UNESCO page (verifier, browser) uses Mozabite; no fetchable page shows At Mzab (Persee shows only a 1986 book title). At Mzab first in `also`. |
| irifiyen-morocco | Irifiyen | **Rifians** | HCP census names only Tarifit. Ramirez Rodriguez, Tamazgha Studies Journal vol. 1 (2023), fetched and text-extracted, uses "the Rifians"; the journal URL 302s to a Squarespace file, so the file read is cited. Irifiyen first in `also`. |
| siwans-egypt | Siwans | Siwans | Respect asked for Isiwan but gave this fallback itself: no fetchable page shows it (CNRS page says "Siwans"; ELP and MRG 403). Isiwan, Siwan, Siwi added to `also`. |

Other nation-level changes: Bari `also` loses the bare colonial exonym "Motilones" ("Motilon Bari" stays,
official Colombian use); Kanak `official_url` set to null because the Senat coutumier site refused
connections to the verifier (WebFetch, curl, browser) and to the assembler on 2026-10-10 (restore
`https://www.senat-coutumier.nc/` when it answers).

### Judgment calls to show David or the advisory circle

- **Bhuri Bai is named** in both Bhil facts (first named individual in the set). IGNCA, a national
  cultural institution, names her as the first Bhil artist to paint on paper and canvas and says she
  "now works as an artist" at the Adivasi Lok Kala Academy. David asked for credits where due; the
  deceased-persons rule applies to Aboriginal and Torres Strait Islander peoples. ARCHITECTURE 9.1's
  "safer still: no named individuals at launch" is advisory; if the circle prefers it, switch
  `gap-south-asia|in-bhil|0` and `|1` to `verified` in the overrides and re-run.
- Korana and Yapese: tense changes toward the present, each inside the cited page's own words.
- Four Amazigh peoples lead with the name a citable page shows rather than the endonym the compiler chose.
  The endonyms sit first in `also` so search still finds them; promotion needs one fetchable page each.

## 6. Tools

- `tools/merge.py` (round 2): adds `region_map`, per-nation `region`, the unverified-name gate, the
  primary-file dedupe tiebreak, `facts_added` per merge, and `field_overrides` in the log. Fails loudly on
  any missing or unused decision, dash, superlative, bad kind, over-length text or missing source field.
  Run: `py -3.10 tools/merge.py`.
- `tools/_round2_overrides.py`: the script that added the round-2 decisions to `merge_overrides.json`
  (kept as the record; merges into existing entries rather than replacing them).
- `tools/validate.py` (unchanged from round 1): PASS, 0 errors, 54 warnings. The warnings are the known
  review flags: capitalized two-word patterns in Australian facts that are place or organization names
  (Alice Springs, Budj Bim, Yarra River, Dhimurru Aboriginal Corporation and so on) and five superlatives
  that describe a place, tract, agreement or employer, each already allowed in `rank_allow`.
- `tools/nations_refresh.py` (unchanged from round 1): polite re-fetch with the project user agent,
  robots.txt, one request per host per second, 20 s timeout, two retries with backoff, PDF via pypdf,
  diacritics stripped for comparison only, statuses verified / stale / unreachable, `--dry-run`.

## 7. Refresh dry run (`--dry-run --limit 40`, run date 2026-10-10)

- Unique source URLs in `nations.json`: **742** (round 1: 609). Checked 40 across 33 hosts, round robin by
  region so the sample spans the set; 73 requests including robots.txt; 79.2 s.
- Facts checked: 99. **Verified 98, stale 0, unreachable 1.**
- The unreachable one is `https://minorityrights.org/communities/indigenous-peoples-3/` (HTTP 403, a
  Cloudflare challenge page; the compilers read MRG in the browser). Human lane, nothing concluded.
- `nations.json` untouched by the dry run; full reports in `tools/refresh_report.json` and
  `tools/refresh_report.md`.

## 8. Round-3 queue

1. Endonym promotion with a fetchable source: Isiwan, Irifiyen, Iqbayliyen, At Mzab (one page each).
2. Kanak: restore `official_url` when the Senat coutumier site answers.
3. Wanniyala-Aetto: add a strengths fact (language, leadership, institutions) to replace the removed one.
4. Hosts that answer tools with 403 or a JavaScript shell but read fine in a browser: minorityrights.org,
   whc.unesco.org, britannica.com, iwgia.org news pages. Either a browser lane in the refresh tool or
   mirror sources.
5. Verifier notes on better name sources for demonyms (Tongans, Pohnpeians, Niueans, Marshallese "Ri-Majel",
   Garo "A.chik" aliases) and the Hai//om click-letter spelling decision for the site.
6. The 13 round-1 "respect edit unresolved" drops still wait for a double-checked rewrite.
7. A full (uncapped) refresh run before publishing, then the first `stale` review.

## October 15, 2026: two missing Virginia profiles

The bounded source batch adds Cheroenhaka (Nottoway) Indian Tribe and Nottoway Indian Tribe of Virginia
as distinct profiles with seven checked facts, four titled history layers and four own-publisher
resources. Every previous canonical record and fact clock is preserved by a selective import of the
isolated assembler output. The updated contract has 459 profiles and 1,294 raw facts; the public model
shows 1,292 facts and preserves the two existing holds. Two reviewed Virginia directory links supplement
the four reviewed federal-source links. Directory-source counts remain 2,272 overlapping records, not
a total of distinct Nations. Nationwide and worldwide coverage remain incomplete.

Mattaponi history remains unpublished pending reuse scope after its own footer's written-permission
condition was observed. Its directory name and verified own-site link remain. No robots refusal or
takedown is invented. New check/review dates describe actual source work, not new historical events.
See research/batches/2026-10-15-us-missing-virginia.json and its independent review records for measured
checks, source provenance, browser observations, remaining limitations and release gates.

## October 16, 2026: Nansemond And Upper Mattaponi Histories

ZOTHEOS adds two previously directory-only Tribal Nations as distinct researched profiles: Nansemond
Indian Nation and Upper Mattaponi Tribe. Eight concise facts, four titled history layers and four
own-publisher resources follow their own public accounts. Four separately reviewed source records,
two Virginia and two federal, link to these two profiles. The duplicate source appearances do not
create additional Nations or establish a new recognition finding.

Nansemond history connects river homelands, colonial displacement, family continuity and community
institutions. Its Environmental Program is a published description, not independently measured
restoration success or a guarantee of present operation. Upper Mattaponi history distinguishes the
1921 adoption of its name from a much longer community history. Sharon Indian School's earlier
construction, 1950s replacement, 1965 closure and 1987 return remain separate. The 1677 treaty account
is attributed history, not a present determination of treaty rights or land title.

The existing source verifier checked all eight new evidence phrases across four cited URLs with
robots rules and a 3.5-second host interval. All eight were verified. Source meaning, identity,
respect and faithful integration were reviewed separately. The selective canonical import preserves
all 459 previous profile objects and their original fact clocks. Check dates are October 16 UTC;
source publication metadata and historical event years remain distinct.

Patawomeck source access succeeded, but new own-content-based history is conservatively deferred
while ZOTHEOS reviews the publisher's reuse scope. Its existing directory name and verified own-site
link remain visible. This is not an access denial, received takedown, removal request or legal ruling
about copyright in facts. The separate earlier Mattaponi publisher-condition review is unchanged.
No empty profile, permission record, consultation or endorsement is invented.

The updated contract has 461 profiles and 1,302 raw facts. The public model shows 1,300 facts and
preserves two existing holds. Directory coverage remains 2,272 mixed-scope records in eight lists,
with ten reviewed profile links. Four state inventories are preserved; 46 other state discovery
scopes and four additional inclusion lanes remain pending. Coverage is incomplete.

Matching Names now repeats the current result summary at the point of reading, adds digestible
zero-match guidance and offers native routes to adjust filters or search researched profiles. It
preserves the original single live announcement, filter state, bounded paging and static names.
Browser verification and final release gates must be recorded separately; this research report does
not itself establish deployment or physical-device accessibility certification.

## October 16, 2026: Distinct Chickahominy Histories And Easier Reading

ZOTHEOS adds Chickahominy Indian Tribe and Chickahominy Indian Tribe - Eastern Division as two
distinct own-source profiles. Eight concise facts, four titled context layers and four direct
resources describe their histories through their own public accounts. Separate reviews connect
one Virginia directory row and one January 30 federal-source row to each profile. Four overlapping
source records do not create four Nations, merge the two governments or establish new legal status.

Chickahominy history covers river homelands, displacement, schooling and persistence under racial
classification and education barriers. Its environmental vision remains an aspiration. Eastern
Division history connects its school, government formation and incorporation without presenting
twentieth-century institutional dates as the origin of its people. Its Tribal Government remains
distinct from the CIED nonprofit. A 2022 compost/garden account and plans described for 2025 are
dated publisher statements; completion, present availability and measured outcomes are not inferred.

The existing HTTP verifier checked eight new evidence phrases across four cited pages, with robots
rules and a 3.5-second host interval. All eight were verified. Factual meaning, identity and source
conditions were reviewed separately. The selective import exactly preserves all 461 earlier profile
objects and their fact clocks. Actual October 16 UTC check dates, source CMS metadata, historical
years and retained directory-source dates have separate meanings. Source bodies remain outside the
publication tree; measured public receipts contain status, time, byte length and response hash.

The contract now contains 463 profiles and 1,310 raw facts; its public model shows 1,308 facts with
two existing holds preserved. The directory retains 2,272 mixed-scope records in eight inventories
and fourteen reviewed profile links. In Virginia, six profile links and eight verified own-site
identity links are different measures. Four state inventories, 46 remaining state-discovery scopes
and four additional pending inclusion lanes remain visible. Four existing queue tasks changed;
the queue still contains 1,812 tasks. US and worldwide coverage remain incomplete.

Explore This Record adds native jumps to Lands and Facts And Sources, with Context And Resources
only when public context exists. Content remains present for reading without JavaScript. Final
browser observations, release checks and deployment verification must be recorded separately;
this research record does not certify physical-device accessibility or publication.

The earlier Mattaponi and Patawomeck reuse-scope reviews and backoff remain unchanged. Their existing
directory names and own-site links remain visible. No new permission, consultation, endorsement,
takedown, removal request or person check is invented. See the corresponding dated batch record
and source/identity receipts for evidence and outstanding release gates.
