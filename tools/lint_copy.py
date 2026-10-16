#!/usr/bin/env python3
"""Copy lint for the site: no em dash (U+2014) and no en dash (U+2013) anywhere a visitor or a search engine can see it.

Usage: python tools/lint_copy.py [files...]   (default: index.html, download.html and every built nations page,
nations.html and nations/**/*.html, at the repo root)
Exit 1 when anything is found, printing file:line and where it was found.

Checked: text nodes (outside <script>/<style>), every attribute value (alt, title, aria-label, content,
placeholder, value, data-*...), the strings inside application/ld+json blocks, string and template literals in
inline JavaScript (comments are skipped), and CSS `content:` strings. Entities (&mdash; &#8212; &#x2014; and
&ndash; &#8211; &#x2013;) are decoded before checking, and the JavaScript escapes \\u2014 and \\u2013 count too.
Code comments may keep their dashes: nobody sees them.
"""
import glob
import json
import os
import re
import sys
from html.parser import HTMLParser

DASHES = ("\u2014", "\u2013")
JS_ESC = re.compile(r"\\u201[34]|\\u\{201[34]\}", re.I)
CSS_ESC = re.compile(r"\\0*201[34]", re.I)


def has_dash(text):
    return any(d in text for d in DASHES)


class Lint(HTMLParser):
    def __init__(self, name):
        super().__init__(convert_charrefs=True)
        self.name, self.hits, self.raw = name, [], None
        self.kind = None   # 'js', 'json', 'css', 'other' while inside script/style

    def hit(self, line, where, text):
        snippet = re.sub(r"\s+", " ", text.strip())
        found = [snippet.find(d) for d in DASHES if d in snippet]
        i = min(found) if found else -1
        if i < 0:
            m = JS_ESC.search(snippet) or CSS_ESC.search(snippet)
            i = m.start() if m else 0
        self.hits.append(f"{self.name}:{line}: {where}: ...{snippet[max(0, i - 40):i + 40]}...")

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        for k, v in attrs:
            if v and has_dash(v):
                self.hit(line, f"<{tag} {k}>", v)
        if tag in ("script", "style"):
            t = (dict(attrs).get("type") or "").lower()
            if tag == "style":
                self.kind = "css"
            elif t in ("", "text/javascript", "module", "application/javascript"):
                self.kind = "js"
            elif "json" in t or t == "speculationrules":
                self.kind = "json"
            else:
                self.kind = "other"
            self.raw, self.raw_line = [], line

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.raw is not None:
            text, line, kind = "".join(self.raw), self.raw_line, self.kind
            self.raw, self.kind = None, None
            if kind == "js":
                self.check_js(text, line)
            elif kind == "json":
                self.check_json(text, line)
            elif kind == "css":
                self.check_css(text, line)

    def handle_data(self, data):
        if self.raw is not None:
            self.raw.append(data)
        elif has_dash(data):
            self.hit(self.getpos()[0], "text", data)

    # -- embedded languages ------------------------------------------------------------------------------------------
    def check_json(self, text, line):
        try:
            data = json.loads(text)
        except ValueError:
            if has_dash(text):
                self.hit(line, "json block (unparsed)", text)
            return

        def walk(v):
            if isinstance(v, str):
                if has_dash(v):
                    self.hit(line + text[:text.find(v)].count("\n") if v in text else line, "json", v)
            elif isinstance(v, dict):
                for x in v.values():
                    walk(x)
            elif isinstance(v, list):
                for x in v:
                    walk(x)
        walk(data)

    def check_js(self, src, line0):
        i, n = 0, len(src)
        while i < n:
            c = src[i]
            if src.startswith("//", i):
                j = src.find("\n", i)
                i = n if j < 0 else j
            elif src.startswith("/*", i):
                j = src.find("*/", i + 2)
                i = n if j < 0 else j + 2
            elif c in "'\"`":
                j = i + 1
                while j < n and src[j] != c:
                    if src[j] == "\\":
                        j += 1
                    elif c != "`" and src[j] == "\n":
                        break
                    j += 1
                lit = src[i:j + 1]
                if has_dash(lit) or JS_ESC.search(lit):
                    self.hit(line0 + src[:i].count("\n"), "script string", lit)
                i = j + 1
            else:
                i += 1

    def check_css(self, css, line0):
        stripped = re.sub(r"/\*[\s\S]*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), css)
        for m in re.finditer(r"content\s*:\s*([^;}]*)", stripped):
            v = m.group(1)
            if has_dash(v) or CSS_ESC.search(v):
                self.hit(line0 + stripped[:m.start()].count("\n"), "css content", v)


def lint(path, root=None):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    name = os.path.relpath(path, root).replace(os.sep, "/") if root else os.path.basename(path)
    p = Lint(name)
    p.feed(text)
    p.close()
    return p.hits


def default_files(root):
    files = [os.path.join(root, n) for n in ("index.html", "download.html", "theater.html", "nations.html")]
    files += sorted(glob.glob(os.path.join(root, "nations", "**", "*.html"), recursive=True))
    return [f for f in files if os.path.isfile(f)]


def main(argv):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = argv or default_files(root)
    hits, n = [], 0
    for f in files:
        if os.path.isfile(f):
            n += 1
            hits += lint(f, None if argv else root)
    for h in hits:
        print(h)
    print(f"lint_copy: {len(hits)} em or en dash(es) in visible copy" if hits
          else f"lint_copy: ok, no em or en dash in visible copy ({n} files)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
