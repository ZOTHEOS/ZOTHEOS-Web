"""Release switch for zotheos.org (stdlib only): one command moves the whole site between its two release states.

Both pages (index.html and download.html) carry both variants of everything that depends on the release, and CSS
shows one of them, keyed on <html data-release>:
  prerelease  the ask is "Join the release list" -> #waitlist; the status reads "Windows desktop: internal testing";
              the release page explains what is still being validated
  available   the ask is "Download for Windows" + version + size -> the installer; the status reads the version;
              the release page shows the file name, size, SHA-256 checksum and the download

This tool, on both pages:
  - sets <html data-release>
  - fills the release details:  data-rs="version" | "size" | "file" | "sha256"  get their text,
    links with data-rs-href get the installer href
  - copies the state's variant into every meta tag that carries data-rs-pre / data-rs-avail (the descriptions;
    {version} and {size} are filled in), so link previews and search snippets follow the switch
  - rewrites the SoftwareApplication entry of the landing's JSON-LD (availability, operating system, description,
    and softwareVersion / fileSize / downloadUrl only while available)
  - then runs tools/csp_sync.py, because the JSON-LD block is hashed into the Content-Security-Policy
Visible copy itself switches by CSS (.rs-pre / .rs-avail), so no page script is involved.

Usage (run from PowerShell or cmd; in Git Bash prefix MSYS_NO_PATHCONV=1 so a leading / in --href survives):
  py -3.10 tools/release_switch.py                       show the current state and the filled values
  py -3.10 tools/release_switch.py prerelease            back to the release list ask (details are kept)
  py -3.10 tools/release_switch.py available --version 1.0.0 --href /download/ZOTHEOS_Setup_1.0.0_x64.exe
      --installer C:\\release\\ZOTHEOS_Setup_1.0.0_x64.exe   (size and SHA-256 are read from the file)
  py -3.10 tools/release_switch.py available --version 1.0.0 --size "904 MB" --sha256 <64 hex> --href /download/...
  py -3.10 tools/release_switch.py --check               non-zero when a page disagrees with its state:
      placeholders left while available, or copy of the other state still visible (outside .rs-pre / .rs-avail,
      in a meta description or in the JSON-LD), or the two pages in different states
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ("index.html", "download.html")
PLACEHOLDERS = {"version": "v0.0.0", "size": "0 MB", "href": "/download.html", "file": "installer.exe",
                "sha256": "sha256-pending"}
PAGE_ONLY = {"file": "download.html", "sha256": "download.html"}   # details only the release page shows
SITE = "https://zotheos.org"

# Phrases that belong to one state only (matched case-insensitively against what the other state shows).
PRERELEASE_ONLY = ("validation in progress", "validation is in progress", "release validation", "internal testing",
                   "before a public download", "no replacement installer", "candidate in validation",
                   "current validation", "is unsigned", "still being checked", "schema.org/preorder",
                   "validation continues")
AVAILABLE_ONLY = ("available to download", "download for windows", "ready to download", "schema.org/instock",
                  "the current installer is for windows")

# The landing's JSON-LD SoftwareApplication entry, per state. AVAILABLE_KEYS exist only while available.
JSONLD = {
    "prerelease": {
        "operatingSystem": "Windows x64 (desktop candidate in validation)",
        "description": "A local AI council with Analyst, Humanist and Skeptic roles. The Windows desktop is built for "
                       "internal testing; setup, installation and clean-machine checks remain in progress before a "
                       "public download.",
        "availability": "https://schema.org/PreOrder",
    },
    "available": {
        "operatingSystem": "Windows x64",
        "description": "A local AI council with Analyst, Humanist and Skeptic roles. The Windows desktop is available "
                       "to download; models are a separate choice, made in Model Setup.",
        "availability": "https://schema.org/InStock",
    },
}
AVAILABLE_KEYS = ("softwareVersion", "fileSize", "downloadUrl")

HTML_TAG = re.compile(r'<html\b[^>]*>')
FIELD = re.compile(r'(<(\w+)\b[^>]*\bdata-rs="(version|size|file|sha256)"[^>]*>)([^<]*)(</\2>)')
HREF_TAG = re.compile(r'<a\b[^>]*\bdata-rs-href\b[^>]*>')
HREF_ATTR = re.compile(r'\bhref="[^"]*"')
VARIANT_TAG = re.compile(r'<meta\b[^>]*\bdata-rs-avail="[^"]*"[^>]*>')
JSONLD_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)


def esc(v):
    return v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def unesc(v):
    return v.replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def read(name):
    with open(os.path.join(ROOT, name), encoding="utf-8", newline="") as f:
        return f.read()


def write(name, s):
    with open(os.path.join(ROOT, name), "w", encoding="utf-8", newline="") as f:
        f.write(s)


def state(s):
    m = HTML_TAG.search(s)
    a = re.search(r'\bdata-release="([^"]*)"', m.group(0)) if m else None
    return a.group(1) if a else "prerelease"


def values(s):
    out = {k: set() for k in PLACEHOLDERS}
    for m in FIELD.finditer(s):
        out[m.group(3)].add(m.group(4))
    for m in HREF_TAG.finditer(s):
        h = HREF_ATTR.search(m.group(0))
        out["href"].add(h.group(0)[6:-1] if h else "")
    return out


def current(s, key):
    """The page's single value for a detail, or "" when it has none or several."""
    v = values(s)[key]
    return next(iter(v)) if len(v) == 1 else ""


