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


## October 15 afternoon source and history batch

`us_nj_state_directory_2026.json` preserves three exact labels from the New Jersey commission's representation
paragraph. They are named representation groups, not a complete recognition register. Inter-Tribal People is
a separate membership category, not a fourth Nation. Nine commission members, four representation categories
and three named groups are different units. The scope is explicitly shown in the source inventory chooser.
No preferred-name, canonical identity or current legal recognition determination is inferred. Sand Hill and
Cohanzick source leads stay in an explicit beyond-commission discovery task, not silent aliases or approved
government identities. Historical 2018 and 2019 announcements and conflicting creation-law labels remain
research evidence; no current recognition event or emergency is invented from today's observation date.

Four state source inventories are now preserved, with 46 state discovery scopes and all four additional
inclusion lanes pending. Source records still overlap and are never added as a count of distinct Nations.
State namespace validation and directory removals now derive from explicitly configured typed inventories,
so adding a state cannot leave its source labels or takedown namespace out of sync. Unknown states remain
rejected until their inventory contract is configured.

The Ute Mountain Ute profile adds one own-source historical homelands paragraph and direct source link.
The Tribe's account describes parts of four present-day states and shared historical border areas. It is not
a present-day reservation map, property ruling or jurisdiction determination. The October 15 fetch matched
the October 12 homepage bytes; this is a fresh review of an unchanged source, not newly published history.
Distinct Ute governments and the broader peoples overview remain separate. No sacred material or coordinates
were imported, and no existing fact was newly verified by adding this contextual account.

Context review dates now validate against the actual UTC calendar day, independently of the canonical model's
last fact-check day. New source review never requires backdating evidence or advancing unrelated checked,
last_verified or generated values. Actual future or invalid context dates, wrong nation/URL links, removed
nations and held fact references still fail or suppress publication under the existing bounded contract.


## October 15 own-source histories and mobile directory

The Southern Ute and Ute Indian Tribe profiles gain five short historical context layers and four direct
own-publisher resources. These stay separate from canonical fact checks. Southern Ute layers cover the
Mouache and Caputa homelands, allotment, restoration and education. The Ute Indian Tribe layers attribute
its Uncompahgre land-restoration account and a dated July 2025 water-case statement. A reported court
recommendation is not a final judgment or a current case outcome. Unknown PDF publication dates and
hearing years remain unknown. No acreage, present jurisdiction, urgency score or private/sacred detail
was imported. The two governments and Ute Mountain Ute remain distinct.

Context notes may carry an optional title of at most 160 characters. Invalid, blank and oversized titles
fail validation. Titles are escaped HTML headings and follow the same publication/removal controls as
their paragraphs. Untitled legacy output stays identical. Source review dates never advance unrelated
canonical checked, last_verified or generated dates.

The Nanticoke Lenni-Lenape source followup captured a self-branded current-site candidate and an NJ Education
document with older published links. The older published host's robots returned HTTP500. Reading stopped
without a homepage request or alternate-host bypass. Current ownership linkage remains pending: the
directory official_url stays null, its canonical crosswalk stays unreviewed, and the draft history stays
unpublished. The queue records the actual failure and a one-day retry backoff. Self-branding alone did not
become a verified ownership chain. No directory names were removed because a source could not be checked.

The directory now places name search immediately after its introduction, before the optional source
filter. The complete profile/source distinction remains in a default-closed native details element.
Every existing static source record, ID, script, stylesheet and source disclosure is preserved. Search
still works in bounded batches and all names remain in HTML without JavaScript. Current coverage remains
2,272 differently scoped source records in eight lists, 457 canonical profiles, four preserved state
source inventories, 46 other state discovery scopes pending, and four additional inclusion lanes pending.
These numbers do not count distinct Nations or establish complete US or worldwide coverage.


## October 15 next own-source histories and reading design

Three existing profiles gain nine short, titled layers: Ute Mountain Ute, Fort Sill Apache and Catawba.
Seven own-publisher resource links are new. The existing Ute Mountain Ute Natural Resources and Fort Sill
history resources are updated in place, with exact successful receipts and their own October 15 review
dates. No new canonical profile, directory identity match or canonical fact refresh is claimed.

Ute Mountain Ute rights dates remain attributed to its Natural Resources account, rather than an
independent interpretation of the underlying Act or consent decree. Environmental and educational
pages describe program purposes and reported curriculum collaboration, not measured outcomes, current
operation or confirmed completion. Fort Sill context explains coercion around displacement and later
institutional rebuilding. The source's mid-1970s period is retained; no exact 1976 date is invented.
Preservation goals are distinct from proof of current classes or outcomes. Related Apache and Ute
governments and broader peoples remain separate records.

