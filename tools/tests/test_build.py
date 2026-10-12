"""Build stability, the change footprint of one edit, the evidence break, and the news shelf flag (slow: each runs
a full build in a scratch copy)."""
import glob
import json
import os
import re
import sys

from conftest import ROOT, run

sys.path.insert(0, os.path.join(ROOT, "data", "nations", "tools"))


def outputs(root):
    rels = ["nations.html", "vercel.json"]
    rels += [os.path.relpath(p, root).replace(os.sep, "/") for p in
             glob.glob(os.path.join(root, "nations", "**", "*.html"), recursive=True) +
             glob.glob(os.path.join(root, "static", "nations", "*"))]
    return {rel: open(os.path.join(root, rel), encoding="utf-8").read() for rel in rels}


def edit_nation(root, nid, fn):
    for name in ("nations.json", "nations.min.json"):
        p = os.path.join(root, "data", "nations", name)
        doc = json.load(open(p, encoding="utf-8"))
        for n in doc["nations"]:
            if n["id"] == nid:
                fn(n)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            if name == "nations.json":
                f.write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
            else:
                f.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))


def test_committed_output_is_the_build_of_the_committed_data():
    code, out = run(ROOT, "tools/nations_build.py", "--check")
    assert code == 0, out[-2000:]


def test_one_also_changes_exactly_its_footprint(scratch):
    before = outputs(scratch)
    edit_nation(scratch, "secwepemc-bc-ca", lambda n: n["also"].append("Shuswap people"))
    code, out = run(scratch, "tools/nations_build.py")
    assert code == 0, out[-2000:]
    after = outputs(scratch)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    shards = [k for k in changed if re.match(r"static/nations/canada\.[0-9a-f]{8}\.json", k)]
    assert len(shards) == 2, changed          # the old canada shard gone, the new one written
    assert "static/nations/search.json" in changed and "static/nations/index.json" in changed
    assert "nations/secwepemc-bc-ca.html" in changed and "nations.html" in changed and "vercel.json" in changed
    others = [k for k in changed if k.startswith("nations/") and k != "nations/secwepemc-bc-ca.html"]
    assert not others, others                  # region and country cards show only the first other name


def test_evidence_break_hides_the_fact_and_says_so(scratch):
    import nations_refresh as R
    page = "The Shuswap Nation Tribal Council brings together the bands of the Secwepemc people."
    pn = R.normalise(page)
    assert R.match("brings together nine Secwépemc communities", pn, R.strip_marks(pn),
                   R.no_punct(R.strip_marks(pn))) is None
    target = {}

    def stale(n):
        f = n["facts"][0]
        target.update(id=f["id"], text=f["text"], host=f["source"]["url"].split("/")[2])
        f["status"] = "stale"
    edit_nation(scratch, "secwepemc-bc-ca", stale)
    code, out = run(scratch, "tools/nations_build.py")
    assert code == 0, out[-2000:]
    nation = open(os.path.join(scratch, "nations", "secwepemc-bc-ca.html"), encoding="utf-8").read()
    assert target["text"] not in nation and "1 fact is being re-checked." in nation
    shard = glob.glob(os.path.join(scratch, "static", "nations", "canada.*.json"))[0]
    assert target["text"] not in open(shard, encoding="utf-8").read()
    ver = open(os.path.join(scratch, "nations", "verification.html"), encoding="utf-8").read()
    host = target["host"][4:] if target["host"].startswith("www.") else target["host"]
    assert f"{host}: 1 fact, the cited words are no longer on the page" in ver


def test_news_shelf_hidden_then_shown(scratch):
    news = json.load(open(os.path.join(ROOT, "static", "nations", "news.json"), encoding="utf-8"))
    assert news == {"gathered": None, "items": [], "outlets": [], "shelf": False}
    hub = open(os.path.join(ROOT, "nations.html"), encoding="utf-8").read()
    assert "Indigenous-led newsrooms" not in hub and "Koori Mail" not in hub
    with open(os.path.join(scratch, "data", "news", "flags.json"), "w") as f:
        json.dump({"shelf_visible": True}, f)
    with open(os.path.join(scratch, "data", "news", "headlines.json"), "w", encoding="utf-8") as f:
        json.dump({"gathered": "12 Oct 2026, 13:41 UTC", "items": [
            {"title": "A headline - with a hyphen", "link": "https://ictnews.org/news/a-story", "outlet": "ICT",
             "date": "2026-10-12", "lang": "en", "region": "us"}]}, f, ensure_ascii=False)
    code, out = run(scratch, "tools/nations_build.py")
    assert code == 0, out[-2000:]
    hub = open(os.path.join(scratch, "nations.html"), encoding="utf-8").read()
    assert "From Indigenous-led newsrooms" in hub and "A headline - with a hyphen" in hub
    assert "Headlines gathered 12 Oct 2026" in hub and "No headline source yet for:" in hub
