import os

import nations_lib as L
from conftest import ROOT


def model_with(fact_patch, human=None, build_date="2026-10-20"):
    m = L.Model(ROOT, build_date)
    f = dict(m.raw["nations"][0]["facts"][0])
    f.update(fact_patch)
    if human is not None:
        m.human = human
    return m.fact_state(f, set())


def test_display_states():
    assert model_with({"status": "unreachable", "last_verified": "2026-10-10"})[0] == "grace"     # 10 days
    assert model_with({"status": "unreachable", "last_verified": "2026-10-05"})[0] == "waiting"   # 15 days
    fid = L.Model(ROOT).raw["nations"][0]["facts"][0]["id"]
    st, date, _ = model_with({"status": "unreachable", "last_verified": "2026-09-01"}, {fid: {"date": "2026-10-01"}})
    assert st == "human" and date == "2026-10-01"
    assert model_with({"status": "unreachable", "last_verified": "2026-06-01"}, {fid: {"date": "2026-06-01"}})[0] == "waiting"
    assert model_with({"status": "stale"})[0] == "hidden"
    assert model_with({"status": "verified", "last_verified": "2026-10-08"})[0] == "ok"


def test_bhil_holds():
    m = L.Model(ROOT)
    bhil = m.by_id["in-bhil"]
    assert bhil["tier"] == "B" and len(bhil["facts"]) == 1 and bhil["review"] == 2
    page = open(os.path.join(ROOT, "nations", "in-bhil.html"), encoding="utf-8").read()
    assert "2 facts are under review." in page and "Bhuri Bai" not in page


def test_no_held_text_anywhere_in_the_output():
    for d, _, fs in os.walk(os.path.join(ROOT, "static", "nations")):
        for f in fs:
            assert "Bhuri Bai" not in open(os.path.join(d, f), encoding="utf-8").read()