Catawba context covers land pressure, constitutional organizing and land/community planning. Its own
About page gives conflicting 1951 and 1959 federal-status-removal years. Neither year is adopted, the
resource explains the conflict and a separate dated followup remains pending. The existing North
Carolina exact-day discrepancy and retry delay are unchanged. The Black Snake Farm resource labels its
July 15, 2025 FAQ and funding stated through June 2026; current funding, eligibility, schedules and
availability are not established. No aid availability or present legal outcome is promised.

Thirteen sanitized HTTP receipts preserve eleven successful responses and two genuine robots404
responses. Missing robots files are absence of published restrictions under the existing unavailable-
robots policy, not positive permission or endorsement. Actual body hashes, timestamps and paced reads
are retained; no denied source, outside host, sacred detail, personal contact or coordinates were used.
Full source bodies remain local audit artifacts. Reviews are AI-assisted, not human or Nation approval.

Context reading styles now separate subsection headings, paragraphs and source-review dates; resource
links offer at least 44px height. The shared stylesheet is content-addressed, so the build updates its
reference across generated Nations pages. Theme tokens, motion code, the landing page, game, owner-
supplied intro and canonical data remain unchanged. Browser phone/tablet/desktop checks and their
limits are recorded separately; no physical-device or screen-reader certification is claimed.

The queue and source catalogue retain this bounded batch and the unresolved year conflict. Coverage
still consists of differently scoped source records, not a complete list of distinct Nations. Four
state source inventories remain preserved, 46 other state discovery scopes and all four additional
inclusion lanes remain pending. The batch record is batches/2026-10-15-us-next-histories.json.


## October 15 missing Virginia profiles and directory access

Two previously directory-only communities now have separately researched profiles: Cheroenhaka
(Nottoway) Indian Tribe and Nottoway Indian Tribe of Virginia. Their own published names, official
sites and distinct identities were independently AI-reviewed before the two Virginia source rows
were linked. Shared Nottoway wording does not merge governments or establish exclusive representation.
Empty aliases preserve that distinction.

Seven short facts and four titled historical layers use the Tribes' own pages. Topics include
community continuity through land loss and reclassification, 2002 Cheroenhaka government reorganization,
historical language records, the public 1821 petition account and the Nottoway center's May 5, 2012
opening. Four direct resources let readers continue at the publishers. Source publication dates remain
unknown except the Cheroenhaka snapshot's printed December 31, 2022 update. Historical dates do not
establish current recognition, jurisdiction, visitor access, fluency, funding or measured outcomes.
Intertribal allegations and derogatory colonial classifications are not adopted.

The existing assembler compiled only the new reviewed input in isolation. The existing HTTP verifier
then actually checked all seven new evidence phrases across six cited URLs, with robots rules and
a 10.2-second host interval. Its legacy compile date was replaced with the real candidate assembly
day. The final selective import preserves every prior canonical nation/fact object and its clocks.
Raw, verification and respect records remain durable inputs; no human or Nation approval is claimed.

Mattaponi robots and homepage returned HTTP200, but the homepage footer requires expressed written
Tribal Council permission to reuse content. No Mattaponi history or empty profile was published.
Its existing directory label and verified own-site link remain visible. A dated reuse-scope followup
retains that distinction, with a seven-day not-before date and no routine re-fetch of the unchanged
notice. This is not an access failure, received takedown, blanket removal or legal ruling.

The optional Profiles Ready To Read checkbox combines with name search and source inventory. It
filters only reviewed directory links to actually public profiles. Six linked source records do
not mean only six researched profiles exist: the hint links to all profiles. Pending source records
remain available when the filter is off, and all names remain in static HTML without JavaScript.
The direct Browse Matching Names link avoids unnecessary scrolling past the source explanations.
Native checkbox/keyboard behavior, bounded paging and explicit-source/deep-row resets remain checked.

Current measured coverage is 459 canonical profiles, 1,294 raw facts, 1,292 public facts and two held
facts. The directory still has 2,272 differently scoped source records in eight lists. Four state
inventories are preserved; 46 other state discovery scopes and four inclusion lanes remain pending.
These overlapping units are not a count of distinct Nations or complete US/worldwide coverage.
The canonical game-card export includes the same two new profiles without changing game mechanics.
The batch and independent reviews are recorded in batches/2026-10-15-us-missing-virginia.*.json.

