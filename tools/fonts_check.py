#!/usr/bin/env python3
"""Check the self-hosted fonts: both pages share one @font-face block, every file it names exists, and nothing
asks another site for a font.

Usage (stdlib only):  python tools/fonts_check.py [--root DIR]      exit 1 on any problem
                      python tools/fonts_check.py --record          add new font files to tools/fonts.sha256

Checked:
  - index.html and download.html each carry exactly one <style id="zth-fonts"> block, and the two are identical
  - every url(...) in that block, and the <link rel="preload" as="font"> href, points at a file under static/fonts/
  - the preloaded file is one the block actually uses, and the preload carries crossorigin (fonts are CORS fetches)
  - every .woff2 in static/fonts/ is named by the block (an orphan would still be published and cached for a year)
  - static/fonts/OFL.txt is present (the SIL Open Font License travels with the fonts)
  - no page and no vercel.json header mentions fonts.googleapis.com or fonts.gstatic.com, and no page says
    "Google Fonts" (the visible privacy copy must stay in step with the CSP)
  - every Content-Security-Policy (page meta and vercel.json) has font-src 'self' and nothing else
  - vercel.json serves /static/fonts/(.*) with an immutable Cache-Control
  - every font file matches its hash in tools/fonts.sha256. Because the cache is immutable, a changed file must get a
    new name; a file whose bytes changed under the same name fails here. --record adds new files and drops removed
    ones, and never re-blesses a changed file. (The manifest lives in tools/, not static/fonts/, so it is not itself
    served under the immutable rule.)
See docs/FONTS.md for how to add or update a face.
"""
import argparse
import hashlib
import json
import os
import re
import sys

PAGES = ("index.html", "download.html")
BLOCK_RE = re.compile(r'<style id="zth-fonts">(.*?)</style>', re.S)
URL_RE = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)")
PRELOAD_RE = re.compile(r'<link\b[^>]*\brel="preload"[^>]*\bas="font"[^>]*>', re.I)
META_RE = re.compile(r'<meta\b[^>]*http-equiv="Content-Security-Policy"[^>]*\bcontent="([^"]*)"', re.I)
THIRD_PARTY = ("fonts.googleapis.com", "fonts.gstatic.com")
BANNED_PHRASE = re.compile(r"google\s+fonts", re.I)
FONTS_SOURCE = "/static/fonts/(.*)"
MANIFEST = "tools/fonts.sha256"


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def font_src_ok(policy):
    m = re.search(r"(?<![\w-])font-src\s+([^;]*)", policy)
    return bool(m) and m.group(1).split() == ["'self'"]


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_manifest(path):
    out = {}
    if os.path.isfile(path):
        for line in read(path).splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                digest, name = line.split(None, 1)
                out[name.lstrip("*")] = digest
    return out


