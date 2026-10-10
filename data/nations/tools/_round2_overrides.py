"""Round 2: add the gap-* decisions to merge_overrides.json (round-1 entries untouched).

Run once: py -3.10 tools/_round2_overrides.py
Every entry carries its reason; merge.py fails loudly on any unused or missing decision.
"""
import json
import os
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "merge_overrides.json")

with open(PATH, encoding="utf-8") as fh:
    ov = json.load(fh, object_pairs_hook=OrderedDict)

ov["_doc"] = [d for d in ov["_doc"] if not d.startswith("Round 2")] + [
    "Round 2 (2026-10-10): gap-africa, gap-caribbean-guianas, gap-pacific, gap-south-asia folded in. "
    "region_map renames the workflow keys gap-* to published geographic keys (ARCHITECTURE 2.6); a nations entry may set "
    "'region' for one nation. Four gap-africa lead names were flagged by the verifier as not shown on the cited name source: "
    "where a citable page fetched by the assembler shows the endonym it stays (Ishelhiyen, Britannica); otherwise the lead "
    "falls back to the exonym the cited page does show and the endonym is kept first in also, to be promoted when a source "
    "is found (Kabyles, Mozabite, Siwans). Sources: Wikipedia and Wikipedia imports (museum-digital actor text) were not used.",
]

ov["region_map"] = OrderedDict([
    ("gap-africa", "africa"),
    ("gap-pacific", "oceania"),
    ("gap-south-asia", "asia"),
    ("gap-caribbean-guianas", "caribbean-guianas"),
])

R2_FACT_EDITS = OrderedDict([
    ("gap-africa|benet-uganda|2", {"use": "respect", "why": "Removes the word 'raids' and spells out UWA; a removal, no claim added; the IWGIA evidence phrase still supports the text."}),
    ("gap-africa|haiom-namibia|2", {"use": "respect", "why": "Spelling normalised to the community's own form Hai//om inside one fact; no claim changed."}),
    ("gap-africa|korana-south-africa|0", {"use": "respect", "why": "Tense only. The SAHO page gives the self-name in past habitual ('would refer to themselves'); a people's own name is a standing statement, and fact 1 shows living Korana communities. No new claim."}),
    ("gap-africa|iqbayliyen-kabyles-algeria|0", {"use": "verified", "why": "This round the lead name falls back to Kabyles (no fetchable source shows Iqbayliyen: Inalco EN/FR, IWGIA 2024, CNRS pages 403, museum-digital text is a Wikipedia import). The respect text would put an unverified name into a fact; keep the verified text, which already matches the lead. Round 3: promote the endonym with a source."}),
    ("gap-africa|toubou-chad-libya-niger|0", {"use": "respect", "why": "Drops 'of Chad' after Tibesti on a contested belonging question; a removal. IWGIA still says 'originally from the Tibesti plateau'."}),
    ("gap-africa|samburu-kenya|1", {"use": "respect", "why": "Removes the literacy aside; the UNEP evidence phrase (constitutional rights, views to government) covers the whole remaining text."}),
    ("gap-africa|mbuti-drc|1", {"use": "respect", "why": "Reframed on the evidence phrase itself. Verifier quote of the WHC page: 'The primary management challenges ... are ... ensuring of the involvement of the indigenous populations, Mbuti and Efe pygmies, in the management of the Reserve.' 'Calls for ensuring the involvement ... in the management' restates that listed need without framing the peoples as the challenge; no claim beyond the quoted sentence."}),
    ("gap-caribbean-guianas|warao-orinoco-guyana-trinidad|1", {"use": "respect", "why": "Assembler fetch 2026-10-10: the Guyana Ministry page heads the entry 'WARRAUS'; naming the Guyanese spelling bridges to the lead name Warao. 'Wetlands' was already in the verified text; nothing added."}),
    ("gap-caribbean-guianas|tareno-trio-suriname-brazil|0", {"use": "respect", "why": "Reorders to the self-name first; every clause unchanged and verifier-confirmed on the ISA page."}),
    ("gap-pacific|i-kiribati-ki|0", {"use": "respect", "why": "Assembler extracted the Shima PDF (pypdf) 2026-10-10: 'an unimwane, a senior man in the village'. The gloss 'the senior men' is inside the cited text."}),
    ("gap-pacific|yapese-fm|2", {"use": "respect", "why": "Verifier and assembler fetch (2026-10-10) both confirm the two page sentences: 'The Yapese were seafaring people who sailed vast distances over the Pacific.' and 'Even in recent times, canoes from Yap have sailed to the Marianas, Okinawa, and Palau.' The continuity wording stays inside the page; 'across the Pacific' is the page's 'over the Pacific'."}),
    ("gap-pacific|nauruans-nr|1", {"use": "respect", "why": "The census report itself says the 12 clans or tribes 'are represented' in the flag star (verifier quote); present tense is the page's own."}),
    ("gap-south-asia|in-bhil|0", {"use": "respect", "why": "Credit where due. IGNCA page (verifier quote and assembler fetch 2026-10-10): 'Bhuri Bai of Pitol was the first Bhil artist to use paper and canvas for her painting'; 'Bhuri Bai now works as an artist in the Adivasi Lok Kala Academy in Bhopal'. Living artist named by a national cultural institution; the deceased-persons rule (AU) does not apply. First named individual in the set, deliberate."}),
    ("gap-south-asia|in-bhil|1", {"use": "respect", "why": "Same credit reason; subjects limited to the page's list (assembler fetch: 'attire, ornaments and gudna (tattoos), huts and granaries, the haat, festivals and dances and oral narratives'); 'the haat market' glosses haat."}),
    ("gap-south-asia|in-ho|1", {"use": "respect", "why": "Removes the creator clause (a removal); 'recently devised left-to-right alphabet' is on the Unicode chapter page (assembler fetch 2026-10-10); the two-publications clause is verifier-confirmed in 13.9."}),
    ("gap-south-asia|np-tamu|2", {"use": "respect", "why": "Gurung as the Tamu language is the entry's own verified naming (verify.names: NFDIN 'Gurung(Tamu)', body Tamu Hyul Chhonj Dhin Gurung Rashtriya Parishad); no new claim."}),
])
for k, v in R2_FACT_EDITS.items():
    ov["fact_edits"][k] = v

