import nations_lib as L
from conftest import ROOT, node_eval


def test_feistel4_is_a_bijection_and_terminates():
    m = L.Model(ROOT)
    counts = sorted({len(r["ab"]) for r in m.regions} | set(range(1, 301)))
    for n in counts:
        for key in (0, 1, 0xDEADBEEF, 2 ** 32 - 1):
            perm = [L.feistel4(x, n, key) for x in range(n)]
            assert sorted(perm) == list(range(n)), (n, key)


def test_feistel4_and_ring_match_the_javascript():
    cases = [[x, n, key] for n in (1, 2, 3, 5, 16, 21, 53, 100, 299) for x in range(0, n, max(1, n // 7))
             for key in (0, 12345, 4294967295)]
    js = node_eval("process.stdout.write(JSON.stringify(DATA.map(c => ZN.feistel4(c[0], c[1], c[2]))));", cases)
    assert js == [L.feistel4(*c) for c in cases]
    m = L.Model(ROOT)
    data = {"date": m.build_date, "v": m.version, "counts": [len(r["ab"]) for r in m.regions]}
    js = node_eval("const s = ZN.fnv1a32(DATA.date + '|' + DATA.v); process.stdout.write(JSON.stringify("
                   "DATA.counts.map((n, i) => ZN.ringPick(s, i, n))));", data)
    seed = L.ring_seed(m.build_date, m.version)
    assert js == [L.ring_pick(seed, i, n) for i, n in enumerate(data["counts"])]


def test_ring_is_deterministic_and_turns_daily():
    m = L.Model(ROOT)
    a = [n["id"] for _, n, _ in m.ring("2026-10-12")]
    b = [n["id"] for _, n, _ in L.Model(ROOT).ring("2026-10-12")]
    c = [n["id"] for _, n, _ in m.ring("2026-10-13")]
    assert a == b and len(a) == 15
    assert a != c