def check_manifest(root, files, record):
    """Return problems; with record=True, also add new files and drop removed ones (never re-bless a changed one)."""
    path = os.path.join(root, *MANIFEST.split("/"))
    known = load_manifest(path)
    bad, current = [], {f: sha256(os.path.join(root, "static", "fonts", f)) for f in files}
    for name, digest in sorted(current.items()):
        if name not in known:
            if not record:
                bad.append(f"static/fonts/{name} is not in {MANIFEST}; run tools/fonts_check.py --record")
        elif known[name] != digest:
            bad.append(f"static/fonts/{name} changed under the same name; the cache is immutable, so give it a "
                       f"new name (see docs/FONTS.md)")
    for name in sorted(set(known) - set(current)):
        if not record:
            bad.append(f"{MANIFEST} lists {name}, which is gone; run tools/fonts_check.py --record")
    if record:
        merged = {n: known.get(n, d) for n, d in current.items()}
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("# sha256 of each file in static/fonts/. Written by tools/fonts_check.py --record.\n")
            f.write("# A changed font gets a new file name; never edit a hash here by hand.\n")
            for name in sorted(merged):
                f.write(f"{merged[name]}  {name}\n")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--record", action="store_true", help="add new font files to tools/fonts.sha256")
    args = ap.parse_args()
    root = args.root
    bad, blocks = [], {}

    def local(href, where):
        if not href.startswith("/static/fonts/"):
            bad.append(f"{where}: {href} is not under /static/fonts/")
            return
        if not os.path.isfile(os.path.join(root, href.lstrip("/"))):
            bad.append(f"{where}: {href} does not exist")

    for page in PAGES:
        p = os.path.join(root, page)
        if not os.path.isfile(p):
            bad.append(f"{page}: missing")
            continue
        html = read(p)
        found = BLOCK_RE.findall(html)
        if len(found) != 1:
            bad.append(f"{page}: expected one <style id=\"zth-fonts\"> block, found {len(found)}")
            continue
        block = found[0]
        blocks[page] = block
        urls = URL_RE.findall(block)
        if not urls:
            bad.append(f"{page}: the font block names no files")
        for u in urls:
            local(u, page)
        for tag in PRELOAD_RE.findall(html):
            href = re.search(r'\bhref="([^"]+)"', tag)
            href = href.group(1) if href else ""
            local(href, f"{page} preload")
            if href not in urls:
                bad.append(f"{page}: preload {href} is not used by the font block (a wasted download)")
            if not re.search(r"\bcrossorigin\b", tag):
                bad.append(f"{page}: font preload {href} lacks crossorigin, so the browser fetches it twice")
        for host in THIRD_PARTY:
            if host in html:
                bad.append(f"{page}: still mentions {host}")
        if BANNED_PHRASE.search(html):
            bad.append(f"{page}: says \"Google Fonts\"; the fonts are self-hosted, so that copy is no longer true")
        metas = META_RE.findall(html)
        if len(metas) != 1 or not font_src_ok(metas[0]):
            bad.append(f"{page}: meta CSP font-src must be exactly 'self'")

    if len(set(blocks.values())) > 1:
        bad.append("index.html and download.html font blocks differ; copy one block to both pages")

    fonts_dir = os.path.join(root, "static", "fonts")
    if not os.path.isfile(os.path.join(fonts_dir, "OFL.txt")):
        bad.append("static/fonts/OFL.txt is missing (the licence must travel with the fonts)")

    files = sorted(f for f in os.listdir(fonts_dir) if f.lower().endswith(".woff2")) if os.path.isdir(fonts_dir) else []
    used = {os.path.basename(u) for b in blocks.values() for u in URL_RE.findall(b)}
    for f in files:
        if f not in used:
            bad.append(f"static/fonts/{f} is not named in the zth-fonts block; delete it or use it")
    bad.extend(check_manifest(root, files, args.record))

    vp = os.path.join(root, "vercel.json")
    if not os.path.isfile(vp):
        bad.append("vercel.json is missing (it carries the CSP and the font cache rule)")
    else:
        raw = read(vp)
        for host in THIRD_PARTY:
            if host in raw:
                bad.append(f"vercel.json: still mentions {host}")
        immutable = False
        for entry in json.loads(raw).get("headers", []):
            for hd in entry.get("headers", []):
                key = hd.get("key", "").lower()
                if key == "content-security-policy" and not font_src_ok(hd.get("value", "")):
                    bad.append(f"vercel.json {entry.get('source')}: CSP font-src must be exactly 'self'")
                if (entry.get("source") == FONTS_SOURCE and key == "cache-control"
                        and "immutable" in hd.get("value", "").lower()):
                    immutable = True
        if not immutable:
            bad.append(f"vercel.json: no {FONTS_SOURCE} entry sets an immutable Cache-Control (docs/FONTS.md relies on it)")

    for b in bad:
        print("FONTS " + b)
    n = len(URL_RE.findall(next(iter(blocks.values()), "")))
    print(f"fonts_check: {'FAIL' if bad else 'ok'} ({n} faces, {len(files)} files, {len(blocks)} pages)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
