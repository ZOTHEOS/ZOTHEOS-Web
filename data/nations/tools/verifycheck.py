import sys, json, io, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
v = json.load(io.open(sys.argv[1], "r", encoding="utf-8"))
c = collections.Counter(r["verdict"] for r in v["results"])
print("results:", len(v["results"]), dict(c))
print("names:", len(v["names"]), "ok=false:", [n["id"] for n in v["names"] if not n["ok"]])
for r in v["results"]:
    if r["verdict"] == "fixed":
        t = r["text"]; bad = []
        if len(t) > 200: bad.append("len")
        if "\u2014" in t or "\u2013" in t: bad.append("dash")
        print("fixed", r["id"], r["fact"], len(t), "words_ev=", len(r["evidence"].split()), bad or "ok")