R2_NATIONS = OrderedDict([
    ("gap-africa|siwans-egypt", {
        "name": "Siwans",
        "also_add": ["Isiwan", "Siwan", "Siwi"],
        "why": "Respect asked for the self-name Isiwan but gave the fallback itself: no fetchable page shows Isiwan (CNRS page: 'Berbers, Siwans and Egyptians' only; Endangered Languages Project and Minority Rights Group 403; the rest is Wikipedia). Lead stays Siwans; Isiwan first in also. Round 3: promote with a source.",
    }),
    ("gap-africa|ishelhin-morocco", {
        "name": "Ishelhiyen",
        "also": ["Ishelhin", "Chleuh", "Shluh", "Shilha"],
        "name_source_url": "https://www.britannica.com/topic/Ishelhiyen",
        "why": "verify.names: the Inalco page shows only 'Chleuh'. Encyclopaedia Britannica headword 'Ishelhiyen' ('Also known as: Chleuh, Shluh'), fetched 2026-10-10 with the project user agent (HTTP 200). The compiler's spelling Ishelhin stays first in also; id unchanged (ids are stable).",
    }),
    ("gap-africa|iqbayliyen-kabyles-algeria", {
        "name": "Kabyles",
        "also": ["Iqbayliyen", "Kabyle"],
        "name_source_url": "https://www.inalco.fr/langues/kabyle-berbere",
        "why": "verify.names: no fetchable page shows Iqbayliyen (Inalco EN 'Kabyle (taqbaylit, Algeria)', Inalco FR 'Les Kabyles', IWGIA 2024 'Kabyle/Kabyls', CNRS LGIDF 403; museum-digital text is a Wikipedia import). Inalco FR page fetched 2026-10-10 shows 'Les Kabyles'. Endonym kept first in also; promote when a source is found.",
    }),
    ("gap-africa|irifiyen-morocco", {
        "name": "Rifians",
        "also": ["Irifiyen", "Riffians", "Rif"],
        "name_source_url": "https://static1.squarespace.com/static/6515b87f2af0cc4746f62fbc/t/65aaef8b85646b6267c70641/1705701259628/09-RamirezA-Fall2023.pdf",
        "why": "verify.names: the HCP census PDF names only the language Tarifit. No fetchable page shows Irifiyen (Britannica 'Rif' page and Cambridge excerpt unreachable; HAL, Persee and Encyclopedie berbere results use Rifains). Ramirez Rodriguez, 'The Official Archaeological Perspective in Morocco and the Rif Heritage', Tamazgha Studies Journal vol. 1 (2023), fetched 2026-10-10 and text-extracted, uses 'the Rifians' for the people; the journal URL (tamazghastudiesjournal.org/s/09-RamirezA-Fall2023.pdf) 302s to this file, so the file read is cited. Endonym kept first in also; promote when a source is found.",
    }),
    ("gap-africa|at-mzab-algeria", {
        "name": "Mozabite",
        "also": ["At Mzab", "Ath Mzab", "Mozabites"],
        "why": "verify.names: the UNESCO page (read by the verifier in the browser; 403 to fetch tools) uses 'Mozabite'; no fetchable page shows At Mzab (Persee shows only a 1986 book title 'At-Mzab'). Lead takes the page's exact token; endonym kept first in also.",
    }),
    ("gap-caribbean-guianas|bari-catatumbo-co-ve", {
        "also_remove": ["Motilones"],
        "why": "Respect: bare 'Motilones' is a colonial-era exonym applied to Bari and Yukpa alike; 'Motilon Bari' stays (official Colombian use).",
    }),
    ("gap-caribbean-guianas|xinka-southeast-guatemala", {
        "region": "central-america-caribbean",
        "why": "Geography: south-eastern Guatemala belongs with the existing Central America region, not the Caribbean and Guianas key.",
    }),
    ("gap-caribbean-guianas|chorti-maya-guatemala-honduras", {
        "region": "central-america-caribbean",
        "why": "Geography: Guatemala and Honduras belong with the existing Central America region.",
    }),
    ("oceania|kanak-nc", {
        "lands": "New Caledonia, including Grande Terre and the Loyalty Islands",
        "official_url": None,
        "why": "Round 1 (kept): contested name left out of a plain-fact field. Round 2: the Senat coutumier site refused connections on 2026-10-10 (verifier: WebFetch, curl https and http, browser pane; assembler: ECONNREFUSED). No dead link on a live card; restore https://www.senat-coutumier.nc/ when it answers.",
    }),
])
for k, v in R2_NATIONS.items():
    # merge into an existing round-1 entry rather than replace it (oceania|kanak-nc keeps its lands override)
    ov["nations"].setdefault(k, OrderedDict()).update(v)

with open(PATH, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(ov, fh, ensure_ascii=False, indent=2)
    fh.write("\n")
print("overrides updated:", len(ov["fact_edits"]), "fact_edits,", len(ov["nations"]), "nations,", len(ov["region_map"]), "region_map")
