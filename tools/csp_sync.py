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
(download.html stays script-src 'none'). The game group also hashes its page and injected overlay styles. Other directives are never touched, and each file keeps its own line endings.

Pages are grouped (GROUPS). Every file in a group must carry the same inline scripts (one hash list), or --check
reports the odd file: the 450 generated nation pages come from one template, so a template edit that reached only
some pages is caught. For a "strict" group the whole meta policy of every file must equal the header policy byte for
byte, less the directives a meta policy cannot carry (frame-ancestors, report-uri, sandbox). A group whose files
are missing is skipped, so a checkout without a nations build still passes.
"""
import argparse
import base64
import glob
import hashlib
import json
import os
import re
import sys
from html.parser import HTMLParser

PAGES = ("index.html", "download.html")   # the two landing pages (kept for tools that import this name)
META_IGNORED = ("frame-ancestors", "report-uri", "sandbox")


def groups(root):
    """The page groups, with their files resolved under root."""
    nat = sorted(os.path.relpath(p, root).replace(os.sep, "/")
                 for p in glob.glob(os.path.join(root, "nations", "**", "*.html"), recursive=True))
    return [
        {"name": "index.html", "files": ["index.html"], "sources": ["/", "/index", "/index.html"], "strict": False},
        {"name": "download.html", "files": ["download.html"], "sources": ["/download", "/download.html"], "strict": False},
        {"name": "game", "files": ["game/index.html"], "sources": ["/game", "/game/", "/game/index", "/game/index.html"], "strict": False, "meta": False, "styles": True},
        {"name": "nations hub", "files": ["nations.html"], "sources": ["/nations", "/nations.html"], "strict": True},
        {"name": "nations pages", "files": nat, "sources": ["/nations/(.*)"], "strict": True},
    ]


def meta_policy(policy):
    """A header policy as a meta element may carry it: the directives browsers ignore in meta are dropped."""
    parts = [d.strip() for d in policy.split(";") if d.strip()]
    return "; ".join(d for d in parts if d.split()[0] not in META_IGNORED)


META_RE = re.compile(r'(<meta\b[^>]*http-equiv="Content-Security-Policy"[^>]*\bcontent=")([^"]*)(")', re.I)
DIRECTIVE_RE = re.compile(r"(?<![\w-])script-src(?![\w-])[^;]*")


class _InlineScripts(HTMLParser):
    """Collects the raw text of every <script> without a src attribute. Script bodies are raw text to the parser
    (no character-reference decoding), and comments are skipped, as in a browser."""

    def __init__(self, tag="script"):
        self.tag = tag
        super().__init__(convert_charrefs=True)
        self.bodies, self.cur = [], None

    def handle_starttag(self, tag, attrs):
        if tag == self.tag:
            self.cur = "skip" if any(k == "src" for k, _ in attrs) else []

    def handle_data(self, data):
        if isinstance(self.cur, list):
            self.cur.append(data)

    def handle_endtag(self, tag):
        if tag == self.tag:
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


def game_style_hashes(root, html):
    """Hash both page styles and the exact overlay CSS printed by game/build.py."""
    parser = _InlineScripts("style")
    parser.feed(html.replace("\r\n", "\n").replace("\r", "\n"))
    parser.close()
    source = read(os.path.join(root, "game", "index.src.html"))
    block = re.search(r"var CSS = ((?:'(?:[^'\\]|\\.)*'\s*\+?\s*)+);", source, flags=re.S)
    if not block:
        raise SystemExit("game: injected CSS could not be found in the readable source")
    css = ''.join(re.findall(r"'((?:[^'\\]|\\.)*)'", block.group(1))).replace("\\'", "'").replace('\\\\', '\\')
    return ["'sha256-" + base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii") + "'"
            for body in parser.bodies + [css]]


def fix_styles(policy, hashes):
    pattern = re.compile(r"(?<![\w-])style-src(?![\w-])[^;]*")
    if not pattern.search(policy):
        raise SystemExit("game policy has no style-src directive")
    return pattern.sub(lambda m: "style-src " + " ".join(hashes), policy, count=1)


def directive(hashes):
    return "script-src " + (" ".join(hashes) if hashes else "'none'")


def fix_policy(policy, hashes):
    if not DIRECTIVE_RE.search(policy):
        raise SystemExit("policy has no script-src directive: " + policy[:80])
    return DIRECTIVE_RE.sub(lambda m: directive(hashes), policy, count=1)


def page_for_source(source, grps=None):
    """vercel.json header source -> name of the page group it serves (None when it is not one of ours)."""
    for g in grps or groups(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
        if source in g["sources"]:
            return g["name"]
    return None


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
    drift, writes, hashes, metas, styles = [], {}, {}, {}, {}
    grps = [g for g in groups(root) if g["files"] and all(os.path.isfile(os.path.join(root, f)) for f in g["files"])]

    for g in grps:
        ref = None
        for page in g["files"]:
            p = os.path.join(root, page)
            html = read(p)
            hs = page_hashes(html)
            if ref is None:
                ref = hs
            elif hs != ref:
                drift.append(f"{page}: inline scripts differ from the group {g['name']}")
                continue
            if g.get("styles"):
                styles[g["name"]] = game_style_hashes(root, html)
            if not g.get("meta", True):
                continue
            n = len(META_RE.findall(html))
            if n != 1:
                drift.append(f"{page}: expected one meta CSP, found {n}")
                continue
            new = META_RE.sub(lambda m: m.group(1) + fix_policy(m.group(2), hs) + m.group(3), html, count=1)
            if new != html:
                drift.append(f"{page}: meta CSP script-src is stale ({len(hs)} inline scripts)")
                writes[p] = new
            metas.setdefault(g["name"], {})[page] = META_RE.search(new).group(2)
        hashes[g["name"]] = ref or []

    vp = os.path.join(root, "vercel.json")
    if os.path.isfile(vp):
        raw = read(vp)
        nl = "\r\n" if "\r\n" in raw else "\n"
        conf = json.loads(raw)
        seen = set()
        for entry in conf.get("headers", []):
            name = page_for_source(entry.get("source", ""), grps)
            if name is None or name not in hashes:
                continue
            for hd in entry.get("headers", []):
                if hd.get("key", "").lower() == "content-security-policy":
                    seen.add(name)
                    fixed = fix_policy(hd["value"], hashes[name])
                    if name in styles:
                        fixed = fix_styles(fixed, styles[name])
                    if fixed != hd["value"]:
                        drift.append(f"vercel.json {entry['source']}: script/style hashes are stale")
                        hd["value"] = fixed
                    g = next(x for x in grps if x["name"] == name)
                    if g["strict"]:
                        want = meta_policy(fixed)
                        for page, pol in metas.get(name, {}).items():
                            if pol != want:
                                drift.append(f"{page}: meta policy differs from the {entry['source']} header policy "
                                             f"(strict group {name})")
        for name in hashes:
            if name not in seen:
                drift.append(f"vercel.json: no Content-Security-Policy header serves {name}")
        new = json.dumps(conf, indent=2) + "\n"
        if nl != "\n":
            new = new.replace("\n", nl)
        if new != raw:
            if not any(d.startswith("vercel.json") and "stale" in d for d in drift):
                drift.append("vercel.json: formatting differs from canonical json (indent 2)")
            writes[vp] = new

    for g in grps:
        many = f" in each of {len(g['files'])} pages" if len(g["files"]) > 1 else ""
        print(f"{g['name']}: {len(hashes[g['name']])} inline script(s){many}")
    if a.check:
        for d in drift[:40]:
            print("DRIFT " + d)
        if len(drift) > 40:
            print(f"DRIFT ... and {len(drift) - 40} more")
        print("csp_sync --check: " + ("FAIL" if drift else "ok"))
        return 1 if drift else 0
    for p, text in writes.items():
        write(p, text)
    if writes:
        names = ", ".join(os.path.relpath(p, root) for p in writes)
        print(f"updated {len(writes)} file(s)" + (": " + names if len(writes) < 6 else ""))
    else:
        print("csp_sync: already in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