def set_state(s, st):
    m = HTML_TAG.search(s)
    tag = m.group(0)
    if 'data-release="' in tag:
        new = re.sub(r'\bdata-release="[^"]*"', f'data-release="{st}"', tag)
    else:
        new = tag[:-1] + f' data-release="{st}">'
    return s[:m.start()] + new + s[m.end():]


def fill(s, d):
    """d: the release details given on the command line (None keeps what the page has)."""
    def field(m):
        v = d.get(m.group(3))
        return m.group(0) if v is None else m.group(1) + esc(v) + m.group(5)
    s = FIELD.sub(field, s)
    if d.get("href") is not None:
        s = HREF_TAG.sub(lambda m: HREF_ATTR.sub(f'href="{esc(d["href"])}"', m.group(0), count=1), s)
    return s


def apply_variants(s, st):
    """Copy the state's variant into content= of every meta tag that carries both."""
    version, size = unesc(current(s, "version")), unesc(current(s, "size"))   # raw text: esc() below escapes once

    def one(m):
        tag = m.group(0)
        pick = re.search(r'\bdata-rs-%s="([^"]*)"' % ("avail" if st == "available" else "pre"), tag)
        if not pick:
            return tag
        text = unesc(pick.group(1)).replace("{version}", version).replace("{size}", size)
        return re.sub(r'\bcontent="[^"]*"', lambda _: f'content="{esc(text)}"', tag, count=1)
    return VARIANT_TAG.sub(one, s)


def apply_jsonld(s, st):
    m = JSONLD_RE.search(s)
    if not m:
        return s
    obj = json.loads(m.group(2))
    graph = obj.get("@graph", [obj])
    app = next((g for g in graph if g.get("@type") == "SoftwareApplication"), None)
    if app is None:
        return s
    want, rebuilt = JSONLD[st], {}
    for k, v in app.items():
        if k in AVAILABLE_KEYS:
            continue
        rebuilt[k] = want[k] if k in ("operatingSystem", "description") else v
        if k == "operatingSystem" and st == "available":
            # The markup holds these HTML-escaped (&amp;); JSON-LD is raw script text, so it gets them unescaped.
            href = unesc(current(s, "href"))
            rebuilt["softwareVersion"] = unesc(current(s, "version")).lstrip("vV")
            rebuilt["fileSize"] = unesc(current(s, "size"))
            rebuilt["downloadUrl"] = SITE + href if href.startswith("/") and not href.startswith("//") else href
    if isinstance(rebuilt.get("offers"), dict):
        rebuilt["offers"] = dict(rebuilt["offers"], availability=want["availability"])
    app.clear()
    app.update(rebuilt)
    body = "\n  " + json.dumps(obj, indent=2, ensure_ascii=True) + "\n  "   # the block's own layout, byte for byte
    return s[:m.start(2)] + body + s[m.end(2):]


