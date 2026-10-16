#!/usr/bin/env python3
"""Gates for /nations (DESIGN_NATIONS 11.4, 12.1, 4.1, 3.3, 7.1). Exit 1 on any failure.

  - reserved ids (a nation id may not be a word the site uses as a path) and blocked ids (taken down) absent
  - the copied tokens in tools/nations/partials/tokens.css still equal index.html's values
  - the Appearance popover's Theme and Motion rows in the header partial still equal index.html's
  - the first-paint script and the zth-fonts block partials still equal index.html's
  - the glyph gate: every grapheme cluster of every published string is drawn whole by one face of its role's stack
    (cmap read with fontTools, and the code point inside that face's declared unicode-range); a brand-face name has
    no combining mark; a fallback-face name has every code point in ZN Serif (the fallback never falls back)
  - labels: every TEXT string in herald.js and every mono label in the built pages is ASCII, the middle dot, or a code
    point used in regions.json display names
  - no rule in the stylesheet uppercases or italicizes a name; no speech synthesis in nations pages or the game
  - banned terms (ARCHITECTURE 9.1) absent from publisher copy (templates and partials; fact text is validate.py's
    job; a source title is the publisher's words, quoted as published); a held fact's text absent from every output
  - fold parity: the fold shipped in nations.html's herald.js (run with node) equals tools/nations_fold.py over every
    name, other name, retrieval name, lands line, region and country name

Usage: py -3.10 tools/nations_lint.py [--report] [--build-date YYYY-MM-DD]
       --report   print the glyph audit (fallback names, script lines, Devanagari titles) and never fail on glyphs
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from html.parser import HTMLParser

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nations_lib as L  # noqa: E402
from nations_fold import fold  # noqa: E402

NATIONS_ONLY = ("--zn-", "--page-bg", "--ink-low", "--line", "--rim-hover", "--gutter")
LABEL_CLASSES = {"lbl", "eyebrow", "hr-k", "kind", "hr-region", "ap-label", "ft-col-l", "hr-status", "fcount", "row-m"}
NAME_SELECTORS = (".nm", ".hr-name", ".n-h1")
UPPER_CLASSES = {"lbl", "eyebrow", "hr-k", "kind", "hr-region", "ap-label", "ft-col-l", "txt-link", "pill", "hr-more",
                 "ap-opt", "nh-nav", "skip"}
BANNED = re.compile(r"(?i)\b(extinct|vanished|last of the|disappeared|primitive|savages?|noble savage|spirit animal|"
                    r"legend says|blood quantum|full[- ]blood(?:ed)?|half[- ]breed)\b")


def css_blocks(text, selector):
    """Merged --token: value pairs of every top-level block with exactly this selector."""
    out = {}
    for m in re.finditer(r"(?:^|\})\s*" + re.escape(selector) + r"\s*\{([^{}]*)\}", text, re.M):
        for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", m.group(1)):
            out[k] = " ".join(v.split())
    return out


class Faces:
    def __init__(self, root):
        self.root = root
        brand = L.brand_block(root)
        names_css = L.read(os.path.join(root, "tools", "nations", "partials", "fonts-names.css"))
        self.cov = {}
        for fam in ("Instrument Serif", "DM Sans", "JetBrains Mono"):
            self.cov[fam] = L.family_cover(brand, fam, root)
        self.cov["Instrument Serif italic"] = L.family_cover(brand, "Instrument Serif", root, style="italic")
        for fam, _, _, _ in L.parse_font_faces(names_css):
            self.cov[fam] = L.family_cover(names_css, fam, root)
        self.stacks = {
            "brand-name": ["Instrument Serif", "ZN Serif", "ZN Cherokee", "ZN Syllabics", "ZN Tifinagh"],
            "names-name": ["ZN Serif", "ZN Cherokee", "ZN Syllabics", "ZN Tifinagh"],
            "brand-line": ["DM Sans"],
            "names-line": ["ZN Sans", "ZN Devanagari", "ZN Cherokee", "ZN Syllabics", "ZN Tifinagh"],
            "reading": ["DM Sans", "ZN Sans", "ZN Devanagari", "ZN Cherokee", "ZN Syllabics", "ZN Tifinagh"],
            "label": ["JetBrains Mono", "ZN Mono"],
            "display": ["Instrument Serif italic", "ZN Serif"],
        }

    def miss(self, s, stack):
        """Clusters no single face of the stack draws whole."""
        out = []
        for cl in L.clusters(s):
            if cl.isspace():
                continue
            if not any(all(ord(c) in self.cov.get(f, ()) for c in cl) for f in self.stacks[stack]):
                out.append(cl)
        return out


def cps(cl):
    return " ".join(f"U+{ord(c):04X}" for c in cl)


def glyph_gate(model, faces, brand, report):
    errs, audit = [], {"fallback": [], "lines": 0, "deva": set()}
    for n in model.nations:
        sc = L.script_of(n["name"])
        fc = "brand" if (sc == "latn" and brand.serif_ok(n["name"])) else "names"
        if fc == "brand" and L.has_mark(n["name"]):
            errs.append(f"nation {n['id']}: a brand-face name carries a combining mark")
        if fc == "names":
            audit["fallback"].append(n["name"])
            if sc == "latn":
                lack = [c for c in n["name"] if ord(c) not in faces.cov.get("ZN Serif", ()) and not c.isspace()]
                for c in lack:
                    errs.append(f"nation {n['id']}: {cps(c)} in name has no glyph in ZN Serif (the whole-name face)")
        for cl in faces.miss(n["name"], f"{fc}-name"):
            errs.append(f"nation {n['id']}: {cps(cl)} in name has no face in the names stack")
        lines = [("also", a) for a in n["also"]] + [("lands", n["lands"])]
        if n["pronounce"]:
            lines.append(("pronunciation", n["pronounce"]["text"]))
            lines.append(("pronunciation credit", n["pronounce"]["publisher"]))
        lines += [("fact " + f["id"], f["text"]) for f in n["facts"]]
        for role, text in lines:
            stack = "brand-line" if brand.sans_ok(text) else "names-line"
            if stack == "names-line":
                audit["lines"] += 1
            if role == "pronunciation credit":
                stack = "reading"
            for cl in faces.miss(text, stack):
                errs.append(f"nation {n['id']}: {cps(cl)} in {role} has no face in the reading stack")
        for f in n["facts"]:
            for role, text in (("source title", f["title"]), ("publisher", f["publisher"])):
                if any(0x900 <= ord(c) <= 0x97F for c in text):
                    audit["deva"].add(text)
                for cl in faces.miss(text, "reading"):
                    errs.append(f"nation {n['id']}: {cps(cl)} in {role} of {f['id']} has no face in the reading stack")
    for r in model.regions:
        for cl in faces.miss(r["display"], "label"):
            errs.append(f"region {r['key']}: {cps(cl)} in the label has no face in the mono stack")
        for cl in faces.miss(r["display"], "display"):
            errs.append(f"region {r['key']}: {cps(cl)} in the heading has no face in the display stack")
    for c, name in model.countries.items():
        for cl in faces.miss(name, "reading"):
            errs.append(f"country {c}: {cps(cl)} has no face in the reading stack")
    if report:
        print(f"glyph audit: {len(audit['fallback'])} names render whole in ZN Serif or a script face: "
              + ", ".join(audit["fallback"]))
        print(f"glyph audit: {audit['lines']} other-name, lands, pronunciation or fact lines render whole in ZN Sans")
        print("glyph audit: source titles with Devanagari: " + " | ".join(sorted(audit["deva"])))
    return errs


class LabelText(HTMLParser):
    def __init__(self, classes=None):
        super().__init__(convert_charrefs=True)
        self.stack, self.found = [], []
        self.classes = classes or LABEL_CLASSES
        self.upper_only = classes is not None

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "img", "meta", "link", "input", "use", "path"):
            return
        cls = set((dict(attrs).get("class") or "").split())
        self.stack.append((tag, bool(cls & self.classes)))

    def handle_endtag(self, tag):
        while self.stack:
            t, _ = self.stack.pop()
            if t == tag:
                break

    def handle_data(self, data):
        if any(lab for _, lab in self.stack) and data.strip():
            self.found.append(data)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=L.ROOT)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--build-date", default=None)
    a = ap.parse_args(argv)
    root = a.root
    errs, warns = [], []
    model = L.Model(root, a.build_date)
    errs += model.errors
    raw_ids = [n["id"] for n in model.raw["nations"]]
    for i in raw_ids:
        if i in L.RESERVED_IDS:
            errs.append(f"nation id {i} is reserved (it would collide with a page path)")
        if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", i):
            errs.append(f"nation id {i} is not ascii kebab")
    for n in model.nations:
        if len(L.clusters(n["name"])) > 60:
            warns.append(f"nation {n['id']}: name is over 60 grapheme clusters; check the xs size on a phone")

    landing = L.read(os.path.join(root, "index.html"))
    part = lambda name: L.read(os.path.join(root, "tools", "nations", "partials", name))
    # tokens drift
    tok = part("tokens.css")
    pairs = [(":root", ":root"), ('[data-theme="codex"]', '[data-theme="codex"]'),
             ('[data-theme="skeleton"]', '[data-theme="skeleton"]'), (":root:not([data-theme])", ":root:not([data-theme])")]
    for mine_sel, land_sel in pairs:
        mine, theirs = css_blocks(tok, mine_sel), css_blocks(landing, land_sel)
        for k, v in mine.items():
            if k.startswith(NATIONS_ONLY):
                continue
            if k not in theirs:
                errs.append(f"tokens.css {mine_sel} {k}: index.html defines no such token in {land_sel}")
            elif theirs[k] != v:
                errs.append(f"tokens.css {mine_sel} {k}: {v} drifted from index.html's {theirs[k]}")
    # header drift: the Theme and Motion rows
    rows_re = re.compile(r'(<div class="ap-row">\s*<span class="ap-label" id="apThemeLabel">.*?</span>\s*</div>\s*</div>)\s*'
                         r'(<div class="ap-row" id="apMotionRow">.*?<p class="ap-note" id="apMotionNote"[^>]*>[^<]*</p>\s*</div>)',
                         re.S)
    norm = lambda s: " ".join(s.split())
    ml, mp = rows_re.search(landing), rows_re.search(part("header.html"))
    if not ml or not mp:
        errs.append("header drift: the Theme and Motion rows were not found in index.html or the header partial")
    elif norm(ml.group(1)) != norm(mp.group(1)) or norm(ml.group(2)) != norm(mp.group(2)):
        errs.append("header drift: the Appearance Theme or Motion row differs from index.html; copy it again")
    if "<script>" + part("bootstrap.js") + "</script>" not in landing:
        errs.append("bootstrap.js no longer matches index.html's first-paint script")
    if '<style id="zth-fonts">' + part("fonts-brand.css") + "</style>" not in landing:
        errs.append("fonts-brand.css no longer matches index.html's zth-fonts block")
    # glyphs
    faces = Faces(root)
    brand = L.BrandCover(root)
    gerrs = glyph_gate(model, faces, brand, a.report)
    if a.report:
        for e in gerrs:
            print("GLYPH " + e)
    else:
        errs += gerrs
    # labels
    allowed = set(range(0x20, 0x7F)) | {0xB7, 0xA0} | {ord(c) for r in model.regions for c in r["display"]}
    herald = part("herald.js")
    m = re.search(r"var TEXT = \{(.*?)\};", herald, re.S)
    if not m:
        errs.append("herald.js has no TEXT object")
    else:
        for s in re.findall(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"", m.group(1)):
            s = s[0] or s[1]
            bad = [c for c in s if ord(c) not in allowed]
            if bad:
                errs.append(f"herald.js TEXT string {s[:40]!r} has {cps(bad[0])}")
    built = (["nations.html"] if os.path.isfile(os.path.join(root, "nations.html")) else []) + sorted(
        os.path.relpath(p, root).replace(os.sep, "/") for p in glob.glob(os.path.join(root, "nations", "**", "*.html"), recursive=True))
    sample = [p for p in built if "/" not in p.replace("nations/", "", 1) or p.startswith("nations/region/")]
    # a nation's name, or a publisher's, never sits in an uppercased label or control
    ours = {r["display"] for r in model.regions} | set(model.countries.values())
    theirs = {n["name"] for n in model.nations if len(n["name"]) >= 4} | {
        f["publisher"] for n in model.nations for f in n["facts"] if len(f["publisher"]) >= 6}
    theirs -= ours
    theirs_re = re.compile(r"(?<!\w)(" + "|".join(re.escape(x) for x in sorted(theirs, key=len, reverse=True)) + r")(?!\w)")
    for rel in sample:
        lp = LabelText(UPPER_CLASSES)
        lp.feed(L.read(os.path.join(root, rel)))
        for t in lp.found:
            bad = [c for c in t if ord(c) not in allowed and not lp.upper_only]
            if t.strip() in ours:
                continue
            m2 = theirs_re.search(t)
            if m2:
                errs.append(f"{rel}: {m2.group(1)!r} is set in an uppercased label or control; names are never uppercased")
        lp = LabelText()
        lp.feed(L.read(os.path.join(root, rel)))
        for t in lp.found:
            bad = [c for c in t if ord(c) not in allowed]
            if bad:
                errs.append(f"{rel}: mono label {t.strip()[:40]!r} has {cps(bad[0])}, which the label faces may not carry")
    # name styling
    css = part("tokens.css") + part("nations.css")
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        if any(re.search(re.escape(ns) + r"(?![\w-])", sel) for ns in NAME_SELECTORS) or "data-face=\"names\"" in sel:
            tt = re.search(r"text-transform\s*:\s*([\w-]+)", body)
            if tt and tt.group(1) != "none":
                errs.append(f"stylesheet: {sel.strip()[:60]} sets text-transform on a name")
            if re.search(r"font-style\s*:\s*italic|font:\s*italic", body):
                errs.append(f"stylesheet: {sel.strip()[:60]} italicizes a name")
    # speech synthesis, banned terms, held facts
    scan = [os.path.join(root, p) for p in built] + glob.glob(os.path.join(root, "game", "*.html")) + \
           glob.glob(os.path.join(root, "game", "*.js")) + glob.glob(os.path.join(root, "tools", "nations", "partials", "*")) + \
           glob.glob(os.path.join(root, "tools", "nations", "templates", "*"))
    held = [f["text"] for nat in model.raw["nations"] for f in nat["facts"]
            if f["id"] in {e["fact"] for e in model.overrides.get("hide_fact", [])}]
    outs = glob.glob(os.path.join(root, "static", "nations", "*"))
    for p in scan + outs:
        t = L.read(p)
        if "speechSynthesis" in t or "SpeechSynthesisUtterance" in t:
            errs.append(f"{os.path.relpath(p, root)}: speech synthesis appears; no page may speak a name")
        if "partials" in p or "templates" in p:
            mb = BANNED.search(re.sub(r"<[^>]+>", " ", t))
            if mb:
                errs.append(f"{os.path.relpath(p, root)}: banned term {mb.group(0)!r} in publisher copy")
        for h in held:
            if h in t or json.dumps(h, ensure_ascii=False)[1:-1] in t:
                errs.append(f"{os.path.relpath(p, root)}: a fact held for review is published")
    for bid in model.blocked_ids:
        for p in built:
            if bid in L.read(os.path.join(root, p)):
                errs.append(f"{p}: names the taken-down id {bid}")
    # fold parity
    corpus = []
    for n in model.raw["nations"]:
        corpus += [n["name"], n["lands"]] + n.get("also", []) + n.get("also_search", [])
    corpus += [r["display"] for r in model.regions] + list(model.countries.values())
    corpus = sorted(set(corpus))
    node = shutil.which("node")
    hub = os.path.join(root, "nations.html")
    if not node:
        warns.append("fold parity skipped: node is not installed")
    else:
        if os.path.isfile(hub):
            hs = re.findall(r"<script>(.*?)</script>", L.read(hub), re.S)
            js = next((s for s in hs if "ZN_TEST" in s), None)
        else:
            js = None
        if js is None:
            from nations_fold import js as fold_js
            js = "(function(){" + fold_js() + "globalThis.ZN_TEST={fold:fold};})();"
        with tempfile.TemporaryDirectory() as td:
            jp, cp = os.path.join(td, "h.js"), os.path.join(td, "c.json")
            with open(jp, "w", encoding="utf-8") as f:
                f.write(js + "\nconst fs=require('fs');const c=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));"
                        "process.stdout.write(JSON.stringify(c.map(s=>globalThis.ZN_TEST.fold(s))));")
            with open(cp, "w", encoding="utf-8") as f:
                json.dump(corpus, f, ensure_ascii=False)
            p = subprocess.run([node, jp, cp], capture_output=True, text=True, encoding="utf-8")
            if p.returncode != 0:
                errs.append("fold parity: node failed: " + p.stderr[-500:])
            else:
                got = json.loads(p.stdout)
                diffs = [(s, fold(s), g) for s, g in zip(corpus, got) if fold(s) != g]
                for s, py, j in diffs[:10]:
                    errs.append(f"fold parity: {s!r} folds to {py!r} in Python, {j!r} in herald.js")
                if not diffs:
                    print(f"fold parity: {len(corpus)} strings agree")
    for w in warns:
        print("WARN " + w)
    for e in errs:
        print("LINT " + e)
    print(f"nations_lint: {'FAIL' if errs else 'ok'} ({len(model.nations)} nations, {len(built)} pages, "
          f"{len(errs)} errors, {len(warns)} warnings)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
