"""Build the game's quick cards and optional history from the canonical published nations view.

Usage: py -3.10 tools/game_nations.py [--check]
The quick file retains two facts per nation. History is a separate, bounded payload, with no new claims.
"""
import argparse
import json
import os

from nations_lib import Model

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = ["today", "governance", "language", "land", "achievement", "population", "culture", "history"]
LIMIT = 512 * 1024 - 8 * 1024
HISTORY_LIMIT = 256 * 1024
NAME_LIMIT = 120
LANDS_LIMIT = 300


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
    return {
        "game/nations.json": encode(quick_doc, LIMIT, "game/nations.json"),
        "game/history.json": encode(history_doc, HISTORY_LIMIT, "game/history.json"),
    }, out, skipped


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check both generated files without writing")
    parser.add_argument("--root", default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    outputs, nations, skipped = build(args.root)
    if args.check:
        outdated = []
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
    history_doc = json.loads(outputs["game/history.json"])
    print("%d nations, %d quick facts; %d nations with history; skipped %d: %s" %
          (len(nations), sum(len(n["facts"]) for n in nations), history_doc["count"], len(skipped), skipped[:8]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
