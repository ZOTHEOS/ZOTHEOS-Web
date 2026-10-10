#!/usr/bin/env python3.10
"""Validate nations.json (and that nations.min.json carries the same data).

Errors (exit 1): schema and types, em/en dashes in any string, fact text over 200
characters, evidence outside 4 to 12 words, non-https or Wikipedia URLs, bad ISO
country codes, bad kinds, dates or as_of, duplicate nation or fact ids, count
mismatches, banned terms from ARCHITECTURE 9.1.
Warnings: superlatives (ranking review), a capitalized two-word name pattern in
Australian facts (deceased-persons review), unknown keys, numbers without as_of.

Usage: py -3.10 tools/validate.py [path/to/nations.json]
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter

ISO2 = set("""AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY
BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA
GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG
KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW
MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD
SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA
VC VE VG VI VN VU WF WS YE YT ZA ZM ZW""".split())
KINDS = {"today", "language", "governance", "land", "culture", "history", "achievement", "population"}
STATUSES = {"verified", "stale", "unreachable"}
TOP_KEYS = {"version", "generated", "count", "facts", "regions", "nations"}
NATION_KEYS = {"id", "region", "name", "also", "also_search", "pronounce", "lands", "countries", "official_url",
               "name_source_url", "facts"}
FACT_KEYS = {"id", "text", "kind", "as_of", "source", "evidence", "status", "checked"}
SOURCE_KEYS = {"title", "publisher", "url", "accessed"}
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FACT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-[0-9a-f]{8}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
YEAR_RE = re.compile(r"^\d{4}$")
BANNED = re.compile(r"(?i)\b(extinct|vanished|last of the|disappeared|primitive|savages?|noble savage|spirit animal|"
                    r"legend says|blood quantum|full[- ]blood(?:ed)?|half[- ]breed)\b")
RANK = re.compile(r"(?i)\b(largest|biggest|most populous|most spoken|second[- ]largest|third[- ]largest|"
                  r"more than any other|smallest|oldest|most powerful)\b")
PERSON = re.compile(r"\b[A-Z][a-z]+ (?:[A-Z][a-z]+ )?[A-Z][a-z]{2,}\b")


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(here), "nations.json")
    errors: list[str] = []
    warns: list[str] = []
    raw_text = open(path, encoding="utf-8").read()
    for ch, nm in (("—", "em dash"), ("–", "en dash")):
        if ch in raw_text:
            errors.append(f"{nm} present in file ({raw_text.count(ch)}x)")
    doc = json.loads(raw_text)

    def url_ok(u, where, nullable=False):
        if u is None:
            if not nullable:
                errors.append(f"{where}: URL is null")
            return
        if not isinstance(u, str) or not u.startswith("https://"):
            errors.append(f"{where}: URL not https: {u!r}")
        elif "wikipedia.org" in u.lower():
            errors.append(f"{where}: Wikipedia cited: {u}")
        elif " " in u:
            errors.append(f"{where}: URL has a space")

    def text_ok(s, where, maxlen=None):
        if not isinstance(s, str) or not s.strip():
            errors.append(f"{where}: empty or not a string")
            return False
        if s != s.strip():
            warns.append(f"{where}: leading/trailing whitespace")
        if maxlen and len(s) > maxlen:
            errors.append(f"{where}: {len(s)} chars (max {maxlen})")
        return True

    if set(doc) != TOP_KEYS:
        errors.append(f"top-level keys {sorted(doc)} != {sorted(TOP_KEYS)}")
    if doc.get("version") != "1":
        errors.append("version must be '1'")
    if not DATE_RE.match(str(doc.get("generated", ""))):
        errors.append("generated must be YYYY-MM-DD")
    nations = doc.get("nations", [])
    if doc.get("count") != len(nations):
        errors.append(f"count {doc.get('count')} != {len(nations)}")
    nfacts = sum(len(n.get("facts", [])) for n in nations)
    if doc.get("facts") != nfacts:
        errors.append(f"facts {doc.get('facts')} != {nfacts}")
    rc = Counter(n.get("region") for n in nations)
    if dict(rc) != doc.get("regions"):
        errors.append(f"regions counts mismatch: {doc.get('regions')} vs {dict(rc)}")
    order = [(n.get("region", ""), n.get("name", "").casefold()) for n in nations]
    regions_seen = [r for r, _ in order]
    if regions_seen != sorted(regions_seen):
        errors.append("nations not sorted by region")

    nids, fids, name_country = Counter(), Counter(), Counter()
    for ni, n in enumerate(nations):
        w = f"nations[{ni}]({n.get('id')})"
        extra = set(n) - NATION_KEYS
        missing = (NATION_KEYS - {"also_search"}) - set(n)
        if missing:
            errors.append(f"{w}: missing keys {sorted(missing)}")
        if extra:
            warns.append(f"{w}: unknown keys {sorted(extra)}")
        nid = n.get("id", "")
        nids[nid] += 1
        if not ID_RE.match(nid or ""):
            errors.append(f"{w}: id not ascii kebab")
        text_ok(n.get("region"), f"{w}.region")
        text_ok(n.get("name"), f"{w}.name", 120)
        text_ok(n.get("lands"), f"{w}.lands", 300)
        for key in ("also", "also_search"):
            if key in n:
                if not isinstance(n[key], list) or not all(isinstance(a, str) and a.strip() for a in n[key]):
                    errors.append(f"{w}.{key}: must be a list of non-empty strings")
                elif n.get("name") in n[key]:
                    warns.append(f"{w}.{key}: repeats the lead name")
        pr = n.get("pronounce")
        if pr is not None:
            if not isinstance(pr, dict) or set(pr) != {"text", "source_url"}:
                errors.append(f"{w}.pronounce: must be null or {{text, source_url}}")
            else:
                text_ok(pr["text"], f"{w}.pronounce.text", 160)
                url_ok(pr["source_url"], f"{w}.pronounce.source_url")
        cs = n.get("countries")
        if not isinstance(cs, list) or not cs:
            errors.append(f"{w}.countries: empty")
        else:
            for c in cs:
                if c not in ISO2:
                    errors.append(f"{w}.countries: bad ISO code {c!r}")
                name_country[(str(n.get("name", "")).casefold(), c)] += 1
            if len(set(cs)) != len(cs):
                errors.append(f"{w}.countries: duplicates")
        url_ok(n.get("official_url"), f"{w}.official_url", nullable=True)
        url_ok(n.get("name_source_url"), f"{w}.name_source_url")
        facts = n.get("facts")
        if not isinstance(facts, list) or not facts:
            errors.append(f"{w}: no facts")
            continue
        for fi, f in enumerate(facts):
            fw = f"{w}.facts[{fi}]"
            fextra, fmissing = set(f) - FACT_KEYS, FACT_KEYS - set(f)
            if fmissing:
                errors.append(f"{fw}: missing keys {sorted(fmissing)}")
            if fextra:
                warns.append(f"{fw}: unknown keys {sorted(fextra)}")
            fid = f.get("id", "")
            fids[fid] += 1
            if not FACT_ID_RE.match(fid or "") or not fid.startswith(nid + "-"):
                errors.append(f"{fw}: bad fact id {fid!r}")
            t = f.get("text", "")
            if text_ok(t, f"{fw}.text", 200):
                if BANNED.search(t):
                    errors.append(f"{fw}: banned term ({BANNED.search(t).group(0)}): {t}")
                if RANK.search(t):
                    warns.append(f"{fw}: superlative ({RANK.search(t).group(0)}), confirm it does not rank peoples: {t}")
                if "AU" in (cs or []) and PERSON.search(t):
                    warns.append(f"{fw}: AU fact with a name-like pattern ({PERSON.search(t).group(0)}), check for deceased persons")
                if re.search(r"\d[\d,.]*\s*(%|percent|people|members|speakers)", t) and f.get("as_of") is None:
                    warns.append(f"{fw}: number without as_of: {t}")
            if f.get("kind") not in KINDS:
                errors.append(f"{fw}: bad kind {f.get('kind')!r}")
            a = f.get("as_of")
            if a is not None and not (isinstance(a, str) and YEAR_RE.match(a)):
                errors.append(f"{fw}: as_of must be null or a 4-digit year string, got {a!r}")
            s = f.get("source")
            if not isinstance(s, dict) or set(s) != SOURCE_KEYS:
                errors.append(f"{fw}.source: keys must be {sorted(SOURCE_KEYS)}")
            else:
                text_ok(s["title"], f"{fw}.source.title")
                text_ok(s["publisher"], f"{fw}.source.publisher")
                url_ok(s["url"], f"{fw}.source.url")
                if not DATE_RE.match(str(s["accessed"])):
                    errors.append(f"{fw}.source.accessed: not YYYY-MM-DD")
            ev = f.get("evidence", "")
            if text_ok(ev, f"{fw}.evidence"):
                wc = len(ev.split())
                if not 4 <= wc <= 12:
                    errors.append(f"{fw}.evidence: {wc} words (must be 4 to 12)")
            if f.get("status") not in STATUSES:
                errors.append(f"{fw}: bad status {f.get('status')!r}")
            if not DATE_RE.match(str(f.get("checked", ""))):
                errors.append(f"{fw}: checked not YYYY-MM-DD")

    for k, c in nids.items():
        if c > 1:
            errors.append(f"duplicate nation id {k} ({c}x)")
    for k, c in fids.items():
        if c > 1:
            errors.append(f"duplicate fact id {k} ({c}x)")
    for (nm, c), k in name_country.items():
        if k > 1:
            warns.append(f"two nations named {nm!r} in {c}")

    mini = os.path.join(os.path.dirname(path), "nations.min.json")
    if os.path.exists(mini):
        with open(mini, encoding="utf-8") as fh:
            if json.load(fh) != doc:
                errors.append("nations.min.json does not match nations.json")
    else:
        warns.append("nations.min.json missing")

    print(f"validate: {len(nations)} nations, {nfacts} facts, {len(rc)} regions")
    for w_ in warns:
        print("  WARN  " + w_)
    for e in errors:
        print("  ERROR " + e)
    print(f"result: {'FAIL' if errors else 'PASS'} ({len(errors)} errors, {len(warns)} warnings)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
