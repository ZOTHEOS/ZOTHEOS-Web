"""The gates fail where they should (DESIGN_NATIONS 23)."""
import os

import nations_lib as L
from conftest import ROOT, run

SALTILLO = chr(0xA78C)
EN_DASH = chr(0x2013)
ACUTE = chr(0x0301)


def test_glyph_gate_catches_a_letter_no_face_has():
    import nations_lint
    m = L.Model(ROOT)
    n = m.by_id["secwepemc-bc-ca"]
    n["name"] = n["name"] + SALTILLO                   # the saltillo: no face in the stack has it
    errs = nations_lint.glyph_gate(m, nations_lint.Faces(ROOT), L.BrandCover(ROOT), False)
    assert any(e.startswith("nation secwepemc-bc-ca: U+A78C in name") for e in errs), errs[:3]


def test_a_combining_mark_flips_a_brand_name_to_the_fallback_face():
    import nations_build
    b = nations_build.Builder(ROOT)
    n = b.m.by_id["secwepemc-bc-ca"]
    assert n["fc"] == "brand"
    n["name"] = "Secwe" + ACUTE + "pemc"               # the same letters with a combining acute
    b.decide()
    assert n["fc"] == "names"


def test_csp_group_and_strict_checks(scratch):
    p = os.path.join(scratch, "nations", "secwepemc-bc-ca.html")
    t = open(p, encoding="utf-8").read()
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(t.replace("(function () {", "(function () { /* edited */", 1))
    code, out = run(scratch, "tools/csp_sync.py", "--check")
    assert code == 1 and "inline scripts differ from the group" in out
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(t.replace("connect-src 'none'", "connect-src 'self'", 1))
    code, out = run(scratch, "tools/csp_sync.py", "--check")
    assert code == 1 and "meta policy differs" in out


def test_lint_copy_en_dash(scratch):
    p = os.path.join(scratch, "nations", "about.html")
    t = open(p, encoding="utf-8").read()
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(t.replace("How this list is made.", "How this list " + EN_DASH + " is made.", 1))
    code, out = run(scratch, "tools/lint_copy.py")
    assert code == 1 and "nations/about.html" in out
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(t.replace("</body>", "<script>// a comment " + EN_DASH + " here\n</script></body>", 1))
    code, out = run(scratch, "tools/lint_copy.py")
    assert code == 0, out


def test_links_gate(scratch):
    p = os.path.join(scratch, "nations", "about.html")
    t = open(p, encoding="utf-8").read()
    cases = (('<a href="https://example.com/x" rel="noopener noreferrer" target="_blank">x</a>', "not a cited source"),
             ('<a href="https://formspree.io/f/x" rel="noopener noreferrer">x</a>', "formspree"),
             ('<a href="https://www.un.org/en/observances/indigenous-day/background" target="_blank">x</a>', "without rel"))
    for bad, word in cases:
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(t.replace("</main>", bad + "</main>", 1))
        code, out = run(scratch, "tools/nations_links.py")
        assert code == 1 and word in out, out[-400:]


def test_uppercase_name_is_refused(scratch):
    p = os.path.join(scratch, "nations", "about.html")
    t = open(p, encoding="utf-8").read()
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(t.replace("</main>", '<p><a class="txt-link" href="/nations/secwepemc-bc-ca">Secwépemc</a></p></main>', 1))
    code, out = run(scratch, "tools/nations_lint.py")
    assert code == 1 and "never uppercased" in out
