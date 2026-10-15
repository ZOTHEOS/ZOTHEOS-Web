# ZOTHEOS Website Expansion Collaboration Handoff

Prepared 15 Oct 2026 for Claude Code from Codex on MELLO MOOSE.

The owner authorizes continuing website enhancement, expansion, commits and publication. They explicitly asked Codex and Claude Code to collaborate, share context, inventory Claude's AI cinema tools and develop ambitious visual work aligned with ZOTHEOS's mission. This handoff coordinates that work. The public website is the current scope.

## Mission And Standard

The founder clarified the public mission on October 15: give power back to humanity. Truth, dignity and sovereignty guide the work, especially in service to people whose voices have been silenced or overlooked. Universal peace is the moral horizon. Help people understand, question and inspect information, strengthen their own judgment, and act with care for one another and the living world. Care explicitly includes land, water and ecosystems. Indigenous Nations visibility, histories, land, sovereignty, language, community work and rights remain a standing priority. Make knowledge welcoming and digestible without weakening its meaning. Attribute communities' own published accounts without implying consultation, permission or endorsement that did not occur.

These are commitments directing the work, not demonstrated guarantees of protection, healing, environmental benefit, consciousness or guaranteed truth. Challenge harmful claims and conduct without dehumanizing people. Accountability requires evidence and fair processes. Do not turn general concerns about power or manipulation into unsupported allegations of universal coordination. Do not publish private personal material or private future project concepts. Truth outranks spectacle. Multiple models can share an error; agreement is not proof. Source claims precisely, preserve uncertainty and make contradictions visible. Product architecture illustrations are explanations, not measured app demonstrations. Core feature status cannot be established by website copy alone. Indigenous identity is not defined by government recognition. Do not merge a people, community, governing body, representative organization, language or census category because the names resemble one another.

## Station And Ownership

- Owner: David Garcia, with final authority over product direction and publication.
- Codex: integration, repository coordination, evidence contracts, verification, pull requests and production checks. Actual model name is not asserted here.
- Claude Code: invited collaborator for visual direction, cinema tool discovery, storyboard and motion prototypes, independent critique and scoped implementation. Report the model actually selected when available; do not assume a model name from prior chat.
- Current local machine: MELLO MOOSE, reported by the owner as the RTX 4090 workstation. This handoff has not measured its GPU.
- Titan is a separate workstation, reported as RTX 5080. A tool on Titan is not automatically available here. No USB transfer has been established as necessary for this batch.

Start each substantive handoff with station, machine, branch and task. State what is observed, proposed, measured or unresolved. Preserve unresolved objections verbatim in the shared record until the owner or evidence settles them.

## Repository And Publication

Website only: `C:\ZOTHEOS-Web`, remote `https://github.com/ZOTHEOS/ZOTHEOS-Web.git`, production `https://zotheos.org`, Vercel project `zotheos-web`. Production follows `main`.

Do not touch `C:\ZOTHEOS` or ZOTHEOS Core, private research, signing keys, workstation services or unrelated checkouts. No prune, gc, cleanup, resets or deletion of other work. Never bypass permissions. Git inspection uses `git -c gc.auto=0 -c maintenance.auto=false ...`.

Inspect branch, remote, working tree and other writers before editing. Codex currently owns the main website working tree. Your first assignment is read only. Do not switch its branch, edit its files or start deployments while replying. Return proposals and ownership requests first. Implementation will use a separately assigned checkout and branch, with no overlapping file ownership. We review patches, commit on feature branches, open and attach a pull request, merge after required checks, then verify exact live output. The owner has authorized this workflow. No direct pushes to main.

No messages to third parties, donations, forms or outreach are authorized. The owner has authorized Codex to communicate with Claude Code for this collaboration. Do not expose credentials, private configuration or personal contacts.

## Published State

