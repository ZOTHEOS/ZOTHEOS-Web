#!/usr/bin/env python3
"""Subset the fallback faces for /nations and write the names font block (DESIGN_NATIONS 11.3).

The brand faces (Instrument Serif, DM Sans, JetBrains Mono) cover Latin and Latin Extended only. Nation names, other
names, lands, facts and source titles also use IPA and spacing-modifier letters, combining marks, click letters,
Greek, Cyrillic, Cherokee, Canadian Syllabics and Devanagari. This tool:

  1. collects every code point in published strings by role (from tools/nations_lib.Model);
  2. reads the brand faces' cmaps from static/fonts/*.woff2 (needs fontTools and brotli);
  3. subsets each vendored face in tools/fonts-src/ (hashes checked against tools/fonts-src/manifest.json) to its
     role's set, keeping every layout feature (mark, mkmk, ccmp survive) and every name record (the OFL notices
     travel with a Modified Version);
  4. names each output by content hash, static/fonts/zn-<face>.<hash8>.woff2, deleting a superseded file;
  5. writes tools/nations/partials/fonts-names.css, the <style id="zth-fonts-names"> block, with unicode-range taken
     from each subset's real cmap, font-display: block, and size-adjust from measured x-heights;
  6. appends each family's licence block to static/fonts/OFL.txt when missing, and runs fonts_check.py --record.

The fix for a missing letter is a face or a block here, never an edit to a name.
Usage: py -3.10 tools/nations_fonts.py [--root DIR] [--no-record]
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nations_lib as L  # noqa: E402
import nations_directory as D  # noqa: E402

BLOCKS_NAMES = [(0x0020, 0x007E), (0x00A0, 0x00FF), (0x0100, 0x017F), (0x0180, 0x024F), (0x0250, 0x02AF),
                (0x02B0, 0x02FF), (0x0300, 0x036F), (0x0370, 0x03FF), (0x0400, 0x04FF), (0x1E00, 0x1EFF),
                (0x2018, 0x201F)]
# key, CSS family, vendored source, output stem, role, x-height reference (brand family whose sxHeight it matches)
FACES = [
    {"key": "serif", "family": "ZN Serif", "src": "tinos/Tinos-Regular.ttf", "stem": "zn-serif", "role": "names", "ref": "serif"},
    {"key": "sans", "family": "ZN Sans", "src": "noto-sans/NotoSans-Regular.ttf", "stem": "zn-sans", "role": "reading", "ref": "sans"},
    {"key": "mono", "family": "ZN Mono", "src": "cousine/Cousine-Regular.ttf", "stem": "zn-mono", "role": "labels", "ref": "mono"},
    {"key": "cherokee", "family": "ZN Cherokee", "src": "noto-sans-cherokee/NotoSansCherokee-Regular.ttf", "stem": "zn-cherokee",
     "role": [(0x13A0, 0x13FF), (0xAB70, 0xABBF)], "ref": "sans"},
    {"key": "syllabics", "family": "ZN Syllabics", "src": "noto-sans-canadian-aboriginal/NotoSansCanadianAboriginal-Regular.ttf",
     "stem": "zn-syllabics", "role": [(0x1400, 0x167F), (0x18B0, 0x18FF)], "ref": "sans"},
    {"key": "devanagari", "family": "ZN Devanagari", "src": "noto-sans-devanagari/NotoSansDevanagari-Regular.ttf",
     "stem": "zn-devanagari", "role": [(0x0900, 0x097F), (0xA8E0, 0xA8FF), (0x200C, 0x200D), (0x25CC, 0x25CC)], "ref": "sans"},
    {"key": "tifinagh", "family": "ZN Tifinagh", "src": "noto-sans-tifinagh/NotoSansTifinagh-Regular.ttf", "stem": "zn-tifinagh",
     "role": [(0x2D30, 0x2D7F)], "ref": "sans"},
]
BRAND_SX = {"serif": "instrument-serif-latin.woff2", "sans": "dm-sans-var-latin.woff2", "mono": "jetbrains-mono-var-latin.woff2"}
LABEL_ASCII = set(range(0x20, 0x7F)) | {0xB7}


def role_sets(model):
    names, reading = set(), set()
    for n in model.nations:
        s = n["name"] + "".join(n["also"]) + "".join(n["also_search"]) + (n["pronounce"]["text"] if n["pronounce"] else "")
        names |= {ord(c) for c in s}
        reading |= {ord(c) for c in s + n["lands"]}
        for f in n["all_facts"]:
            reading |= {ord(c) for c in f["text"] + f["title"] + f["publisher"]}
        if n["pronounce"]:
            reading |= {ord(c) for c in n["pronounce"]["publisher"]}
    for r in model.regions:
        reading |= {ord(c) for c in r["display"]}
    for c in model.countries.values():
        reading |= {ord(c2) for c2 in c}
    labels = set(LABEL_ASCII)
    for r in model.regions:
        labels |= {ord(c) for c in r["display"]}
    # The directory is a separate published collection, not part of Model.nations.
    # Reuse its actual publication filter so confirmed hide/takedown matches do
    # not become a second route into this string inventory. Never alter spelling.
    directory, _ = D.load(model.root)
    for document in (directory, D.load_canada(model.root), *D.inventories(model.root)):
        for entry in D.visible_entries(SimpleNamespace(m=model), document["entities"]):
            points = {ord(c) for c in entry["name"] + entry["directory_name"]}
            names |= points
            reading |= points
            labels |= points
        source = document["source"]
        points = {ord(c) for c in source["title"] + source["publisher"]}
        reading |= points
        labels |= points
    for _, label, note in D.LANES:
        reading |= {ord(c) for c in label + note}
        labels |= {ord(c) for c in label}
    return names, reading, labels


def ranges_of(cps):
    out, run = [], None
    for cp in sorted(cps):
        if run and cp == run[1] + 1:
            run[1] = cp
        else:
            if run:
                out.append(tuple(run))
            run = [cp, cp]
    if run:
        out.append(tuple(run))
    return out


def urange(cps):
    return ", ".join(f"U+{a:04X}" if a == b else f"U+{a:04X}-{b:04X}" for a, b in ranges_of(cps))


def sx_ratio(path):
    from fontTools.ttLib import TTFont
    f = TTFont(path, lazy=True)
    r = f["OS/2"].sxHeight / f["head"].unitsPerEm
    f.close()
    return r


def subset(src, cps):
    from fontTools import subset as ss
    from fontTools.ttLib import TTFont
    opts = ss.Options()
    opts.layout_features = ["*"]
    opts.layout_scripts = ["*"]
    opts.name_IDs = ["*"]
    opts.name_languages = ["*"]
    opts.name_legacy = True
    opts.notdef_outline = True
    opts.recalc_timestamp = False
    opts.flavor = "woff2"
    opts.hinting = False          # names are large and the brand files are unhinted too; saves about a third
    font = TTFont(src, recalcTimestamp=False)
    sub = ss.Subsetter(opts)
    sub.populate(unicodes=sorted(cps))
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf, reorderTables=True)
    got = set(font.getBestCmap().keys())
    font.close()
    return buf.getvalue(), got


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=L.ROOT)
    ap.add_argument("--no-record", action="store_true", help="do not run fonts_check.py --record")
    ap.add_argument("--build-date", default=None)
    a = ap.parse_args(argv)
    root = a.root
    model = L.Model(root, a.build_date)
    brand = L.BrandCover(root)
    names, reading, labels = role_sets(model)
    src_dir = os.path.join(root, "tools", "fonts-src")
    manifest = json.load(open(os.path.join(src_dir, "manifest.json"), encoding="utf-8"))["files"]
    fonts_dir = os.path.join(root, "static", "fonts")
    scripts = {cp for f in FACES if not isinstance(f["role"], str) for a_, b in f["role"] for cp in range(a_, b + 1)}
    names_set = (names | {cp for a_, b in BLOCKS_NAMES for cp in range(a_, b + 1)}) - scripts
    reading_set = (names_set | reading) - scripts
    label_set = {cp for cp in labels if cp not in brand.mono}
    css, report, keep = [], [], set()
    for face in FACES:
        src = os.path.join(src_dir, *face["src"].split("/"))
        digest = hashlib.sha256(open(src, "rb").read()).hexdigest()
        if manifest.get(face["src"], {}).get("sha256") != digest:
            raise SystemExit(f"{face['src']}: hash differs from tools/fonts-src/manifest.json; record a changed source on purpose")
        role = face["role"]
        want = {"names": names_set, "reading": reading_set, "labels": label_set}.get(role) if isinstance(role, str) else \
            {cp for a_, b in role for cp in range(a_, b + 1)}
        cm = L.cmap(src)
        want = {cp for cp in want if cp in cm}
        if not want:
            raise SystemExit(f"{face['family']}: nothing to subset")
        data, got = subset(src, want)
        name = f"{face['stem']}.{hashlib.sha256(data).hexdigest()[:8]}.woff2"
        keep.add(name)
        out = os.path.join(fonts_dir, name)
        if not os.path.isfile(out) or open(out, "rb").read() != data:
            with open(out, "wb") as f:
                f.write(data)
        for old in os.listdir(fonts_dir):
            if old.startswith(face["stem"] + ".") and old.endswith(".woff2") and old != name:
                os.remove(os.path.join(fonts_dir, old))
        ratio = sx_ratio(os.path.join(fonts_dir, BRAND_SX[face["ref"]])) / sx_ratio(src)
        uni = {cp for cp in got if cp >= 0x20}
        css.append(
            f"    @font-face {{ font-family: '{face['family']}'; font-style: normal; font-weight: 400; font-display: block; "
            f"size-adjust: {ratio * 100:.1f}%;\n      src: url(/static/fonts/{name}) format('woff2');\n"
            f"      unicode-range: {urange(uni)}; }}")
        report.append(f"{name}: {len(data):,} bytes, {len(uni)} code points, size-adjust {ratio * 100:.1f}%")
    block = '<style id="zth-fonts-names">\n' + "\n".join(css) + "\n  </style>"
    part = os.path.join(root, "tools", "nations", "partials", "fonts-names.css")
    with open(part, "w", encoding="utf-8", newline="\n") as f:
        f.write(block + "\n")
    # licence blocks
    ofl_path = os.path.join(fonts_dir, "OFL.txt")
    ofl = open(ofl_path, encoding="utf-8", newline="").read()
    start = ofl.index("This Font Software is licensed under the SIL Open Font License")
    endmark = "OTHER DEALINGS IN THE FONT SOFTWARE."
    body = ofl[start:ofl.index(endmark, start) + len(endmark)]
    added = []
    for face in FACES:
        head = manifest[face["src"]]["copyright"] + " (" + manifest[face["src"]]["family"] + ")"
        if head not in ofl:
            ofl = ofl.rstrip("\n") + "\n\n\n" + head + "\n\n" + body + "\n"
            added.append(face["family"])
    if added:
        with open(ofl_path, "w", encoding="utf-8", newline="") as f:
            f.write(ofl)
    if not a.no_record:
        subprocess.run([sys.executable, os.path.join(root, "tools", "fonts_check.py"), "--root", root, "--record"],
                       check=False, stdout=subprocess.DEVNULL)
    for line in report:
        print("  " + line)
    if added:
        print("  OFL.txt: added licence blocks for " + ", ".join(added))
    return 0


if __name__ == "__main__":
    sys.exit(main())
