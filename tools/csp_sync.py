#!/usr/bin/env python3
"""Keep the Content-Security-Policy script-src hashes in step with the inline scripts.

Usage (from anywhere, stdlib only):
    python tools/csp_sync.py            rewrite index.html / download.html meta CSPs and vercel.json
    python tools/csp_sync.py --check    report drift and exit 1 if anything is stale; writes nothing
    python tools/csp_sync.py --root DIR operate on another checkout

Every inline <script> (no src attribute) in each page is hashed, including type="application/ld+json" and
type="speculationrules" blocks, over the text exactly as the HTML parser sees it (CRLF and lone CR folded to LF;
scripts are found with html.parser, so a '<script' inside an HTML comment is not mistaken for a tag). The script-src
directive of the page's <meta http-equiv="Content-Security-Policy"> and of every vercel.json header entry whose
source serves that page is rewritten to the hash list, or to 'none' when the page has no inline script
(download.html stays script-src 'none'). Other directives are never touched, and each file keeps its own line endings.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import sys
from html.parser import HTMLParser

PAGES = ("index.html", "download.html")
META_RE = re.compile(r'(<meta\b[^>]*http-equiv="Content-Security-Policy"[^>]*\bcontent=")([^"]*)(")', re.I)
DIRECTIVE_RE = re.compile(r"(?<![\w-])script-src(?![\w-])[^;]*")


class _InlineScripts(HTMLParser):
    """Collects the raw text of every <script> without a src attribute. Script bodies are raw text to the parser
    (no character-reference decoding), and comments are skipped, as in a browser."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bodies, self.cur = [], None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.cur = "skip" if any(k == "src" for k, _ in attrs) else []

    def handle_data(self, data):
        if isinstance(self.cur, list):
            self.cur.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            if isinstance(self.cur, list):
                self.bodies.append("".join(self.cur))
            self.cur = None


def page_hashes(html):
    text = html.replace("\r\n", "\n").replace("\r", "\n")
    parser = _InlineScripts()
    parser.feed(text)
    parser.close()
    out = []
    for body in parser.bodies:
        digest = hashlib.sha256(body.encode("utf-8")).digest()
        out.append("'sha256-" + base64.b64encode(digest).decode("ascii") + "'")
    return out


def directive(hashes):
    return "script-src " + (" ".join(hashes) if hashes else "'none'")


def fix_policy(policy, hashes):
    if not DIRECTIVE_RE.search(policy):
        raise SystemExit("policy has no script-src directive: " + policy[:80])
    return DIRECTIVE_RE.sub(lambda m: directive(hashes), policy, count=1)


def page_for_source(source):
    """vercel.json header source -> page file it serves (None when it is not one of ours)."""
    if source == "/":
        return "index.html"
    name = source.lstrip("/")
    if not name.endswith(".html"):
        name += ".html"
    return name if name in PAGES else None


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 on drift, write nothing")
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args()
    root = a.root
    drift, writes, hashes = [], {}, {}

    for page in PAGES:
        p = os.path.join(root, page)
        if not os.path.isfile(p):
            continue
        html = read(p)
        hs = page_hashes(html)
        hashes[page] = hs
        n = len(META_RE.findall(html))
        if n != 1:
            drift.append(f"{page}: expected one meta CSP, found {n}")
            continue
        new = META_RE.sub(lambda m: m.group(1) + fix_policy(m.group(2), hs) + m.group(3), html, count=1)
        if new != html:
            drift.append(f"{page}: meta CSP script-src is stale ({len(hs)} inline scripts)")
            writes[p] = new

    vp = os.path.join(root, "vercel.json")
    if os.path.isfile(vp):
        raw = read(vp)
        nl = "\r\n" if "\r\n" in raw else "\n"
        conf = json.loads(raw)
        seen = set()
        for entry in conf.get("headers", []):
            page = page_for_source(entry.get("source", ""))
            if page is None or page not in hashes:
                continue
            for hd in entry.get("headers", []):
                if hd.get("key", "").lower() == "content-security-policy":
                    seen.add(page)
                    fixed = fix_policy(hd["value"], hashes[page])
                    if fixed != hd["value"]:
                        drift.append(f"vercel.json {entry['source']}: script-src is stale")
                        hd["value"] = fixed
        for page in hashes:
            if page not in seen:
                drift.append(f"vercel.json: no Content-Security-Policy header serves {page}")
        new = json.dumps(conf, indent=2) + "\n"
        if nl != "\n":
            new = new.replace("\n", nl)
        if new != raw:
            if not any(d.startswith("vercel.json") and "stale" in d for d in drift):
                drift.append("vercel.json: formatting differs from canonical json (indent 2)")
            writes[vp] = new

    for page, hs in hashes.items():
        print(f"{page}: {len(hs)} inline script(s)")
    if a.check:
        for d in drift:
            print("DRIFT " + d)
        print("csp_sync --check: " + ("FAIL" if drift else "ok"))
        return 1 if drift else 0
    for p, text in writes.items():
        write(p, text)
        print("updated " + os.path.relpath(p, root))
    if not writes:
        print("csp_sync: already in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