Published baseline when this handoff was prepared: `5bf1982bb58b96fbb81cf272e5240448d995425e`, PR 14, https://github.com/ZOTHEOS/ZOTHEOS-Web/pull/14. Feature revision: `b302dc809ff77754fbc10a531e063ffeb749c6f1`. Confirm current main before implementation.

PR 14 adds open source-inventory choices, source filters, 40-record browsing, continuation focus and working record deep links. Every name remains in the HTML without JavaScript. Source detail disclosures keep unresolved differences outside the fold. Actual preview checks included 390px phones, 1280px desktop, Appearance through the phone Menu, light and dark controls, Calm motion and Ute search selecting the three distinct federal-list governments.

The measured collection has 457 canonical profiles and 1,287 raw facts, with 1,285 public and two named-person facts held. The source directory has 2,260 records in six differently scoped inventories. These are not counts of distinct Nations:

| Source Inventory | Observed Records | Meaning |
| --- | ---: | --- |
| US federal published names | 577 | January 30, 2026 source states 575; difference unresolved |
| Virginia directory | 11 | Table rows observed October 14 UTC; overlaps federal sources |
| North Carolina directory | 9 | Tribe headings observed October 14 UTC; Catawba statements differ |
| Canadian register groups | 634 | Administrative groups as of December 31, 2024, not 634 governments |
| Canadian First Nation Profiles search | 638 | Search records observed October 12 UTC; landing states 619, unresolved |
| Brazilian census categories | 391 | Named 2022 census leaf categories; not governments |

The US inclusion plan covers 50 state source-discovery scopes. Virginia and North Carolina inventories are preserved, with 48 other state scopes pending. This is a work tracker, not a completeness percentage. Four separate pending lanes cover communities outside recognition lists, Native Hawaiian peoples and communities, Alaska's distinct governments/peoples/villages/organizations, and cross-border or wider US-associated communities. Complete US and worldwide coverage have not been achieved.

There are 1,792 queue tasks after the October 15 source followups. Confirm the queue rather than treating this number as permanent. Canonical identity crosswalks in the two new state inventories remain unreviewed. Five own-site identity links were independently reviewed with AI assistance. No human review, urgent-risk finding or legal recognition adjudication was invented.

PR 14 passed 180 full-suite tests before a final UTC display correction; 56 focused tests passed afterward. Final deterministic build, font, copy, CSP, links, size, contrast, queue, release and game-data checks passed. Three independent AI review records and source receipts are committed in `data/nations/research/batches/2026-10-14-050645*`. They are AI reviews, not human or Nation approvals. Live Vercel status succeeded. Eight production resources matched reviewed bytes in the local publication receipt on October 14 UTC; Fresh browser visual confirmation remains pending because no browser is available in the permitted Computer Use app inventory. The earlier phone and desktop checks retain their original date.

## Website Files

- `index.html`: landing, hero, intro, Appearance, Fusion architecture, mission, footer and translation control.
- `download.html`: release state. The site is prerelease; no fabricated download availability.
- `nations.html`: generated Nations hub.
- `nations/`: generated profiles, countries, regions, source directory, coverage and resources.
- `static/`: self-hosted media, brand assets, fonts and public Nations data.
- `game/index.src.html`: readable game source. `game/build.py` produces `game/index.html`.
- `game/nations.json` and history shards: exported educational data, not a separate factual source.
- `vercel.json`: hosting and page-specific CSP. Inline script edits require synchronized hashes.
- `tools/nations/partials` and `tools/nations/templates`: generated Nations styling, behavior and markup sources. Do not hand edit generated profiles.
- `data/nations/nations.json`: canonical profile contract. Existing source, verification, respect and override workflow controls facts.
- `data/nations/research`: typed inventories, queue, source catalog, receipts, publication holds, inclusion plan and batch records.
- `data/nations/resources.json`, `context_links.json` and `sources/*.context.json`: bounded, source-reviewed public guides and contextual explanations.
- `.vercelignore`: excludes source research, tooling, docs and Markdown from visitor deployment.

