#!/usr/bin/env python3.10
"""ZOTHEOS nations assembler, round 2.

Reads, for every region present in the nations folder:
    <region>.raw.json      compiler output (data contract)
    <region>.verify.json   independent source check (results[], names[])
    <region>.respect.json  naming and respect review (items[])
plus any gap-*.raw/verify/respect.json files, and the assembler's decision file
tools/merge_overrides.json. Writes nations.json, nations.min.json and
tools/merge_log.json (every decision, with its reason).

Rules (fail loudly rather than guess):
  * a fact survives only if verify verdict is supported or fixed (fixed text,
    evidence and as_of are applied) and respect action is not remove;
  * every fact-level respect edit must have a decision in merge_overrides.json
    (respect / verified / drop); every nation-level respect edit must have an
    entry too, so no free-text instruction is silently skipped;
  * verify.names and respect.name corrections are applied; a conflict between
    them without an override is an error; a verify.names entry that says the
    cited name_source_url does not show the lead name (ok false) and offers no
    fix must be settled by a nations override (name or name_source_url);
  * region_map in the overrides renames workflow region keys (gap-*) to the
    published geographic key; a nations override may also set "region" for one
    nation; ARCHITECTURE 2.6: region keys are plain geography;
  * a nation with zero surviving facts is dropped;
  * nations are deduplicated across regions by id and by lead name + shared
    country, merging facts (the primary region file wins ties over a remapped
    gap file, then file order; deterministic);
  * every kept fact must carry source.url, source.publisher, source.accessed and
    evidence; any U+2014 or U+2013 anywhere in output is an error;
  * a superlative that is not in rank_allow or fact_drops is an error
    (ARCHITECTURE 9.1: never rank nations).

Usage: py -3.10 tools/merge.py [--dir NATIONS_DIR]
"""
from __future__ import annotations

import argparse
import copy
import glob
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter, OrderedDict, defaultdict

GENERATED = "2026-10-08"
VERSION = "1"
DASHES = ("—", "–")
KINDS = {"today", "language", "governance", "land", "culture", "history", "achievement", "population"}
RANK_RE = re.compile(
    r"(?i)\b(largest|biggest|most populous|most spoken|second[- ]largest|third[- ]largest|"
    r"more than any other|smallest|oldest|most powerful)\b"
)
STRUCTURED_NATION_KEYS = ("name", "also", "also_add", "pronounce", "patch", "lands", "official_url", "name_source_url")


class MergeError(Exception):
    pass