## October 16: Two Missing US Profiles And Clearer Results

Nansemond Indian Nation and Upper Mattaponi Tribe now have distinct own-source profiles with eight
checked facts, four history layers and four resources. Separate identity reviews link two Virginia
and two federal source records to these same two profiles. Each source record keeps its original
category and date; no recognition list defines Indigenous identity.

Patawomeck public access succeeded. New own-content-based history remains pending a conservative
reuse-scope review, while its existing directory name and verified own-site link stay visible. This
is not a takedown, access denial, removal request or legal ruling about facts. The separate Mattaponi
publisher-condition followup remains unchanged. Source checks use October 16 UTC; historical dates,
page metadata and old fact clocks retain their own meanings.

Current coverage comprises 461 canonical profiles, 1,302 raw facts, 1,300 public facts and two held
facts. The directory retains 2,272 mixed-scope records in eight inventories, with ten reviewed profile
links. Four state inventories are preserved; 46 state discovery scopes and four additional inclusion
lanes remain pending. The persistent queue contains 1,812 tasks. These are different units, and none
supports a complete US or worldwide coverage claim.

Matching Names gains an adjacent summary and useful empty-result recovery. The single original live
status, native links, retained filters, bounded paging and no-JavaScript names remain part of the
reading contract. Source and control review do not replace final browser and deployment verification.


## October 16: Exact Sources For History Layers And Two Open Research Gaps

Coharie's two existing context layers now carry explicit native source links: the schooling layer
points to the Tribe's history page, and the river layer to its Great Coharie River Initiative page.
Their text, original review dates and canonical facts remain unchanged. Optional `source_urls` accepts
one to four distinct exact URLs already described by the same Nation's approved official resources.
References resolve across context files without depending on filename order. Unapproved, malformed,
cross-Nation, control-character or ambiguous references fail validation. If a referenced resource is
held, its associated layer and citation remain hidden. Older notes without explicit references are
not backfilled or rewritten. Citation and context review dates keep their separate meanings.

Meherrin and Occaneechi missing-profile research reached successful public responses, then stopped
at different publication-scope concerns. Meherrin's stated site-use conditions need scoped review;
no written Tribal authorization is claimed. An Occaneechi history capture contains unrelated
material, and its dated media disclaimer also needs scope review. No actor, blanket site-compromise
claim, legal restriction on facts, recognition finding or current emergency is inferred.

Both tasks remain `needs_review` with explicit pending publication scopes, no routine refetch,
no automatic restoration and no outreach. Their directory names and original October 14 source
edition stay visible. No new profile, historical facts or community endorsement is published from
these sources. These are not received takedowns or failed-access receipts. The existing directory
removal-hold mechanism, prior publisher conditions and fact/person restoration controls are unchanged.

Coverage remains 467 canonical profiles, 1,326 raw facts and 1,324 public facts, with two held facts.
The directory retains 2,272 overlapping source records. The 1,812-task queue has 1,682 pending,
128 needing review and two existing blocked tasks. Different source units are not added into a count
of distinct Nations, and no complete US or worldwide coverage is claimed. The batch and source
metadata are retained in `batches/2026-10-16-us-source-scopes-and-layer-links.json` and `receipts/`.

## October 16: Sappony, Waccamaw Siouan And Native History Navigation

Two missing North Carolina directory profiles gain separately reviewed own-source histories. Sappony
preserves its High Plains community across North Carolina and Virginia, changing livelihoods, chosen
name and shared family governance. Waccamaw Siouan preserves an attributed account of refuge and
continuity, the completed 1986 to 2005 leadership period of Priscilla Freeman Jacobs, member governance
and stated educational aims. Related peoples and similarly named governments remain distinct.

Eight facts passed the actual isolated verifier across six cited URLs with robots enabled and a
10.2-second host interval. Seven own resources support four short reading layers. Unknown publication
dates stay unknown; historical event dates and actual October 16 checks remain separate. Older statewide
counts, uncertain early-contact chronology, oral-origin accounts, personal contacts, media and current
service promises are excluded. The Sappony community HTTP 404 and inspected-but-unused article are recorded
as limits, not successful sources or a profile-wide takedown.

Optional per-note reading_id creates stable native heading targets. With at least two visible opted-in
layers, In This History offers wrapping touch/keyboard links. Duplicate IDs within one Nation fail even
if a candidate is held. Holds suppress the related link and target; surviving IDs never renumber.
Legacy fragments without opt-in remain byte-exact. No new scripts, storage or remote request is added.