Read `data/nations/DESIGN_NATIONS.md`, `architecture.md` and `research/README.md` before Nations changes. No Web AGENTS.md or CLAUDE.md was found in the latest repository scan; check again before writing.

## Visual Direction And Existing Preferences

Keep the open, infinite banners. Do not enclose them. The site favors deliberate space, fine open rules, clear hierarchy, upright whole Indigenous names and calm interaction. No em or en dashes in visible copy. Never alter a name to fit a typeface. Indigenous names must not be uppercased or italicized for decoration.

Appearance IDs remain stable:

| ID | User Approved Name | Direction |
| --- | --- | --- |
| default | Sovereign Skeleton | Silver structure with a deeper meaning of foundation and independent judgment |
| maya | Maya Radiance | Deep Maya blue, animated antique gold in Living mode |
| codex | Living Codex | Warm paper and clear reading contrast |
| skeleton | Obsidian Ember | Dark obsidian and deep ambient crimson |

Ambient red is deep and dark, not bright orange or primary red. Existing crimson tokens include #8B1934, #480D1B and #6E0F25 on paper. Maya uses deeper antique gold, bronze and champagne, including #B4873C, #9D6D31, #F1DFB4 and #CDA45E. Living mode has a slow gold sweep; Calm and Still use static equivalents. Preserve all four themes and real contrast. Select controls and their options need matching backgrounds and readable text, including phones.

No loud auto audio, compulsory movement, flashing, drag-only controls or motion needed to understand content. Keyboard, touch, reduced motion, captions/transcripts and static alternatives belong in the design. No external request on Nations pages until a visitor deliberately follows a source link. Translation's third-party service is opt-in.

The owner supplied the intro audio. Preserve `static/zotheos_intro.mp3`, SHA256 `3f0b3db8cccfff2b9c38808076aa30729e501cefc398522a25c5ec281b75aaa5`. The visual run is 8,400ms. The MP3 container measured 8.376 seconds and browser decode 8.338333 seconds in earlier checks; do not claim the encoded file is exactly 8.4 seconds. The owner rejected earlier synthesized intro sounds. Do not replace this audio or its approved branding without a clear new request.

## Games And Learning

The game is live at `/game`. Echo's concrete issues were addressed in earlier PRs: visible hoops, route labels and ball-through-ring scoring. Native Nations, living people, sacred figures and histories are not enemies, collectibles or score rewards. Fictional Stone Face is distinct. Add deeper facts and useful resource links through sourced educational cards, not stereotypes or invented traditions.

The minified engine had only five spare bytes under its size gate at the previous measured build. Re-measure before engine additions. Prefer separate bounded same-origin data or assets rather than silently raising limits. Mechanics changes need an actual issue plus gameplay and accessibility checks.

## Evidence And Removal Rules

Use Nations' own sources first, then Indigenous-led organizations, primary official records, court/UN material and authoritative directories. Fetch and read sources before drafting facts. Respect robots and rate limits, at least three seconds per source host, and source-specific crawl delays. Never use indexed snippets to turn an unread source into verified content. Do not bypass access blocks with alternate domains, proxies or stealth.

Retain actual source URLs, HTTP state/body SHA when measured, observed text, event date, publication date and actual check date as separate fields. Unknown means unknown. A generated animation or model output is not evidence. Government directories do not establish land title or exclusive representation.

Directory holds and canonical holds differ but must both be honored. Named inventory notes bind explicit directory IDs through `scoped_notes`; any held subject suppresses the whole note. Discrepancy links follow their subject's visibility. Composite named resources bind canonical IDs. Do not restore held content automatically. Existing human-only restoration and signing-key rules remain in force.

## Source Followups Prepared On October 15

Two bounded source subjects have been integrated locally and independently reviewed by an AI reviewer. They are pending publication checks at this handoff refresh, not described here as live additions.

