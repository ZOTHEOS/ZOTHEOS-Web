"""Build the game's quick cards and optional history from the canonical published nations view.

Usage: py -3.10 tools/game_nations.py [--check]
The quick file retains two facts per nation. History is a separate, bounded payload, with no new claims.
"""
import argparse
import hashlib
import json
import math
import os
import re

from nations_lib import Model

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = ["today", "governance", "language", "land", "achievement", "population", "culture", "history"]
LIMIT = 512 * 1024 - 8 * 1024
HISTORY_LIMIT = 256 * 1024
NAME_LIMIT = 120
LANDS_LIMIT = 300
POOL_LIMIT = 600


def clip(s, n):
    return s if s is None or len(s) <= n else None


def fact_record(fact, raw_fact, *, full=False):
    """Keep source access separate from the canonical displayed checking receipt."""
    source = raw_fact["source"]
    out = {
        "text": fact["text"], "kind": fact["kind"], "as_of": fact.get("as_of"),
        "source": {"title": source["title"] if full else clip(source.get("title"), 200),
                   "publisher": source["publisher"], "url": source["url"], "accessed": source["accessed"]},
        "checked": fact["date"], "state": fact["state"],
    }
    if full:
        out["id"] = fact["id"]
    if fact.get("note"):
        # In the published model this is the date of the unsuccessful reachability check.
        out["note"] = fact["note"]
    return out


def encode(doc, limit, label):
    text = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    if "\u2014" in text or "\u2013" in text:
        raise ValueError("dash in " + label)
    size = len(text.encode("utf-8"))
    if size >= limit:
        raise ValueError("%s is %d UTF-8 bytes, over its %d-byte budget" % (label, size, limit))
    return text


