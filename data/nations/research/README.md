# Nations coverage and research queue

This sidecar extends the existing Nations system. `../nations.json` remains the published profile contract.
The existing `../sources/` compiler, independent verification and respect-review files, assembler overrides,
weekly source checks, publication gates and takedown policy remain in charge of facts. Research tasks never
publish themselves. This queue is durable in Git and can be resumed by a later local Codex run without this chat.

The weekly `nations-refresh` workflow checks already cited sources and opens a pull request. It does not discover
missing governments or peoples. Its presence in the checkout does not prove its schedule or repository permissions
are currently enabled. The architecture's proposed `nations_author.py` is not present in the current tools.

## Files

- `us_federal_directory.json`: every name record in the January 2026 federal notice, with its entity type,
  source, date, historical aliases and unreviewed profile crosswalk. This is directory information, separate from
  the mixed people/government profiles. The captured canonical registry audit measures 457 researched profiles, separate from the 577 federal source-name records. Directory-only names can be shown with their source and a clear
  profile-pending label. New facts still pass the existing review lane.
- `coverage_queue.json`: tasks, priorities, leases, source scopes, dated receipts and independent-review states.
- `ca_registry_groups_2024.json`: dated Canadian administrative-name snapshot, with 634 named registry groups
  from the 2024 report. It is not a complete list of Canadian Indigenous peoples or a current government count.
- `directory_sources.json`: research sources, exact host allowlists and their distinct entity units. This does
  not modify `../source_priority.json` or approve a source's claims for publication.
- `initial_audit.json`: measured initial registry and directory counts. Counts are tied to the registry hash.
- `receipts/`: retrieval records and public-source snapshots. The existing `.vercelignore` excludes `data/`
  from the website. These are internal site records, not secrets; the GitHub repository is public.

## Count discipline

