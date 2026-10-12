import json
import os

from conftest import ROOT, node_eval
from nations_fold import fold, tokens

import nations_lib as L


def test_fold_parity_over_every_name_and_place():
    m = L.Model(ROOT)
    corpus = []
    for n in m.raw["nations"]:
        corpus += [n["name"], n["lands"]] + n.get("also", []) + n.get("also_search", [])
    corpus += [r["display"] for r in m.regions] + list(m.countries.values())
    corpus = sorted(set(corpus))
    assert len(corpus) >= 1200
    js = node_eval("process.stdout.write(JSON.stringify(DATA.map(s => ZN.fold(s))));", corpus)
    assert js == [fold(s) for s in corpus]


def test_fold_rules():
    assert tokens("Sḵwx̱wú7mesh Úxwumixw") == ["skwxwumesh", "uxwumixw"]
    assert tokens("Tłı̨chǫ") == ["tlicho"]
    assert tokens("xʷməθkʷəy̓əm") == ["xwmethkweyem"]
    assert tokens("ǂKhomani") == ["khomani"]
    assert tokens("Route 7 east") == ["route", "7", "east"]   # a 7 between spaces is a number, and stays


def search(queries):
    s = json.load(open(os.path.join(ROOT, "static", "nations", "search.json"), encoding="utf-8"))
    return node_eval("const E = DATA.s.n.map(r => ZN.prep(r, DATA.s.regions, DATA.s.countries));"
                     "process.stdout.write(JSON.stringify(DATA.q.map(q => ZN.search(E, q).slice(0, 8).map(x => "
                     "({id: x.e.id, n: x.e.n, also: x.m.also || null, r: x.m.r})))));", {"s": s, "q": queries})


def test_search_cases():
    r = dict(zip(["Maori", "Dine", "oodham", "ootham", "Musqueam", "Toba", "Эскимосы", "Hopi", "Pima"],
                 search(["Maori", "Dine", "oodham", "ootham", "Musqueam", "Toba", "Эскимосы", "Hopi", "Pima"])))
    assert any("Māori" in x["n"] for x in r["Maori"])
    assert any(x["n"] == "Diné" for x in r["Dine"])
    assert any(x["id"].startswith("tohono") for x in r["oodham"])
    assert any(x["id"].startswith("akimel") for x in r["ootham"])          # Akimel O’otham is spelled with t
    assert r["Musqueam"][0]["n"] == "xʷməθkʷəy̓əm" and r["Musqueam"][0]["also"] == "Musqueam"
    assert r["Toba"][0]["n"] == "Qom" and r["Toba"][0]["also"] is None       # also_search never shows
    assert any(x["id"] == "yupik-chukotka" for x in r["Эскимосы"])
    assert r["Hopi"][0]["n"].startswith("Hopi") and r["Hopi"][0]["r"] == 0  # the name outranks any lands match
    assert r["Pima"][0]["id"].startswith("akimel")