Coverage is 469 canonical profiles, 1,334 raw facts and 1,332 public facts, with two prior held facts.
The 1,812-task queue changes only these two subjects; 1,680 tasks remain pending, 130 need review and
two prior tasks remain blocked. Directory names still comprise 2,272 overlapping records, not distinct
Nations. Meherrin, Occaneechi and all prior publication-scope/backoff decisions remain unchanged.
The source batch is batches/2026-10-16-us-sappony-waccamaw.json. Review and live verification are separate
release gates; no human or Nation approval is claimed.

## October 16: MOWA And Practical Pathways

The three-subject batch preserves MOWA as distinct from other Choctaw peoples and governments. Its
own historical accounts support four checked facts, two titled reading layers and four own links.
No recognition adjudication, current membership, service outcome, restricted knowledge or media is
imported. Exact response hashes are metadata; full publisher bodies stay outside the repository.
Four new facts passed the actual isolated verifier with robots enabled and a measured 10.316439-second
minimum interval in the final run. The earlier measured 10.195433-second gap is recorded, not rounded
into compliance. The bounded repeat used a 10.3-second wrapper floor; both attempts remain in evidence.

Piqua remains needs_review for an express name/seal-use condition, manual-only with no automatic
refetch/restoration or alternate-source bypass. Echota remains blocked after a pre-HTTP TLS hostname
failure, with one-day backoff and no invented HTTP response or source hash. Existing directory labels
and the original Alabama source date remain visible. The other 1,809 queue tasks stay unchanged.

The ten practical pathways use source-linked context plus explicitly attributed ZOTHEOS planning
proposals. Public offices do not replace a Nation's sovereignty. UNDRIP, country-specific law and
community protocols are distinct. US ICWA eligibility is not universal. OCAP is scoped to First Nations
in Canada, with FNIGC's trademark attribution. No translation invention or unauthorized voice reuse
is proposed. Optional named canonical examples inherit all fact/Nation holds, receipt clocks and
person/grace labels. A held named source removes the entire dependent chapter and offline brief entry.
There are no new guide scripts, forms, uploads, browser storage or network providers.

Source records: batches/2026-10-16-mowa-and-pathways.json and
batches/2026-10-16-practical-pathways-sources.json. Release checks and live verification remain separate.

## October 16: Own Sources And Reader-Controlled Practice

A bounded three-subject batch adds distinct UCAN and Southeastern Mvskoke profiles using their own
published sources. Two separate source authors cross-reviewed the proposals. Eight facts passed
actual isolated verification with robots enabled and no redirects. Exact response hashes and source
dates remain distinct; original bodies stay outside the repository. No human or Nation approval is implied.
Ma-Chis returned HTTP403 at robots; the directory remains and a one-day backoff is recorded.

Four Paths To Action examples connect canonical source facts with clearly hypothetical planning
exercises. Public evidence precedes questions, numbered steps, limits and reflection. No outreach,
submission, land access, fundraising permission, legal entitlement or current-service outcome is promised.
The new examples inherit canonical holds, receipt clocks and person/grace labels. There are no new
guide scripts, forms, browser storage or network providers. The blank action brief remains available.

Source record: batches/2026-10-16-own-sources-and-practice.json. Publication and live checks remain separate.

## October 16: Community Histories And Focused Pathway Briefs

A bounded three-subject batch adds distinct Cherokee Tribe of Northeast Alabama and Absentee
Shawnee Tribe of Indians of Oklahoma profiles using their own published sources. Separate automated
reviews checked source meaning and respect conditions. Eight facts passed actual isolated source
verification: seven fact URLs and two robots files, with measured post-response spacing above 10.6
seconds, no redirects or retries. Metadata dates, historical dates and actual check dates stay separate.
No human or Nation approval is implied. Agua Caliente's robots returned HTTP403; its directory row
remains, with one-day backoff and no content fetch or alternate-host attempt. Other tasks stay unchanged.

Two new hypothetical examples support private role maps and community-led learning plans. Neither
creates legal routes, citizenship rights, teaching authority or cultural reuse permission. Ten chapter
briefs add native downloads, blank offline reader fields and selected sources without new scripts,
forms, storage or network providers. Required-source holds remove dependent briefs from the normal
build; named-example holds do not hide unrelated chapters. Shared blank-brief access remains.

Source record: batches/2026-10-16-community-history-and-pathways.json. Publication and live checks remain separate.