def fold(s: str) -> str:
    """Comparison key: casefold, strip diacritics, keep letters and digits."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^\w]+", " ", s.casefold()).strip()


def load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def find_regions(root: str) -> list[str]:
    regs = []
    for p in sorted(glob.glob(os.path.join(root, "*.raw.json"))):
        base = os.path.basename(p)[: -len(".raw.json")]
        if "prev-run" in base:
            continue
        regs.append(base)
    return regs


def dash_scan(obj, where: str, errors: list[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            dash_scan(v, f"{where}.{k}", errors)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            dash_scan(v, f"{where}[{i}]", errors)
    elif isinstance(obj, str) and any(d in obj for d in DASHES):
        errors.append(f"em/en dash at {where}: {obj[:100]!r}")


def dedupe_list(items: list[str], exclude: str = "") -> list[str]:
    seen, out = set(), []
    ex = fold(exclude) if exclude else None
    for x in items:
        k = fold(x)
        if not k or k in seen or k == ex:
            continue
        seen.add(k)
        out.append(x)
    return out


def apply_url_map(n: dict, url_map: dict) -> None:
    for key in ("official_url", "name_source_url"):
        if n.get(key) in url_map:
            n[key] = url_map[n[key]]
    if isinstance(n.get("pronounce"), dict) and n["pronounce"].get("source_url") in url_map:
        n["pronounce"]["source_url"] = url_map[n["pronounce"]["source_url"]]
    for f in n["facts"]:
        if f["source"].get("url") in url_map:
            f["source"]["url"] = url_map[f["source"]["url"]]


def fact_id(nation_id: str, f: dict) -> str:
    h = hashlib.sha1(f"{f['source']['url']}|{fold(f['evidence'])}".encode("utf-8")).hexdigest()[:8]
    return f"{nation_id}-{h}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    args = ap.parse_args()
    root = args.dir
    ov = load(os.path.join(root, "tools", "merge_overrides.json"))
    fact_edits = ov.get("fact_edits", {})
    fact_drops = ov.get("fact_drops", {})
    rank_allow = ov.get("rank_allow", {})
    nation_ov = ov.get("nations", {})
    url_map = ov.get("url_map", {})
    region_map = ov.get("region_map", {})

    errors: list[str] = []
    log = {
        "facts_dropped": [], "nations_dropped": [], "texts": Counter(), "verify": Counter(),
        "respect_fact": Counter(), "respect_nation": Counter(), "edit_decisions": Counter(),
        "name_changes": [], "merges": [], "used_overrides": set(), "per_region": {},
        "region_remaps": {}, "field_overrides": [],
    }
    regions = find_regions(root)
    if not regions:
        raise MergeError("no <region>.raw.json files found")

    built: list[dict] = []
    for reg in regions:
        raw = load(os.path.join(root, f"{reg}.raw.json"))
        ver = load(os.path.join(root, f"{reg}.verify.json"))
        res = load(os.path.join(root, f"{reg}.respect.json"))
        region_in = raw.get("region") or reg
        region_key = region_map.get(region_in, region_in)
        if region_key != region_in:
            log["region_remaps"][region_in] = region_key
        if region_key.startswith("gap-"):
            errors.append(f"{reg}: region key {region_key!r} is a workflow label, not geography; add it to region_map")
        base = int(ver.get("index_base", 0))
        vres = {}
        for x in ver["results"]:
            k = (x["id"], int(x["fact"]) - base)
            if k in vres:
                errors.append(f"{reg}: duplicate verify result {k}")
            vres[k] = x
        vnames = {x["id"]: x for x in ver.get("names", [])}
        rfact, rnat = {}, defaultdict(list)
        for x in res["items"]:
            if x.get("fact") is None:
                rnat[x["id"]].append(x)
            else:
                k = (x["id"], int(x["fact"]))
                if k in rfact:
                    errors.append(f"{reg}: duplicate respect item {k}")
                rfact[k] = x
        stats = Counter()
        for n0 in raw["nations"]:
            nid = n0["id"]
            n = copy.deepcopy(n0)
            nkey = f"{reg}|{nid}"
            stats["nations_in"] += 1
            # ---------- nation level ----------
            nat_items = rnat.get(nid, [])
            removed = any(i["action"] == "remove" for i in nat_items)
            for i in nat_items:
                log["respect_nation"][i["action"]] += 1
            if removed:
                why = "; ".join(i["reason"][:160] for i in nat_items if i["action"] == "remove")
                log["nations_dropped"].append({"region": reg, "id": nid, "name": n["name"], "reason": f"respect remove: {why}"})
                for i, f in enumerate(n["facts"]):
                    log["facts_dropped"].append({"key": f"{nkey}|{i}", "reason": "nation removed by respect review", "text": f["text"]})
                stats["nations_removed"] += 1
                continue
            vn = vnames.get(nid)
            new_name = None
            if vn is not None and not vn.get("ok", True) and vn.get("name"):
                new_name = ("verify", vn["name"])
            if vn is not None and not vn.get("ok", True) and not vn.get("name"):
                if not any(k in nation_ov.get(nkey, {}) for k in ("name", "name_source_url")):
                    errors.append(f"{nkey}: verifier could not confirm the lead name on name_source_url and offered no fix; "
                                  f"add a nations override with name or name_source_url")
            for i in nat_items:
                if i.get("name"):
                    if new_name and new_name[1] != i["name"] and "name" not in nation_ov.get(nkey, {}):
                        errors.append(f"{nkey}: verify name {new_name[1]!r} conflicts with respect name {i['name']!r}")
                    new_name = ("respect", i["name"])
            for i in nat_items:
                if i["action"] == "edit" and nkey not in nation_ov:
                    errors.append(f"{nkey}: nation-level respect edit has no entry in merge_overrides.json nations")
                if i.get("also") is not None:
                    n["also"] = list(i["also"])
                if i.get("also_add"):
                    n["also"] = list(n["also"]) + list(i["also_add"])
                if "pronounce" in i:
                    n["pronounce"] = i["pronounce"]
                for pk, pv in (i.get("patch") or {}).items():
                    n[pk] = pv
            o = nation_ov.get(nkey, {})
            if o:
                log["used_overrides"].add(("nation", nkey))
            if "name" in o:
                new_name = ("override", o["name"])
            also_given = "also" in o or any(
                i.get("also") is not None or "also" in (i.get("patch") or {}) for i in nat_items)
            if new_name and new_name[1] != n["name"]:
                log["name_changes"].append({"region": reg, "id": nid, "from": n["name"], "to": new_name[1], "by": new_name[0]})
                old = n["name"]
                n["name"] = new_name[1]
                if not also_given:
                    # keep the former lead name findable unless a reviewer set the list
                    n["also"] = [old] + list(n["also"])
            if "also" in o:
                n["also"] = list(o["also"])
            for rm in o.get("also_remove", []):
                before = len(n["also"])
                n["also"] = [a for a in n["also"] if a != rm]
                if len(n["also"]) == before:
                    errors.append(f"{nkey}: also_remove {rm!r} not present")
            if o.get("also_add"):
                n["also"] = list(n["also"]) + list(o["also_add"])
            for k in ("lands", "pronounce", "official_url", "name_source_url"):
                if k in o:
                    if n.get(k) != o[k]:
                        log["field_overrides"].append({"key": nkey, "field": k, "from": n.get(k), "to": o[k], "why": o.get("why", "")[:200]})
                    n[k] = o[k]
            search = list(o.get("also_search", []))
            n["also"] = dedupe_list(n["also"], exclude=n["name"])
            if search:
                n["also_search"] = dedupe_list(search, exclude=n["name"])
            if "new_id" in o:
                log["name_changes"].append({"region": reg, "id": nid, "id_to": o["new_id"], "by": "override"})
                n["id"] = o["new_id"]
            # ---------- fact level ----------
            kept = []
            for i, f0 in enumerate(n0["facts"]):
                key = f"{nkey}|{i}"
                v = vres.get((nid, i))
                r = rfact.get((nid, i))
                if v is None or r is None:
                    errors.append(f"{key}: missing {'verify' if v is None else 'respect'} entry")
                    continue
                log["verify"][v["verdict"]] += 1
                log["respect_fact"][r["action"]] += 1
                if v["verdict"] not in ("supported", "fixed"):
                    log["facts_dropped"].append({"key": key, "reason": f"verify: {v['verdict']}", "note": v.get("note", "")[:300], "text": f0["text"]})
                    continue
                f = copy.deepcopy(f0)
                src = "raw"
                if v["verdict"] == "fixed":
                    if v.get("text"):
                        f["text"] = v["text"]
                        src = "verifier"
                    if v.get("evidence"):
                        f["evidence"] = v["evidence"]
                    if "as_of" in v:
                        f["as_of"] = v["as_of"]
                if r["action"] == "remove":
                    log["facts_dropped"].append({"key": key, "reason": "respect: remove", "note": r.get("reason", "")[:300], "text": f["text"]})
                    continue
                if r["action"] == "edit":
                    d = fact_edits.get(key)
                    if d is None:
                        errors.append(f"{key}: respect edit has no decision in merge_overrides.json fact_edits")
                        continue
                    log["used_overrides"].add(("fact", key))
                    log["edit_decisions"][d["use"]] += 1
                    if d["use"] == "drop":
                        log["facts_dropped"].append({"key": key, "reason": f"respect edit unresolved: {d['why']}", "text": f["text"], "respect_text": r.get("text")})
                        continue
                    if d["use"] == "respect":
                        if not r.get("text"):
                            errors.append(f"{key}: decision 'respect' but respect item has no text")
                            continue
                        f["text"] = r["text"]
                        src = "respect"
                    elif d["use"] != "verified":
                        errors.append(f"{key}: unknown decision {d['use']!r}")
                        continue
                    if "as_of" in d:
                        f["as_of"] = d["as_of"]
                elif r["action"] != "keep":
                    errors.append(f"{key}: unknown respect action {r['action']!r}")
                    continue
                if key in fact_drops:
                    log["used_overrides"].add(("drop", key))
                    log["facts_dropped"].append({"key": key, "reason": f"assembler: {fact_drops[key]}", "text": f["text"]})
                    continue
                if RANK_RE.search(f["text"]):
                    if key in rank_allow:
                        log["used_overrides"].add(("rank", key))
                    else:
                        errors.append(f"{key}: superlative needs a rank_allow or fact_drops decision: {f['text']!r}")
                        continue
                s = f.get("source") or {}
                missing = [k for k in ("url", "publisher", "accessed") if not s.get(k)] + ([] if f.get("evidence") else ["evidence"])
                if missing:
                    log["facts_dropped"].append({"key": key, "reason": f"missing {', '.join(missing)}", "text": f["text"]})
                    continue
                if any(dd in f["text"] or dd in f["evidence"] for dd in DASHES):
                    errors.append(f"{key}: em/en dash in fact text or evidence; fix the source file, do not auto-replace")
                    continue
                if len(f["text"]) > 200:
                    errors.append(f"{key}: fact text {len(f['text'])} chars (max 200)")
                    continue
                if f.get("kind") not in KINDS:
                    errors.append(f"{key}: bad kind {f.get('kind')!r}")
                    continue
                log["texts"][src] += 1
                out = OrderedDict()
                out["text"] = f["text"]
                out["kind"] = f["kind"]
                out["as_of"] = None if f.get("as_of") in (None, "") else str(f["as_of"])
                out["source"] = OrderedDict((k, s[k]) for k in ("title", "publisher", "url", "accessed") if k in s)
                out["evidence"] = f["evidence"]
                out["status"] = "verified"
                out["checked"] = ver.get("checked") or GENERATED
                out["_key"] = key
                kept.append(out)
            n["facts"] = kept
            n["_region"] = o.get("region", region_key)
            if n["_region"] != region_key:
                log["field_overrides"].append({"key": nkey, "field": "region", "from": region_key, "to": n["_region"], "why": o.get("why", "")[:200]})
            # dedupe tiebreak: the primary region file wins over a remapped gap file, then file order
            n["_prio"] = 0 if region_in == region_key else 1
            n["_order"] = len(built)
            n["_src_keys"] = [nkey]
            apply_url_map(n, url_map)
            if not kept:
                log["nations_dropped"].append({"region": reg, "id": nid, "name": n["name"], "reason": "zero surviving facts"})
                stats["nations_zero"] += 1
                continue
            built.append(n)
            stats["nations_kept"] += 1
        log["per_region"][reg] = dict(stats)

    # ---------- unused overrides (stale decisions are errors) ----------
    for k in fact_edits:
        if ("fact", k) not in log["used_overrides"]:
            errors.append(f"fact_edits entry not used: {k}")
    for k in fact_drops:
        if ("drop", k) not in log["used_overrides"]:
            already = any(d["key"] == k for d in log["facts_dropped"])
            if not already:
                errors.append(f"fact_drops entry not used: {k}")
    for k in rank_allow:
        if ("rank", k) not in log["used_overrides"]:
            errors.append(f"rank_allow entry not used: {k}")
    for k in nation_ov:
        if ("nation", k) not in log["used_overrides"]:
            if not any(d["region"] + "|" + d["id"] == k for d in log["nations_dropped"]):
                errors.append(f"nations override not used: {k}")

    # ---------- dedupe across regions ----------
    final: list[dict] = []
    by_id: dict[str, dict] = {}
    by_name: dict[tuple[str, str], dict] = {}
    for n in sorted(built, key=lambda x: (x["_region"], fold(x["name"]), x["_prio"], x["_order"])):
        target = by_id.get(n["id"])
        if target is None:
            for c in n["countries"]:
                t = by_name.get((fold(n["name"]), c))
                if t is not None:
                    target = t
                    break
        if target is not None:
            log["merges"].append({"into": target["id"], "into_file": target["_src_keys"][0], "from": n["id"], "from_file": n["_src_keys"][0],
                                  "region": target["_region"], "name": n["name"], "facts_added": 0})
            target["also"] = dedupe_list(target["also"] + n["also"], exclude=target["name"])
            if n.get("also_search"):
                target["also_search"] = dedupe_list(target.get("also_search", []) + n["also_search"], exclude=target["name"])
            for c in n["countries"]:
                if c not in target["countries"]:
                    target["countries"].append(c)
            seen = {(f["source"]["url"], fold(f["evidence"])) for f in target["facts"]}
            for f in n["facts"]:
                k = (f["source"]["url"], fold(f["evidence"]))
                if k not in seen:
                    target["facts"].append(f)
                    seen.add(k)
                    log["merges"][-1]["facts_added"] += 1
            target["_src_keys"] += n["_src_keys"]
            continue
        by_id[n["id"]] = n
        for c in n["countries"]:
            by_name.setdefault((fold(n["name"]), c), n)
        final.append(n)

    # ---------- shape output ----------
    nations_out = []
    fact_ids = set()
    for n in final:
        o = OrderedDict()
        o["id"] = n["id"]
        o["region"] = n["_region"]
        o["name"] = n["name"]
        o["also"] = n["also"]
        if n.get("also_search"):
            o["also_search"] = n["also_search"]
        o["pronounce"] = n.get("pronounce")
        o["lands"] = n["lands"]
        o["countries"] = n["countries"]
        o["official_url"] = n.get("official_url")
        o["name_source_url"] = n["name_source_url"]
        facts = []
        for f in n["facts"]:
            f = OrderedDict(f)
            f.pop("_key", None)
            fid = fact_id(n["id"], f)
            if fid in fact_ids:
                errors.append(f"duplicate fact id {fid}")
            fact_ids.add(fid)
            ff = OrderedDict([("id", fid)])
            ff.update(f)
            facts.append(ff)
        o["facts"] = facts
        nations_out.append(o)
    ids = Counter(n["id"] for n in nations_out)
    for k, c in ids.items():
        if c > 1:
            errors.append(f"duplicate nation id {k}")
    region_counts = OrderedDict(sorted(Counter(n["region"] for n in nations_out).items()))
    doc = OrderedDict()
    doc["version"] = VERSION
    doc["generated"] = GENERATED
    doc["count"] = len(nations_out)
    doc["facts"] = sum(len(n["facts"]) for n in nations_out)
    doc["regions"] = region_counts
    doc["nations"] = nations_out
    dash_scan(doc, "nations.json", errors)

    if errors:
        print(f"MERGE FAILED with {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        return 2

    with open(os.path.join(root, "nations.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(root, "nations.min.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))

    log_out = {
        "generated": GENERATED,
        "regions_read": regions,
        "per_region": log["per_region"],
        "verify_verdicts": dict(log["verify"]),
        "respect_fact_actions": dict(log["respect_fact"]),
        "respect_nation_actions": dict(log["respect_nation"]),
        "edit_decisions": dict(log["edit_decisions"]),
        "text_source": dict(log["texts"]),
        "region_remaps": log["region_remaps"],
        "field_overrides": log["field_overrides"],
        "name_changes": log["name_changes"],
        "merges": log["merges"],
        "nations_dropped": log["nations_dropped"],
        "facts_dropped": log["facts_dropped"],
        "totals": {"nations": doc["count"], "facts": doc["facts"], "regions": region_counts,
                   "facts_by_region": OrderedDict(sorted(Counter(n["region"] for n in nations_out for _ in n["facts"]).items()))},
    }
    with open(os.path.join(root, "tools", "merge_log.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(log_out, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"OK: {doc['count']} nations, {doc['facts']} facts, {len(region_counts)} regions; "
          f"dropped {len(log['nations_dropped'])} nations and {len(log['facts_dropped'])} facts; "
          f"merged {len(log['merges'])} duplicate(s).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except MergeError as exc:
        print(f"MERGE FAILED: {exc}", file=sys.stderr)
        sys.exit(2)
