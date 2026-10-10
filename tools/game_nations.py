"""Build game/nations.json, the game edition of the nations registry, from data/nations/nations.json.

Every nation that fits the game's data contract, up to two facts each (present-day kinds first), each with its
source and checked date. Facts held for the owner's decision (named living individuals) are left out. The file must
stay under the game's 512 KB read limit. Usage: py -3.10 tools/game_nations.py [--check]"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "nations", "nations.json")
OUT = os.path.join(ROOT, "game", "nations.json")
HELD = ("Bhuri Bai",)                      # named living individuals: held until the owner decides
ORDER = ["today", "governance", "language", "land", "achievement", "population", "culture", "history"]
LIMIT = 512 * 1024 - 8 * 1024             # stay clear of the game's 524 288 character read limit


def clip(s, n):
    return s if s is None or len(s) <= n else None


def build():
    d = json.load(open(SRC, encoding="utf-8"))
    out, skipped = [], []
    for n in d["nations"]:
        name, lands, cs = n.get("name", ""), n.get("lands", ""), n.get("countries") or []
        if not (1 <= len(name) <= 80 and 1 <= len(lands) <= 200 and 1 <= len(cs) <= 6):
            skipped.append(n["id"]); continue
        facts = []
        for f in sorted(n["facts"], key=lambda f: ORDER.index(f["kind"]) if f["kind"] in ORDER else 99):
            s = f["source"]
            if any(h in f["text"] for h in HELD) or f.get("status") not in (None, "verified"):
                continue
            if not (len(f["text"]) <= 300 and s["url"].startswith("https://") and 1 <= len(s["publisher"]) <= 120):
                continue
            facts.append({"text": f["text"], "kind": f["kind"], "as_of": f.get("as_of"),
                          "source": {"title": clip(s.get("title"), 200), "publisher": s["publisher"], "url": s["url"], "accessed": s["accessed"]}})
            if len(facts) == 2:
                break
        if not facts:
            skipped.append(n["id"]); continue
        also = [a for a in (n.get("also") or []) if 1 <= len(a) <= 80][:6]
        e = {"id": n["id"], "name": name, "also": also, "lands": lands, "countries": cs, "region": n.get("region"), "facts": facts}
        if n.get("official_url", "") and n["official_url"].startswith("https://"):
            e["official_url"] = n["official_url"]
        if n.get("pronounce"):
            e["pronounce"] = n["pronounce"]
        out.append(e)
    upd = max(f["source"]["accessed"] for e in out for f in e["facts"])
    doc = {"updated": upd, "count": len(out), "source": "data/nations/nations.json", "nations": out}
    txt = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
    assert "—" not in txt and "–" not in txt, "dash in game nations data"
    assert len(txt) < LIMIT, "game nations file is %d characters, over %d" % (len(txt), LIMIT)
    return txt, out, skipped


if __name__ == "__main__":
    txt, out, skipped = build()
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        sys.exit(0 if cur == txt else "game/nations.json is out of date: run py -3.10 tools/game_nations.py")
    open(OUT, "w", encoding="utf-8", newline="\n").write(txt)
    print("game/nations.json: %d nations, %d facts, %d characters; skipped %d: %s" % (len(out), sum(len(e["facts"]) for e in out), len(txt), len(skipped), skipped[:8]))