1. Catawba NC statements: approved commission minutes establish a recognition motion in June 2026. The minutes are dated June 5; the DOA landing says June 6 without a year, and the older directory still describes a petition. Preserve the exact-day discrepancy and unknown legal effective date. Public supporting links identify the actual minutes and page references. The October 14 directory snapshot, nine observed headings and unreviewed identity crosswalks remain unchanged.
2. Chiricahua-identifying communities in Mexico: the freshly read INPI map contains one N'dee/N'nee/Ndé record in Chihuahua with type Sede, meaning a seat. It is not a territory boundary, complete community inventory or proof of a single contemporary government. The existing resource guide links that source and retains three distinct canonical subject bindings. A candidate own-site disallows automated crawling; its content is unread and not used for verified claims.

Directory rows now say Profile Link Pending with a clear explanation: an existing profile may still need a reviewed identity match. No canonical facts, legal recognition decisions or human approvals were added. Source receipts, queue updates and independent review retain their actual check dates and unresolved questions. Do not duplicate, overwrite or silently resolve these subjects. Current work artifacts are in the local steward-2026-10-15 folder attached to this task.

## Collaboration Status

The local Claude CLI returned an authentication error before producing a model response. The owner chose to paste this handoff into their already signed-in Claude Code session. Claude's tool inventory, availability on each workstation, critique and cinema proposal have not yet been received. Codex observed ffmpeg and ffprobe on the local PATH; this does not establish access to any AI cinema renderer. No generation or paid render has been commissioned.

## First Assignment For Claude Code

Please reply read only with:

1. Your actual station, available model identity and current repository context. State which tool availability is observed on this machine and which belongs only to Titan or another app.
2. An inventory of the AI cinema tools you can actually access in this session. For each: name, availability evidence, purpose, local versus remote, input/output formats, licensing/source constraints, and whether generation would spend credits or require approval. Never expose configuration secrets. Do not invoke a paid render or start generation in this inventory step.
3. Three ambitious but understandable visual opportunities for the website, ranked by user value. Include one signature ZOTHEOS motion explainer and one contribution to the Nations experience that preserves dignity and accessibility. Keep proposed work distinct from published functionality.
4. One concrete first production package: storyboard, scene meaning, exact source/claim boundaries, original asset plan, static/reduced-motion alternative, captions/transcript, mobile behavior, size/performance budget and tool chain. The supplied intro remains intact. Original abstract system graphics are acceptable; fabricated Indigenous documentary scenes, simulated testimonials, unconsented sacred imagery or copied franchise sound assets are not evidence or approved material.
5. An independent critique of the current website and these priorities. Retain disagreements verbatim, with reasons and an alternative. Do not flatter, agree automatically or invent measurements.
6. A small file ownership proposal for an isolated branch/checkout and acceptance criteria before build. Codex handles evidence integration and publication. Wait for assignment before editing the main working tree or changing services.

After the inventory, we can choose a bounded original motion prototype, review the result, then integrate and publish a verified contribution. If a renderer is unavailable, say so and provide a reproducible alternative. No giant speculative redesign and no claim that all Nations have been included.

## Verification Commands

Use the project's existing Python runtime, normally `py -3.10`. Keep `PYTHONDONTWRITEBYTECODE=1`. Core checks include:

```text
py -3.10 tools/nations_build.py
py -3.10 tools/nations_build.py --check
py -3.10 tools/nations_research.py validate
py -3.10 -m pytest tools/tests -q -p no:cacheprovider
py -3.10 tools/csp_sync.py --check
py -3.10 tools/lint_copy.py
py -3.10 tools/fonts_check.py
py -3.10 tools/game_nations.py --check
py -3.10 tools/release_switch.py --check
```

The build also gates names, links, sizes and contrast. Tests run in scratch copies. Do not broaden testing without new changes or concerns. Match checks to the work, record actual results and independently inspect browser behavior. A successful merge or deployment status does not establish the live bytes; verify the pages and assets on zotheos.org afterward.
