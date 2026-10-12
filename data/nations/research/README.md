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
  the mixed people/government profiles. The latest captured audit measures 457 entries. Directory-only names can be shown with their source and a clear
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
All candidate matches remain unreviewed. Neither 143 nor 45 is a count of confirmed federal-government profiles,
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