The [2026 federal notice](https://www.govinfo.gov/content/pkg/FR-2026-01-30/html/2026-01899.htm) states 575 Tribal
entities. Its structured name list contains 577 distinct records: 348 in the contiguous-state section and 229
in Alaska. All records are preserved and the difference is explicitly unresolved. The
[BIA directory](https://www.bia.gov/service/tribal-leaders-directory) dataset fetched for this audit has 602
rows: 577 classified Tribe and 25 classified Affiliate. These are measured directory rows, not a new legal
recognition finding, and the GIS data cannot establish land ownership.

The captured registry has 143 US-associated entries, including governments and broader peoples. There are
45 exact name/alias candidate rows in the federal-directory crosswalk and 532 without such a candidate.
Those initial candidate matches were unreviewed in that captured audit. Four government crosswalks were subsequently reviewed with AI assistance and linked by explicit receipts. Neither 143 nor 45 is a count of confirmed federal-government profiles,
and 532 is not a proven count of absent nations. No government-coverage percentage is calculated.

Canada's [First Nation Profiles](https://services.sac-isc.gc.ca/fnp/main/Index.aspx?lasng=eng) states 619 First
Nations. Its [2024 Indian Register report](https://www.sac-isc.gc.ca/eng/1753213597358/1753213649039) distinguishes
619 bands from 634 registry groups. Inuit regions, Inuit communities, Metis governments and broad peoples need
separate source inventories. A four-region Inuit map is not a four-community denominator.
The saved Canadian report contains 646 numbered headings. Excluding its 12 explicitly labeled General list
administrative headings leaves 634 named groups. The snapshot preserves those group names and codes,
dated to 31 December 2024, with all identity crosswalks unreviewed.

Other recorded units include [Peru's 55 identified peoples](https://bdpi.cultura.gob.pe/mapa-de-pueblos-indigenas-u-originarios),
[Brazil's 391 census ethnicities/peoples/groups](https://www.ibge.gov.br/brasil-indigena/),
[Colombia's 115 census peoples](https://www.dane.gov.co/files/investigaciones/boletines/grupos-etnicos/infograf%C3%ADa-grupos-etnicos-2019.pdf)
and [Guatemala ALMG's 22 Maya linguistic communities](https://almg.org.gt/actividades-2/). Their source dates and units
stay attached. Community, language, territory, governing body, census category and broader people are never
silently equated. A language list is not an all-Indigenous-peoples directory. State recognition does not decide
who may identify as Indigenous, and source lists are not claimed to enumerate the entire world.

## Priority and recurring work

Chiricahua identity and present-day governing bodies come first, including the Fort Sill government's own
account and the Mexican catalogue. Keep Fort Sill government identity, Mescalero government identity and the
broader Chiricahua people distinct until sources and naming review settle their relationships.

The three Ute governments each have their own task. The Nuche entry now remains a broader Ute people record, with the three government names removed from its aliases.
Separate Southern Ute, Ute Mountain Ute and Ute Indian Tribe profiles were added on 12 October 2026.
Do not duplicate them. Preserve the broader people record and review identity crosswalks against the original sources.

After owner priorities, enumerate Americas sources and rotate global geographic lanes at equal priority.
Read at most three subjects per run. Daily execution belongs to the Codex heartbeat, which the primary session
manages. This tooling installs no local model, service, scheduler or background executable.

From the repository root:

```text
python tools/nations_research.py validate
python tools/nations_research.py audit
python tools/nations_research.py reconcile --write
python tools/nations_research.py next --limit 3
python tools/nations_research.py claim --task TASK_ID --write
python tools/nations_research.py finish --task TASK_ID --note "Factual handoff" --receipt RECEIPT_JSON --write
python tools/nations_research.py block --task TASK_ID --note "Measured source failure" --write
```

Audit, validation and planning are read-only. Reconciliation prevents re-adding explicitly linked existing
profiles, and separates unreviewed candidate identity work from new-profile drafting. It does not invent
an identity match or a human review. Endonyms and short names without exact matches still need a source-backed
identity check against names, aliases and the nation's canonical site before a new profile is drafted.
A claim creates a four-hour lease; a later run can reclaim an expired
lease. A successful handoff goes to `needs_review`, never to approved or published. A blocked source has a one-day
retry delay. One writing steward at a time owns the queue; Git conflict review is required after concurrent edits.

Each source read needs its real retrieval date. HTTP reads record the actual status and saved-body SHA256.
Browser-tool receipts record the observed title and supporting text and omit unknown HTTP status. Failed fetches
remain failures; no inaccessible source becomes verified through a guessed receipt. New source hosts need review.
Plain HTTP links from the BIA dataset remain disabled until a separate HTTPS and source review is recorded.

Research land rights, water, governance and current risks from the nation's own statements first, followed by
official institutions and the established source priorities. Risk starts `unassessed`. A risk signal must retain
its source URL, publication date, event date and receipt, and stays pending independent review. Historical events
do not become current emergencies merely because the page was fetched today. No inferred urgency score,
unsourced casualty number, sacred or restricted cultural detail, private personal record, or outreach belongs here.

Every profile draft should include an explicit identity unit, source-backed preferred name, evidence phrases,
and an independent verification/respect handoff through the existing regional research files. Ordinary source
and identity review may be agent-led and labeled AI-assisted where existing policy allows. Reviewed pull
requests and the owner's standing publication authorization control release; this queue adds no blanket
human-approval barrier. Actual human-only restoration rules, overrides, corrections and nation-led takedowns
still apply. Do not use the queue to bypass those rules or publish unreviewed AI claims.

## Verification

The accompanying stdlib tests cover mixed-unit counts, unresolved source-count discrepancies, unreviewed links,
HTTPS/host boundaries, bounded regional selection, expired leases, review handoffs, retry backoff, and read-only
defaults. Test fixtures are fictional and never enter the published data.

```text
python -m unittest discover -s tools/tests -p test_nations_research.py
```

If a restricted Windows sandbox cannot write its temporary directory, set `ZOTHEOS_TEST_TMP` to an explicitly
owned scratch directory. Tests never alter the published registry.

## Source inventories added in the October 12 steward cycle

`ca_fn_profiles_2026.json` preserves 638 distinct First Nation Profile search records observed on
October 12, 2026. A fresh landing page still states 619; the 19-record difference remains unresolved.
The observation date is not an effective date for every record. These records are separate from the
634 administrative register groups dated December 31, 2024. Four literal question-mark source labels
remain visible and prioritized for review against the communities' own names. No inferred correction
or cross-catalogue identity match was approved.

`br_census_groups_2022.json` preserves 391 named leaf census categories. The source table has 404 data
rows: 12 subtotal headings and one unspecified residual response are excluded. Eight named leaf
categories under the other-Americas heading remain included. Source indicators are statistical IDs,
not government identifiers. Asterisks remain in the original source labels and their meanings are
explained publicly, including linguistic-family responses and self-declared names historically
classified as having disappeared. The saved table is a 2022 census snapshot; a revised 2026 edition
was not established. The original shorter fetch pacing is recorded as a policy defect, and both
primary sources were reread with compliant pacing and identical body hashes.

The two inventories create 1,029 pending per-record research tasks, not 1,029 new nation facts or
government profiles. Exact-name candidates create separate identity-review tasks. The offline queue
can validate and reconcile these typed IDs and still selects at most three subjects per run. A name
that happens to match an existing broader people is not automatically the same government or census
category. Preferred names, identity relationships and own-source histories remain research work.

`sources/chiricahua-scope-2026-10-12.context.json` and the resources page provide a bounded source guide.
Fort Sill, Mescalero and Chiricahua Apache Nation remain separate canonical records. INPI's N'dee
account is broader than Chiricahua and does not establish a single government or an inventory of
named Mexican communities. That unresolved work remains in a separate priority task.

`publication_holds.json` can suppress a directory-only ID using a dated removal receipt. It does not
replace canonical profile/fact overrides, approve restorations or create a removal request. It starts
empty. Holds apply to all name inventories and their font input; no directory-only name is restored
automatically. Composite named resource cards bind to canonical nation IDs and disappear when any
referenced profile is held. Update an existing context item when only its review date changes;
do not append duplicate cards in a new daily file.

The batch record is `batches/2026-10-12-140316.json`. Full source captures stay in local research
artifacts; public repository receipts exclude session headers and form state. Missing HTTP access
remains a failure, not evidence. No new human verification, urgent risk signal, recognition finding
or complete-coverage claim was created.


## Inclusive US coverage, October 14 UTC observation cycle

The owner's priority is all Indigenous peoples and distinct Nations in the US, including communities outside
federal and state recognition. This is a continuing research goal, never a completed-coverage claim. The new
`us_coverage_plan.json` tracks all 50 state source-discovery scopes and four additional lanes: communities
outside recognition lists, Native Hawaiian peoples and communities, Alaska villages/peoples/organizations,
and cross-border or wider US-associated communities. Virginia and North Carolina source inventories are
preserved; 48 other state discovery scopes remain pending. Those scopes are work units, not Nation totals.
A state directory can be preserved while its unlisted communities and histories remain incomplete.

`us_va_state_directory_2026.json` contains 11 observed table rows. Seven source asterisks mean the Virginia
page marks both federal and state recognition; this is attributed notation, not a new legal-status finding.
`us_nc_state_directory_2026.json` contains nine observed tribe headings. NC DOA directory wording says Catawba
petitioned for recognition, while its landing page announces recognition at a June 6 meeting without an
established year. The discrepancy remains visible and queued; nine headings are not a certified recognition
total. Both inventories use `state_tribal_directory_listing`, `snapshot_kind: source_observation`, and the
UTC retrieval day, not an inferred legal effective date. Overlapping lists never create additional Nations.

Every source/own-site link receipt must exist, stay within the bounded receipts directory and match its
measured URL, hash and timestamp. Four Virginia own-site identities and one Lumbee own-site identity were
read and independently reviewed with AI assistance. Canonical identity crosswalks remain unreviewed. No
new historical fact, human receipt, urgency claim or recognition adjudication was created. Full captures
remain local; repository receipts omit cookies, sessions and form state and say where capture bytes live.

Named source notes use `scoped_notes` with explicit directory IDs. Holding any bound record suppresses the
whole note; a named discrepancy's supporting link follows its subject's hold. This prevents an otherwise
removed directory name from surviving in a note. Removing a required inclusion lane or the whole plan when
state inventories exist fails the build. The public directory preserves every original name in its HTML;
JavaScript adds source selection, 40-record browsing and searchable names. No-JavaScript readers retain
inventory anchors and browser Find. Source counts, observation dates and profile checks retain their own
meaning. The footer's compilation/check line is explicitly scoped to researched profiles.

The persistent queue contains per-record identity/history tasks, state-level source discovery and explicit
inclusion-gap tasks. Researchers must locate and read own and primary sources before adding facts; discovery
tasks without approved source IDs must establish a reviewed host allowlist before their first captured read.
Do not turn a state label into a homeland boundary, government count or requirement for Indigenous identity.


## October 15 source followup

Approved NC commission minutes, visually read because the PDF is scanned, record the Catawba recognition motion
in June 2026. The minutes are headed June 5, while the DOA announcement says June 6 without giving its year.
The old directory still describes a petition. The public note now distinguishes the supported month from the
unresolved day difference; it does not assign a legal effective day or alter the October 14 directory snapshot.
April committee-report acceptance and September minutes approval are not new recognition events. Supporting
source links are bounded, match successful measured receipts and follow the discrepancy subject's hold.

INPI's linked KML contains one N'dee/N'nee/Ndé record of type Sede in Chihuahua. The existing source guide adds
that distinction without copying coordinates, creating a government identity or claiming all communities.
A located own-published candidate site denies automated reading; no content was fetched or verified. INALI
failures and the inaccessible legislative summary remain failures, not evidence for public facts. Original
canonical facts, identity crosswalks, human receipts and old source observation dates remain unchanged.

The two source tasks move to needs_review with real receipts. Separate pending followups retain the unresolved
day discrepancy and need for permissible own-government sources, with a seven-day retry delay to avoid routine
repeated reporting of unchanged material. Source guides are AI-assisted and do not claim human approval.


## October 15 Alabama source expansion

`us_al_state_directory_2026.json` preserves nine name headings from the commission's publicly linked roster.
The commission page states nine listings with one federal overlap. These are source records, not nine new
Nations or complete Alabama coverage. The source has one physical PDF page with a printed PAGE 2 footer;
no publication or recognition effective date is inferred from its upload path or Last-Modified header.
Original source capitalization and abbreviations remain visible. No leaders, personal contacts or imagery
were imported. All identity crosswalks remain unreviewed, with nine typed own-source/history followups.

The inclusion plan now preserves three state source inventories and leaves 47 state discovery scopes plus
all four additional inclusion lanes pending. State recognition never defines who is Indigenous. Name search
now precedes the long inclusion and source chooser sections while preserving no-JavaScript name access.
Alabama rows support the same receipt, scope and takedown controls as Virginia and North Carolina. The named
asterisk explanation is bound to its subject; a hold removes that note with the source row.

A candidate own-source redirect was recorded for Poarch. Genuine robots404 was treated as unavailable under
the existing verifier policy and RFC 9309 section 2.3.1.3; the later canonical robots200 allowed public paths.
The canonical homepage returned HTTP403. Reading stopped immediately. No denial was bypassed, no own
identity/history claim or official website link was published, and its followup is deferred for seven days.
Failed and unknown access states remain distinct from successful source receipts. Full source captures stay
local; only sanitized provenance metadata enters this public repository.
