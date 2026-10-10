import sys, json, io
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
d = json.load(io.open(sys.argv[1], "r", encoding="utf-8"))
n = 0
for nat in d["nations"]:
    for i, f in enumerate(nat["facts"]):
        n += 1
        t = f["text"]
        probs = []
        if len(t) > 200: probs.append(f"len={len(t)}")
        if "\u2014" in t or "\u2013" in t: probs.append("dash")
        ev = f["evidence"]; wc = len(ev.split())
        if wc > 12 or wc < 4: probs.append(f"evidence_words={wc}")
        if probs: print(nat["id"], i, probs, "|", t)
print("facts:", n, "nations:", len(d["nations"]))