class _Shown(HTMLParser):
    """What a visitor or a crawler gets in one state: page text outside the other state's blocks, outside the
    dated updates log (.rs-history) and outside <style> / <script> (JSON-LD is kept), plus every meta content."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self, hide_class):
        super().__init__(convert_charrefs=True)
        self.hide_class, self.stack, self.out = hide_class, [], []

    def hidden(self):
        return any(h for _, h in self.stack)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            if a.get("content") and not self.hidden():
                self.out.append(a["content"])
            return
        if tag in self.VOID:
            return
        cls = (a.get("class") or "").split()
        # rs-history: the dated updates log on download.html (tools/release.py log). An old entry may name a state
        # the site has left ("internal testing"); it is history, so it is not checked against the current state.
        skip = (self.hide_class in cls or "rs-history" in cls or tag == "style"
                or (tag == "script" and a.get("type") != "application/ld+json"))
        self.stack.append((tag, skip))

    def handle_startendtag(self, tag, attrs):
        if tag == "meta":
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if not self.hidden():
            self.out.append(data)


def shown_text(s, st):
    p = _Shown("rs-pre" if st == "available" else "rs-avail")
    p.feed(s)
    p.close()
    return re.sub(r"\s+", " ", " ".join(p.out)).lower()


def problems(name, s):
    st, bad = state(s), []
    if st not in ("prerelease", "available"):
        return [f'{name}: unknown data-release "{st}"']
    if st == "available":
        v = values(s)
        for k, ph in PLACEHOLDERS.items():
            if not v[k]:
                if PAGE_ONLY.get(k, name) == name:
                    bad.append(f"{name}: no {k} slot found")
            elif ph in v[k]:
                bad.append(f"{name}: {k} still shows the placeholder {ph!r}")
            if len(v[k]) > 1:
                bad.append(f"{name}: {k} differs between slots: {sorted(v[k])}")
    text = shown_text(s, st)
    for phrase in (PRERELEASE_ONLY if st == "available" else AVAILABLE_ONLY):
        if phrase in text:
            bad.append(f"{name}: shows {phrase!r} while {st}")
    return bad


def sha256_of(fp):
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("state", nargs="?", choices=["prerelease", "available"])
    ap.add_argument("--version", help='shown as given, e.g. "v1.0.0" (a bare 1.0.0 gets a leading v)')
    ap.add_argument("--size", help='installer size as shown, e.g. "904 MB" (measured from --installer when omitted)')
    ap.add_argument("--sha256", help="the installer's SHA-256, 64 hex digits (measured from --installer when omitted)")
    ap.add_argument("--installer", help="the local installer file, to measure its size and SHA-256")
    ap.add_argument("--href", help="installer link, e.g. /download/ZOTHEOS_Setup_1.0.0_x64.exe (its file name is shown)")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    pages = {n: read(n) for n in PAGES}

    if a.check:
        bad = [b for n, s in pages.items() for b in problems(n, s)]
        states = sorted({state(s) for s in pages.values()})
        if len(states) > 1:
            bad.append(f"the pages are in different states: {states}")
        for b in bad:
            print("release_switch --check:", b)
        print("release_switch --check:", "ok" if not bad else "FAILED", f"(state {', '.join(states)})")
        return 1 if bad else 0

    if a.href and re.match(r"^[A-Za-z]:[\\/]", a.href):
        print(f"refused: --href {a.href!r} is a local Windows path. Git Bash rewrites a leading /; run from"
              " PowerShell or cmd, or prefix the command with MSYS_NO_PATHCONV=1.")
        return 1
    if a.href and a.href.startswith("//"):
        print(f"refused: --href {a.href!r} starts with //, which a browser reads as another host. Use one / for a"
              " path on this site, or a full https:// address.")
        return 1
    if a.sha256 and not re.fullmatch(r"[0-9a-fA-F]{64}", a.sha256):
        print("refused: --sha256 must be 64 hex digits")
        return 1

    if a.state:
        d = {"href": a.href, "size": a.size, "sha256": a.sha256.lower() if a.sha256 else None}
        if a.installer:
            if not os.path.isfile(a.installer):
                print(f"refused: --installer {a.installer!r} is not a file")
                return 1
            if d["size"] is None:
                d["size"] = f"{os.path.getsize(a.installer) / 1048576:.0f} MB"
            if d["sha256"] is None:
                d["sha256"] = sha256_of(a.installer)
        ver = a.version
        if ver and re.match(r"^\d", ver):
            ver = "v" + ver
        d["version"] = ver
        d["file"] = a.href.rstrip("/").rsplit("/", 1)[-1] if a.href else None
        out, bad = {}, []
        for n, s in pages.items():
            s = apply_variants(fill(set_state(s, a.state), d), a.state)
            if n == "index.html":
                s = apply_jsonld(s, a.state)
            out[n] = s
            bad += problems(n, s)
        if bad:
            for b in bad:
                print("refused:", b)
            if a.state == "available":
                print("Pass --version and --href, plus --installer (or --size and --sha256), to switch to available.")
            return 1
        for n, s in out.items():
            if s != pages[n]:
                write(n, s)
        pages = out
        r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "csp_sync.py"), "--root", ROOT])
        if r.returncode:
            print("csp_sync.py failed: run it by hand before publishing.")
            return 1

    for n, s in pages.items():
        v = values(s)
        print(f"{n}: state {state(s)}")
        for k in PLACEHOLDERS:
            if v[k]:
                print(f"  {k}: {', '.join(sorted(v[k]))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