def partition(doc, limit, kind):
    """Legacy output when it fits; otherwise lossless bounded content-addressed shards.

    Pool manifests contain [filename, count]. History manifests add the inclusive
    last nation ID, creating a compact ordered index without duplicating every ID.
    A manifest is never itself sharded: clients follow at most one manifest hop.
    """
    rows = doc['nations']
    full = json.dumps(doc, ensure_ascii=False, separators=(',', ':'))
    if len(full.encode('utf-8')) < limit and len(rows) <= POOL_LIMIT:
        return full, {}
    shell = {k: v for k, v in doc.items() if k != 'nations'}
    empty = dict(shell, nations=[] if kind == 'n' else {})
    overhead = len(json.dumps(empty, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    items = [(n['id'], n) for n in rows] if kind == 'n' else sorted(rows.items())
    sizes = {}
    for nid, row in items:
        text = json.dumps(row if kind == 'n' else {nid: row}, ensure_ascii=False, separators=(',', ':'))
        sizes[nid] = len(text.encode('utf-8')) + 1
        if sizes[nid] + overhead >= limit:
            raise ValueError('one %s record exceeds the shard byte budget: %s' % (kind, nid))
    if kind == 'n':
        # Deal each region across comparable pools, instead of leaving a tiny final
        # pool or putting all less-represented regions into the first byte chunk.
        regions = {}
        for item in items:
            regions.setdefault(item[1]['region'], []).append(item)
        order = [item for region in sorted(regions, key=lambda r: (-len(regions[r]), r))
                 for item in sorted(regions[region], key=lambda p: hashlib.sha256(p[0].encode()).digest())]
        count = max(2, math.ceil(len(items) / POOL_LIMIT), math.ceil(sum(sizes.values()) / (limit - overhead)))
        while True:
            groups, weights, by_region = [[] for _ in range(count)], [overhead] * count, [{} for _ in range(count)]
            for nid, row in order:
                available = [i for i in range(count) if len(groups[i]) < POOL_LIMIT and weights[i] + sizes[nid] < limit]
                if not available:
                    break
                i = min(available, key=lambda i: (by_region[i].get(row['region'], 0), len(groups[i]), weights[i], i))
                groups[i].append((nid, row))
                weights[i] += sizes[nid]
                by_region[i][row['region']] = by_region[i].get(row['region'], 0) + 1
            else:
                groups = [g for g in groups if g]
                break
            count += 1
    else:
        groups, group, weight = [], [], overhead
        for nid, row in items:
            if group and (weight + sizes[nid] >= limit or len(group) >= POOL_LIMIT):
                groups.append(group)
                group, weight = [], overhead
            group.append((nid, row))
            weight += sizes[nid]
        if group:
            groups.append(group)
    manifest, outputs = dict(shell, shards=[]), {}
    for group in groups:
        payload = dict(shell, count=len(group), nations=[n for _, n in group] if kind == 'n' else dict(group))
        text = encode(payload, limit, 'game data shard')
        name = kind + '-' + hashlib.sha256(text.encode('utf-8')).hexdigest()[:32] + '.json'
        manifest['shards'].append([name, len(group)] + ([group[-1][0]] if kind == 'h' else []))
        outputs['game/data/' + name] = text
    return encode(manifest, limit, 'game data manifest'), outputs


def stale_shards(root, outputs):
    directory = os.path.join(root, 'game', 'data')
    if not os.path.isdir(directory):
        return []
    return ['game/data/' + name for name in os.listdir(directory)
            if re.fullmatch(r'[nh]-[a-f0-9]{32}\.json', name) and 'game/data/' + name not in outputs]


def build(root=ROOT, model=None):
    model = model if model is not None else Model(root)
    if model.errors:
        raise ValueError("invalid nations publication model: " + "; ".join(model.errors))
    raw_facts = {f["id"]: f for n in model.raw["nations"] for f in n["facts"]}
    out, skipped, histories = [], [], {}
    for n in model.nations:
        name, lands, countries = n["name"], n["lands"], n["countries"]
        if not (1 <= len(name) <= NAME_LIMIT and 1 <= len(lands) <= LANDS_LIMIT and 1 <= len(countries) <= 6):
            skipped.append(n["id"])
            continue
        quick = []
        ordered = sorted(n["facts"], key=lambda f: ORDER.index(f["kind"]) if f["kind"] in ORDER else 99)
        for f in ordered:
            if not (1 <= len(f["text"]) <= 300 and f["url"].startswith("https://")
                    and 1 <= len(f["publisher"]) <= 120):
                continue
            quick.append(fact_record(f, raw_facts[f["id"]]))
            if len(quick) == 2:
                break
        if not quick:
            skipped.append(n["id"])
            continue
        entry = {
            "id": n["id"], "name": name, "also": [a for a in n["also"] if 1 <= len(a) <= 80][:6],
            "lands": lands, "countries": countries, "region": n["region"], "facts": quick,
        }
        if n.get("official_url") and n["official_url"].startswith("https://"):
            entry["official_url"] = n["official_url"]
        if n.get("pronounce"):
            p = n["pronounce"]
            entry["pronounce"] = {"text": p["text"], "source_url": p["url"], "publisher": p["publisher"]}
        out.append(entry)
        history = [f for f in n["facts"] if f["kind"] == "history"]
        if history:
            histories[n["id"]] = {
                "history": [fact_record(f, raw_facts[f["id"]], full=True) for f in history],
                "context": [fact_record(f, raw_facts[f["id"]], full=True)
                            for f in n["facts"] if f["kind"] != "history"],
            }
    dates = [f["checked"] for n in out for f in n["facts"]]
    dates += [f["checked"] for n in histories.values() for section in n.values() for f in section]
    updated = max(dates, default=model.compiled)
    source = "data/nations/nations.json"
    quick_doc = {"updated": updated, "count": len(out), "source": source, "nations": out}
    history_doc = {"updated": updated, "count": len(histories), "source": source, "nations": histories}
    outputs = {}
    for name, doc, budget, kind in [('nations', quick_doc, LIMIT, 'n'), ('history', history_doc, HISTORY_LIMIT, 'h')]:
        text, shards = partition(doc, budget, kind)
        # Keep the same forbidden-character gate for legacy documents and shards.
        if '\u2014' in text or '\u2013' in text:
            raise ValueError('dash in game/' + name + '.json')
        outputs['game/' + name + '.json'] = text
        outputs.update(shards)
    return outputs, out, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check both generated files without writing")
    parser.add_argument("--root", default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    outputs, nations, skipped = build(args.root)
    if args.check:
        outdated = stale_shards(args.root, outputs)
        for rel, text in outputs.items():
            path = os.path.join(args.root, rel)
            with open(path, encoding="utf-8") if os.path.exists(path) else open(os.devnull) as f:
                if f.read() != text:
                    outdated.append(rel)
        if outdated:
            print("Out of date: %s. Run py -3.10 tools/game_nations.py" % ", ".join(outdated))
            return 1
        return 0
    for rel, text in outputs.items():
        path = os.path.join(args.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("%s: %d characters, %d UTF-8 bytes" % (rel, len(text), len(text.encode("utf-8"))))
    # A hold or takedown must also remove previously generated public shard copies.
    # Only delete our exact content-addressed output names; never other game files.
    for rel in stale_shards(args.root, outputs):
        os.unlink(os.path.join(args.root, rel))
    history_doc = json.loads(outputs["game/history.json"])
    print("%d nations, %d quick facts; %d nations with history; skipped %d: %s" %
          (len(nations), sum(len(n["facts"]) for n in nations), history_doc["count"], len(skipped), skipped[:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
