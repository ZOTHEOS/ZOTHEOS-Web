#!/usr/bin/env python3
"""Build /nations from data/nations (DESIGN_NATIONS.md 17.1). Deterministic; stdlib plus fontTools for the fonts step.

    py -3.10 tools/nations_build.py                     build into a scratch copy, run every gate there, then write
                                                         the outputs into the tree (a failed gate writes nothing)
    py -3.10 tools/nations_build.py --check             build into a scratch copy and diff against the committed
                                                         output; exit 1 on any difference (CI runs this)
    py -3.10 tools/nations_build.py --seed-last-verified the one-time migration of 9.2: every verified fact without
                                                         last_verified gets last_verified = checked
    --build-date YYYY-MM-DD   the date the build is for (default: the newest checked date in the data)
    --out DIR                 write the outputs to DIR instead of the tree (with --local-links, links carry .html so
                              python -m http.server can serve the scratch build; never commit that output)
    --game-json               also emit static/nations/game.json (specified, off at launch, 15.4)

Outputs: nations.html, nations/**.html, static/nations/*, static/fonts/zn-*.woff2, static/fonts/OFL.txt (licence
blocks), tools/fonts.sha256, tools/nations/partials/fonts-names.css, the nations entries of vercel.json and the
nations block of sitemap.xml. Every value reaches a page through html.escape; URLs pass only when they match
^https://[^\\s"<>]+$. Strings are set as text, never as markup.
"""
import argparse
import base64
import datetime
import filecmp
import gzip
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import nations_lib as L  # noqa: E402
import nations_directory as D  # noqa: E402
from nations_context import Context  # noqa: E402
from nations_fold import fold, js as fold_js  # noqa: E402

SITE = "https://zotheos.org"
URL_OK = re.compile(r'^https://[^\s"<>]+$')
KIND_LABEL = {"today": "Today", "language": "Language", "land": "Land", "governance": "Governance",
              "culture": "Culture", "population": "Population", "history": "History", "achievement": "Achievement"}
SUPPORT = [("about", "How this is made"), ("sources", "Sources"), ("resources", "Resources"), ("directory", "Directory"), ("coverage", "Where we are"), ("credits", "Credits"),
           ("verification", "Verification"), ("for-nations", "For nations"), ("changes", "Corrections and removals")]
NAV = [("Today", "/nations#today", "hub"), ("Find", "/nations#find", None), ("Regions", "/nations#regions", None),
       ("Coverage", "/nations/coverage", "coverage"), ("About", "/nations/about", "about"),
       ("For nations", "/nations/for-nations", "for-nations")]
SHEET = NAV + [("Directory", "/nations/directory", "directory"), ("Resources", "/nations/resources", "resources"), ("Sources", "/nations/sources", "sources"), ("Credits", "/nations/credits", "credits"),
               ("Verification", "/nations/verification", "verification"), ("Changes", "/nations/changes", "changes")]
POLICY = ("default-src 'none'; base-uri 'none'; object-src 'none'; script-src {scripts}; script-src-attr 'none'; "
          "style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src {connect}; "
          "form-action 'none'; frame-src 'none'; worker-src 'none'; manifest-src 'none'; frame-ancestors 'none'")
GENERATED = ["nations.html", "nations", "static/nations", "static/fonts", "tools/fonts.sha256",
             "tools/nations/partials/fonts-names.css", "vercel.json", "sitemap.xml"]
FONTS_FONTS_URL = "/static/fonts/instrument-serif-latin.woff2"
# herald.js: the spec estimated 12 KB and budgeted 16 KB; ring, walk, search with the emitted fold, card validation and
# the ring list come to about 26 KB unminified, so the gate holds it at 28 KB (reported as a deviation).
BUDGET = {"hub_gz": 60 * 1024, "page_gz": 12 * 1024, "herald_raw": 28 * 1024, "css_gz": 14 * 1024}


class BuildError(Exception):
    pass


# ------------------------------------------------------------------------------------------------ small helpers
def esc(s):
    return html.escape(str(s), quote=True)


def url(u):
    if not isinstance(u, str) or not URL_OK.match(u):
        raise BuildError(f"refused URL {u!r}")
    return esc(u)


def render(tpl, vals):
    def raw(m):
        k = m.group(1)
        if k not in vals:
            raise BuildError(f"template value {k} missing")
        return str(vals[k])

    def plain(m):
        k = m.group(1)
        if k not in vals:
            raise BuildError(f"template value {k} missing")
        return esc(vals[k])
    out = re.sub(r"\{\{\{(\w+)\}\}\}", raw, tpl)
    return re.sub(r"\{\{(\w+)\}\}", plain, out)


def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def wr(p, text):
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def sha8(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()[:8]


def b64hash(body):
    return "'sha256-" + base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii") + "'"


def jdump(obj, pretty=False):
    if pretty:
        return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def mailto(contact, subject, body):
    q = urllib.parse.urlencode({"subject": subject, "body": body}, quote_via=urllib.parse.quote)
    return f"mailto:{contact}?{q}"


def ext(href, text, cls=None):
    c = f' class="{cls}"' if cls else ""
    return (f'<a{c} href="{url(href)}" rel="noopener noreferrer" target="_blank">{text}'
            f'<span class="sr-only"> (opens in a new tab)</span></a>')


def time_el(iso):
    return f'<time datetime="{esc(iso)}">{esc(L.fmt_date(iso))}</time>'


DOT = '<span class="hr-dot" aria-hidden="true">&middot;</span>'
FRET = '<svg class="fret" viewBox="0 0 10 10" aria-hidden="true" focusable="false"><use href="#fret-mini"/></svg>'


def maya(n):
    bars, dots = divmod(n, 5)
    return '<span class="maya-num">' + '<span class="b"></span>' * bars + '<span class="d"></span>' * dots + "</span>"


# ------------------------------------------------------------------------------------------------ the builder
class Builder:
    def __init__(self, root, build_date=None, game_json=False):
        self.root = root
        self.game_json = game_json
        self.model = L.Model(root, build_date)
        if self.model.errors:
            raise BuildError("data: " + "; ".join(self.model.errors))
        self.m = self.model
        collisions = {n["id"] for n in self.m.nations} & {key for key, _ in SUPPORT}
        if collisions:
            raise BuildError("nation ids collide with support pages: " + ", ".join(sorted(collisions)))
        self.brand = L.BrandCover(root)
        self.part = lambda n: rd(os.path.join(root, "tools", "nations", "partials", n))
        self.tpl = lambda n: rd(os.path.join(root, "tools", "nations", "templates", n + ".html"))
        self.contact = self.m.site["contact"]
        self.decide()

    # ---- typographic decisions (11.2, 11.5), shipped in the shard
    def line_face(self, s):
        return "brand" if self.brand.sans_ok(s) else "names"

    def decide(self):
        for n in self.m.nations:
            n["sz"] = L.size_class(n["name"])
            n["sc"] = L.script_of(n["name"])
            n["fc"] = "brand" if (n["sc"] == "latn" and self.brand.serif_ok(n["name"])) else "names"
            n["af"] = self.line_face(", ".join(n["also"][:2])) if n["also"] else "brand"
            n["af_all"] = self.line_face(", ".join(n["also"])) if n["also"] else "brand"
            n["sf"] = self.line_face(n["pronounce"]["text"]) if n["pronounce"] else "brand"
            n["lf"] = self.line_face(n["lands"])
            for f in n["facts"]:
                f["fc"] = self.line_face(f["text"])
            pref = [f for f in n["facts"] if f["kind"] in L.PREF_KINDS]
            n["card_fact"] = (pref or n["facts"] or [None])[0]

    # ---- data files
    def card(self, n):
        c = {"id": n["id"], "n": n["name"], "a": n["also"][:2], "l": n["lands"], "r": n["region"], "sz": n["sz"],
             "fc": n["fc"], "sc": n["sc"], "t": n["tier"], "f": []}
        if n["pronounce"]:
            c["s"] = {"t": n["pronounce"]["text"], "u": n["pronounce"]["url"], "p": n["pronounce"]["publisher"]}
            if n["sf"] == "names":
                c["sf"] = "names"
        if n["official_url"]:
            c["o"] = n["official_url"]
        if n["af"] == "names":
            c["af"] = "names"
        if n["lf"] == "names":
            c["lf"] = "names"
        for f in n["facts"]:
            ff = {"t": f["text"], "k": f["kind"], "p": f["publisher"], "u": f["url"], "d": f["date"],
                  "h": f["human"], "g": f["grace"]}
            if f["as_of"]:
                ff["y"] = f["as_of"]
            if f["grace"]:
                ff["c"] = f["note"]
            if f["fc"] == "names":
                ff["fc"] = "names"
            c["f"].append(ff)
        return c

    def build_data(self, out):
        d = os.path.join(out, "static", "nations")
        os.makedirs(d, exist_ok=True)
        keep, regions = set(), []
        for r in self.m.regions:
            cards = [self.card(n) for n in r["ab"]]
            files = []
            for k in range(0, max(1, len(cards)), 100):
                chunk = cards[k:k + 100]
                key = r["key"] if len(cards) <= 100 else f"{r['key']}-{k // 100 + 1}"
                body = jdump({"r": r["key"], "n": chunk})
                name = f"{key}.{sha8(body)}.json"
                wr(os.path.join(d, name), body)
                keep.add(name)
                files.append(name)
            regions.append({"k": r["key"], "d": r["display"], "n": len(r["nations"]), "ab": len(r["ab"]), "s": files})
        ring = self.m.ring()
        first_r, first_n, first_f = ring[0]
        self.first = (first_r, first_n, first_f)
        index = {"v": self.m.version, "built": self.m.build_date, "major": self.m.major, "shardSize": 100,
                 "regions": regions, "nations": len(self.m.nations), "lastCheck": self.m.last_full_check(),
                 "compiled": self.m.compiled,
                 "first": {"k": first_r["key"], "i": first_r["ab"].index(first_n), "date": self.m.build_date,
                           "n": first_n["name"], "l": first_n["lands"], "t": first_f["text"],
                           "face": first_n["sc"] if first_n["sc"] != "latn" else first_n["fc"]}}
        self.index_json = jdump(index)
        wr(os.path.join(d, "index.json"), self.index_json)
        keep.add("index.json")
        rows = []
        for n in sorted(self.m.nations, key=lambda n: (fold(n["name"]), n["id"])):
            rows.append([n["id"], n["name"], n["also"], n["also_search"], n["lands"], n["region"], n["countries"],
                         n["fc"], n["sc"]])
        search = {"v": self.m.version, "regions": {r["key"]: r["display"] for r in self.m.regions},
                  "countries": {c: self.m.countries[c] for c in sorted(self.m.by_country)}, "n": rows}
        wr(os.path.join(d, "search.json"), jdump(search))
        keep.add("search.json")
        self.status = self.status_obj()
        wr(os.path.join(d, "status.json"), jdump(self.status))
        keep.add("status.json")
        self.coverage = self.coverage_obj()
        wr(os.path.join(d, "coverage.json"), jdump(self.coverage))
        keep.add("coverage.json")
        wr(os.path.join(d, "news.json"), jdump(self.news_obj()))
        keep.add("news.json")
        if self.game_json:
            wr(os.path.join(d, "game.json"), jdump(self.game_obj()))
            keep.add("game.json")
        css = self.css()
        name = f"nations.{sha8(css)}.css"
        wr(os.path.join(d, name), css)
        keep.add(name)
        self.css_name, self.css_text = name, css
        for f in os.listdir(d):
            if f not in keep:
                os.remove(os.path.join(d, f))

    def status_obj(self):
        last = self.m.history[0] if self.m.history else None
        run = None
        if last:
            run = {k: last.get(k) for k in ("run_date", "sample", "urls_checked", "urls_total", "facts_checked",
                                              "verified", "stale", "unreachable")}
            run["date"] = run.pop("run_date")
        c = self.m.counts
        return {"built": self.m.build_date, "data_version": self.m.version, "nations": len(self.m.nations),
                "facts_shown": c["shown"], "facts_review": c["review"], "facts_rechecking": c["rechecking"],
                "facts_waiting": c["waiting"], "facts_grace": c["grace"], "facts_human": c["human"],
                "facts_verified": c["verified_status"], "last_full_check": self.m.last_full_check(), "last_run": run,
                "compiled": self.m.compiled, "check_mode": self.m.site["check_mode"],
                "news_gathered": self.m.news_items.get("gathered") if self.m.news_flags.get("shelf_visible") else None}

    def coverage_obj(self):
        def stats(ns):
            return {"listed": len(ns), "a": sum(n["tier"] == "A" for n in ns), "b": sum(n["tier"] == "B" for n in ns),
                    "c": sum(n["tier"] == "C" for n in ns), "pronounce": sum(bool(n["pronounce"]) for n in ns),
                    "rechecking": sum(n["rechecking"] for n in ns), "review": sum(n["review"] for n in ns)}
        regions = [dict(stats(r["nations"]), key=r["key"], display=r["display"]) for r in self.m.regions]
        countries = []
        for c, ns in self.m.by_country.items():
            u = self.m.universe.get("countries", {}).get(c)
            countries.append(dict(stats(ns), code=c, name=self.m.countries[c],
                                  denominator=u["text"] if u else None, source=u["source"] if u else None))
        regions.sort(key=lambda x: (x["listed"], x["display"]))
        countries.sort(key=lambda x: (x["listed"], x["name"]))
        return {"built": self.m.build_date, "nations": len(self.m.nations), "facts_shown": self.m.counts["shown"],
                "regions": regions, "countries": countries, "last_full_check": self.m.last_full_check()}

    def news_obj(self):
        if not self.m.news_flags.get("shelf_visible"):
            return {"shelf": False, "gathered": None, "items": [], "outlets": []}
        items = self.m.news_items.get("items", [])
        outlets = [{"name": o["name"], "label": o["label"], "region": o["region"]}
                   for o in self.m.news_sources["outlets"] if o.get("enabled") and o.get("leadership")]
        return {"shelf": True, "gathered": self.m.news_items.get("gathered"), "items": items, "outlets": outlets}

    def game_obj(self):
        rdisp = {r["key"]: r["display"] for r in self.m.regions}
        out = []
        for n in self.m.nations:
            if not n["facts"]:
                continue
            e = {"id": n["id"], "name": n["name"], "also": n["also"], "lands": n["lands"],
                 "countries": [self.m.countries[c] for c in n["countries"]], "region": rdisp[n["region"]],
                 "facts": [{"text": f["text"], "kind": f["kind"], "as_of": f["as_of"],
                            "source": {"title": f["title"], "publisher": f["publisher"], "url": f["url"],
                                       "accessed": f["date"]}} for f in n["facts"]]}
            if n["official_url"]:
                e["official_url"] = n["official_url"]
            if n["pronounce"]:
                e["pronounce"] = {"text": n["pronounce"]["text"], "source_url": n["pronounce"]["url"]}
            out.append(e)
        return {"updated": self.m.build_date, "nations": out}

    def css(self):
        text = self.part("tokens.css") + "\n" + self.part("nations.css")
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s*([{};,>])\s*", r"\1", text)
        text = text.replace(";}", "}").strip()
        return text + "\n"

    # ---- page frame
    def frame(self, page_key, path, title, description, body, hub=False):
        cur = lambda k: ' aria-current="page"' if k is not None and k == page_key else ""
        nav = "\n".join(f'      <a href="{esc(h)}"{cur(k)}>{esc(t)}</a>' for t, h, k in NAV)
        sheet = "\n".join(
            f'    <li><a href="{esc(h)}"{cur(k)}><span class="ns-num" aria-hidden="true">{maya(i + 1)}</span>'
            f'<span class="ns-name">{esc(t)}</span></a></li>' for i, (t, h, k) in enumerate(SHEET))
        header = render(self.part("header.html"), {"nav_links": nav, "sheet_links": sheet})
        policy = self.hub_policy if hub else self.page_policy
        head = render(self.part("head.html"), {
            "csp": L_meta(policy), "title": title, "description": description, "canonical": SITE + path,
            "bootstrap": self.bootstrap, "fonts_brand": self.fonts_brand, "fonts_names": self.fonts_names,
            "css": self.css_name, "header": header})
        footer = render(self.part("footer.html"), {"year": self.m.build_date[:4], "contact": self.contact,
                                                   "fonts_line": self.fonts_line, "check_line": self.check_line})
        scripts = render(self.part("scripts.html"), {"appearance": self.appearance})
        return head, footer, scripts

    def page(self, page_key, path, title, description, body):
        head, footer, scripts = self.frame(page_key, path, title, description, body)
        return render(self.tpl("page"), {"head": head, "body": body, "footer": footer, "scripts": scripts})

    # ---- shared fragments
    def name_el(self, n, tag="span", cls="nm", extra=""):
        return (f'<{tag} class="{cls}" dir="auto" data-size="{n["sz"]}" data-face="{n["fc"]}" data-script="{n["sc"]}"'
                f'{extra}>{esc(n["name"])}</{tag}>')

    def face_attr(self, face):
        return ' data-face="names"' if face == "names" else ""

    def receipt(self, f, nation=None, short=False):
        parts = []
        if f["as_of"] and not short:
            parts.append(f"As of {esc(f['as_of'])}")
        label = f"Source: {esc(f['publisher'])}" if short else f"Source: {esc(f['publisher'])}, {esc(f['title'])}"
        parts.append(ext(f["url"], label))
        parts.append(("Checked by a person on " if f["human"] else "Checked ") + time_el(f["date"]))
        if f["grace"] and f["note"]:
            parts.append("Our tool could not reach the page on " + time_el(f["note"]))
        if nation is not None:
            body = (f"Nation: {nation['name']} ({nation['id']})\nFact: {f['id']}\nWhat is wrong:\n\n"
                    "A source that shows the correction (address of the page), optional:\n\n"
                    "If you write for the nation, say so and we act within 72 hours.")
            href = mailto(self.contact, f"Nations correction: {nation['id']} {f['id']}", body)
            parts.append(f'<a href="{esc(href)}">Suggest a correction to this fact</a>')
        return f" {DOT} ".join(parts)

    def herald_card(self, r, n, f):
        cls = ["hr-card"]
        also = n["also"][:2]
        if not also:
            cls.append("no-also")
        if not n["pronounce"]:
            cls.append("no-say")
        out = [f'      <article class="{" ".join(cls)}" id="heraldCard">',
               '        <div class="hr-head">',
               f'          <p class="hr-region">{esc(r["display"])}</p>',
               "          " + self.name_el(n, "h2", "hr-name"),
               '          <span class="hr-line" aria-hidden="true"></span>',
               "        </div>"]
        if also:
            out.append(f'        <p class="hr-also"{self.face_attr(n["af"])}><span class="hr-k">Also known as</span> '
                       f'{esc(", ".join(also))}</p>')
        if n["pronounce"]:
            p = n["pronounce"]
            out.append(f'        <p class="hr-say"{self.face_attr(n["sf"])}><span class="hr-k">Say it</span> {esc(p["text"])}'
                       f' {ext(p["url"], "Pronunciation: " + esc(p["publisher"]))}</p>')
        out.append(f'        <p class="hr-lands"{self.face_attr(n["lf"])}><span class="hr-k">Lands</span> {esc(n["lands"])}</p>')
        out.append(f'        <p class="hr-fact"{self.face_attr(f["fc"])}>{esc(f["text"])}</p>')
        rc = [ext(f["url"], "Source: " + esc(f["publisher"]))]
        if f["as_of"]:
            rc.append(f"As of {esc(f['as_of'])}")
        rc.append(("Checked by a person on " if f["human"] else "Checked ") + time_el(f["date"]))
        if f["grace"] and f["note"]:
            rc.append("Our tool could not reach the page on " + time_el(f["note"]))
        out.append(f'        <p class="hr-receipt">{f" {DOT} ".join(rc)}</p>')
        more = f'<a href="/nations/{esc(n["id"])}">Open this nation</a>'
        if n["official_url"]:
            more += " " + ext(n["official_url"], "Nation's own site")
        out.append(f'        <p class="hr-more">{more}</p>')
        out.append("      </article>")
        return "\n".join(out)

    # ---- the hub
    def hub(self):
        ring = self.m.ring()
        r0, n0, f0 = ring[0]
        rows = []
        for r, n, f in ring:
            rows.append(f'          <li><a class="row" href="/nations/{esc(n["id"])}">{self.name_el(n)}'
                        f'<span class="row-m">{esc(r["display"])}</span>'
                        f'<span class="row-l"{self.face_attr(n["lf"])}>{esc(L.cut_words(n["lands"], 8))}</span></a></li>')
        regions = []
        for r in sorted(self.m.regions, key=lambda r: r["display"]):
            cs = ", ".join(self.m.countries[c] for c in r["countries"])
            regions.append(f'        <li><a class="row" href="/nations/region/{esc(r["key"])}"><span class="row-t">'
                           f'{esc(r["display"])}</span><span class="row-m">{len(r["nations"])} nations</span>'
                           f'<span class="row-l">{esc(cs)}</span></a></li>')
        countries = []
        for c in sorted(self.m.by_country, key=lambda c: self.m.countries[c]):
            countries.append(f'        <li><a class="cc" href="/nations/in/{c.lower()}">{esc(self.m.countries[c])} '
                             f'<span>{len(self.m.by_country[c])}</span></a></li>')
        un = self.m.universe["global"][0]
        cov = (f"{L.fmt_int(len(self.m.nations))} nations, {L.fmt_int(self.m.counts['shown'])} checked facts, "
               f"{len(self.m.regions)} regions, {len(self.m.by_country)} countries. "
               f'<a href="{url(un["url"])}" rel="noopener noreferrer" target="_blank">The United Nations estimates 476 million '
               f'Indigenous people in 90 countries and about 5,000 distinct cultures<span class="sr-only"> (opens in a new tab)'
               f'</span></a>, so this list is a beginning. Thin regions are listed first on the coverage page.')
        status_line = f"1 of 15 in today's ring · {L.fmt_int(len(self.m.nations))} nations · {self.check_short}"
        body_hub = ("What is wrong:\n\nA source that shows the correction (address of the page), optional:\n\n"
                    "If you write for the nation, say so and we act within 72 hours.")
        head, footer, scripts = self.frame("hub", "/nations", "Indigenous nations today | ZOTHEOS", self.hub_description,
                                           "", hub=True)
        return render(self.tpl("hub"), {
            "head": head, "footer": footer, "scripts": scripts, "first_card": self.herald_card(r0, n0, f0),
            "ring_marks": "".join('<span class="g">' + "".join('<i class="on"></i>' if g == 0 and i == 0 else "<i></i>"
                                                               for i in range(5)) + "</span>" for g in range(3)),
            "status_line": status_line, "ring_date": L.fmt_date(self.m.build_date),
            "ring_rows": "\n".join(rows), "region_rows": "\n".join(regions), "country_rows": "\n".join(countries),
            "coverage_para": cov, "panel": self.panel(), "contact": self.contact,
            "mail_hub": mailto(self.contact, "Nations correction", body_hub), "news_shelf": self.news_shelf(),
            "index_json": self.index_json, "herald": self.herald})

    def panel(self):
        s, lfc = self.status, self.m.last_full_check()
        run = s["last_run"]
        if lfc:
            v1, s1 = L.fmt_date(lfc), "full check"
            full = next(h for h in self.m.history if h["run_date"] == lfc)
            v2, s2 = f"{L.fmt_int(full['urls_checked'])} of {L.fmt_int(full['urls_total'])}", "source pages reached"
        else:
            v1, s1 = L.fmt_date(self.m.compiled), "compiled"
            v2 = "none yet"
            s2 = (f"a sample run of {run['urls_checked']} of {L.fmt_int(run['urls_total'])} pages was made on "
                  f"{L.fmt_date(run['date'])}") if run and run.get("sample") else ""
        c = self.m.counts
        v4 = f"{c['hidden']} hidden, {c['waiting']} waiting for a person"
        s4 = f"{c['review']} under review by an editor" if c["review"] else ""
        cell = lambda t, v, sm: (f'        <div><dt>{esc(t)}</dt><dd>{esc(v)}' +
                                 (f"<small>{esc(sm)}</small>" if sm else "") + "</dd></div>")
        out = ['      <dl class="panel">', cell("Last check", v1, s1), cell("Sources reached", v2, s2),
               cell("Facts verified", L.fmt_int(c["verified_status"]), ""), cell("Hidden or waiting", v4, s4), "      </dl>"]
        for sentence in self.state_sentences():
            if s2 and sentence.startswith("A sample run"):
                continue   # already said under Sources reached
            out.append(f'      <p class="note">{esc(sentence)}</p>')
        out.append('      <p class="note" id="vpOverdue" hidden></p>')
        out.append('      <p class="act"><a class="txt-link" href="/nations/verification">What was checked, and what a check '
                   'cannot tell you</a></p>')
        return "\n".join(out)

    def state_sentences(self):
        lfc, run = self.m.last_full_check(), self.status["last_run"]
        out = []
        if not lfc:
            out.append("No full check has been published yet. Every fact shows the date its supporting words were found "
                       "when it was compiled.")
            if run and run.get("sample"):
                out.append(f"A sample run of {run['urls_checked']} of {L.fmt_int(run['urls_total'])} pages was made on "
                           f"{L.fmt_date(run['date'])}.")
        else:
            full = next(h for h in self.m.history if h["run_date"] == lfc)
            out.append(f"Last check {L.fmt_date(lfc)}. {L.fmt_int(full['urls_checked'])} of "
                       f"{L.fmt_int(full['urls_total'])} source pages reached. Changes from a check go live after review.")
            if L.days_between(lfc, self.m.build_date) > L.OVERDUE_DAYS:
                out.append(f"Verification is overdue. The last published check ran on {L.fmt_date(lfc)}. Facts stay shown "
                           "with their last checked date.")
        return out

    def news_shelf(self):
        news = self.news_obj()
        if not news["shelf"]:
            return ""
        rdisp = {r["key"]: r["display"] for r in self.m.regions}
        items = []
        for it in news["items"]:
            lang = f' lang="{esc(it["lang"])}"' if it.get("lang") else ""
            items.append(f'        <li class="row"><span class="row-t"{lang}>{ext(it["link"], esc(it["title"]))}</span>'
                         f'<span class="row-m">{esc(it["outlet"])} {DOT} {time_el(it["date"])}</span></li>')
        have = {o["region"] for o in news["outlets"]}
        missing = [d for k, d in rdisp.items() if not any(k.startswith(h) or h == k for h in have)]
        outlets = ", ".join(f"{esc(o['name'])} ({esc(o['label'])})" for o in news["outlets"])
        gathered = news["gathered"] or ""
        return "\n".join([
            '    <section class="sec" id="news" aria-labelledby="newsH">',
            '      <p class="eyebrow"><svg class="fret" viewBox="0 0 10 10" aria-hidden="true" focusable="false"><use href="#fret-mini"/></svg>From Indigenous-led newsrooms</p>',
            '      <h2 class="sec-h" id="newsH">Headlines</h2>',
            f'      <p class="note">Headlines gathered {esc(gathered)}</p>',
            '      <ul class="rows">', *items, "      </ul>",
            f'      <p class="note">Outlets: {outlets}.</p>',
            f'      <p class="note">No headline source yet for: {esc(", ".join(missing))}.</p>' if missing else "",
            "    </section>"])

    # ---- nation, region, country
    def nation_context(self, n):
        if not hasattr(self, "_nation_context"):
            try:
                self._nation_context = Context(self.root, self.m)
            except (ValueError, OSError) as exc:
                raise BuildError(str(exc)) from exc
        return self._nation_context.page(n["id"])

    def nation_page(self, n):
        r = self.m.region_by_key[n["region"]]
        meta = []
        if n["also"]:
            meta.append(f'    <p{self.face_attr(n["af_all"])}><span class="lbl">Also known as</span> {esc(", ".join(n["also"]))}</p>')
        if n["pronounce"]:
            p = n["pronounce"]
            meta.append(f'    <p{self.face_attr(n["sf"])}><span class="lbl">Say it</span> {esc(p["text"])} '
                        f'{ext(p["url"], "Pronunciation: " + esc(p["publisher"]), "credit-link")}</p>')
        own = (f'  <p class="n-own">{ext(n["official_url"], "Visit the nation&#39;s own site", "pill")}</p>'
               if n["official_url"] else "")
        cs = ", ".join(f'<a href="/nations/in/{c.lower()}">{esc(self.m.countries[c])}</a>' for c in n["countries"])
        facts = []
        for f in n["facts"]:
            facts.append(f'    <article class="fact"><p class="kind">{KIND_LABEL[f["kind"]]}</p>'
                         f'<p class="fact-t"{self.face_attr(f["fc"])}>{esc(f["text"])}</p>'
                         f'<p class="rc">{self.receipt(f, n)}</p></article>')
        counts = []
        if not n["facts"]:
            counts.append("Facts in progress. This entry lists the nation by its own name while facts are compiled and checked.")
        if n["rechecking"]:
            counts.append("1 fact is being re-checked." if n["rechecking"] == 1 else f"{n['rechecking']} facts are being re-checked.")
        if n["review"]:
            counts.append("1 fact is under review." if n["review"] == 1 else f"{n['review']} facts are under review.")
        k = len(n["facts"])
        dots = (f'<span class="cdots" aria-hidden="true">{"<i></i>" * min(k, 5)}</span><span class="fcount">{k}</span>'
                if k else "")
        body_n = (f"Nation: {n['name']} ({n['id']})\nWhat is wrong:\n\n"
                  "A source that shows the correction (address of the page), optional:\n\n"
                  "If you write for the nation, say so and we act within 72 hours.")
        context = self.nation_context(n)
        # Native section links move keyboard focus as well as the reading position.
        if context:
            context = context.replace('id="nContext"', 'id="nContext" tabindex="-1"', 1)
        reading = ['<nav class="nation-reading" aria-labelledby="nReadingTitle">',
                   '<p class="lbl" id="nReadingTitle">Explore This Record</p><ul>',
                   '<li><a href="#nLands">Lands</a></li>',
                   '<li><a href="#nFacts">Facts And Sources</a></li>']
        if context:
            reading.append('<li><a href="#nContext">Context And Resources</a></li>')
        reading.append('</ul></nav>')
        body = render(self.tpl("nation"), {
            "region_key": r["key"], "region_display": r["display"], "sz": n["sz"], "fc": n["fc"], "sc": n["sc"],
            "name": n["name"], "meta": "\n".join(meta), "own": own, "lands": n["lands"],
            "lands_face": self.face_attr(n["lf"]), "countries": cs, "fact_dots": dots, "facts": "\n".join(facts),
            "counts": "\n".join(f'    <p class="counts">{esc(c)}</p>' for c in counts),
            "context": context, "reading_navigation": "\n".join(reading),
            "mail_nation": mailto(self.contact, f"Nations correction: {n['id']}", body_n)})
        first = n["facts"][0]["text"] if n["facts"] else ""
        desc = L.cut_chars(f"{n['name']}: {n['lands']}. {first}".strip(), 155)
        return self.page(None, f"/nations/{n['id']}", f"{n['name']} | Indigenous nations today", desc, body)

    def cards(self, nations):
        out = []
        for n in nations:
            f = n["card_fact"]
            bits = [f'    <li class="card">', f'      <h2 class="nm-h">{self.name_el(n, "a", "nm", " href=" + chr(34) + "/nations/" + esc(n["id"]) + chr(34))}</h2>']
            if n["also"]:
                bits.append(f'      <p class="c-l"{self.face_attr(self.line_face(n["also"][0]))}><span class="lbl">Also known as</span> {esc(n["also"][0])}</p>')
            bits.append(f'      <p class="c-l"{self.face_attr(n["lf"])}><span class="lbl">Lands</span> {esc(n["lands"])}</p>')
            if f:
                bits.append(f'      <p class="c-f"{self.face_attr(f["fc"])}>{esc(f["text"])}</p>')
                bits.append(f'      <p class="rc">{self.receipt(f, short=True)}</p>')
            else:
                bits.append('      <p class="c-l">Facts in progress. This entry lists the nation by its own name while facts are compiled and checked.</p>')
            bits.append(f'      <p><a class="txt-link" href="/nations/{esc(n["id"])}">Open this nation</a></p>')
            bits.append("    </li>")
            out.append("\n".join(bits))
        return "\n".join(out)

    def region_page(self, r):
        cnt = len(r["nations"])
        body = render(self.tpl("region"), {
            "eyebrow": "Region", "heading": r["display"],
            "lede": f"{cnt} nations of {r['display']}, each with its own name first and checked facts with sources.",
            "count_label": f"{cnt} nations", "cards": self.cards(r["nations"])})
        desc = L.cut_chars(f"{cnt} Indigenous nations of {r['display']}, each by its own name, with checked facts and "
                           "the source of every fact.", 155)
        return self.page(None, f"/nations/region/{r['key']}", f"{r['display']} | Indigenous nations today", desc, body)

    def country_page(self, c):
        ns, name = self.m.by_country[c], self.m.countries[c]
        lede = (f"{len(ns)} nations list {name} among their present-day countries." if len(ns) != 1 else
                f"1 nation lists {name} among its present-day countries.")
        body = render(self.tpl("country"), {"heading": name, "lede": lede,
                                            "count_label": f"{len(ns)} {L.plural(len(ns), 'nation', 'nations')}",
                                            "cards": self.cards(ns)})
        return self.page(None, f"/nations/in/{c.lower()}", f"{name} | Indigenous nations today",
                         L.cut_chars(lede + " Each by its own name, with checked facts and their sources.", 155), body)

    # ---- support pages
    def support_pages(self):
        return {
            "about": self.about(), "sources": self.sources(), "resources": self.resources(), "directory": self.directory_page(), "coverage": self.coverage_page(),
            "credits": self.credits(), "verification": self.verification(), "for-nations": self.for_nations(),
            "changes": self.changes_page()}

    def sp(self, key, body, description):
        title = dict(SUPPORT)[key] + " | Indigenous nations today"
        return self.page(key, f"/nations/{key}", title, description, body)

    def about(self):
        g = self.m.universe["global"]
        scale = (f'  <p>The United Nations estimates 476 million Indigenous people living in 90 countries, who represent '
                 f'about 5,000 different cultures ({ext(g[0]["url"], "United Nations, " + esc(g[0]["title"]))}, read '
                 f'{L.fmt_date(g[0]["accessed"])}). The World Bank gives 476.6 million, 6.2 percent of the world&#39;s people '
                 f'({ext(g[1]["url"], "World Bank, " + esc(g[1]["title"]))}, read {L.fmt_date(g[1]["accessed"])}), while the '
                 f'same UN page says less than 5 per cent. The sources differ, and both are shown.</p>\n'
                 f'  <p>This list holds {L.fmt_int(len(self.m.nations))} nations. It is a beginning, and the '
                 f'<a href="/nations/coverage">coverage page</a> says where it is thin.</p>')
        return self.sp("about", render(self.tpl("about"), {
            "user_agent": "ZOTHEOS-nations-verifier/1 (+https://zotheos.org)", "fonts_line": self.fonts_line,
            "scale": scale, "type_sample": self.type_sample()}),
            "How Indigenous nations today is made: sources, the weekly check, the daily ring, editorial responsibility and the typefaces.")

    def type_sample(self):
        rows, used = [], set()

        def add(caption, text, face, script="latn", kind="name"):
            if text in used:
                return
            used.add(text)
            if kind == "name":
                el = f'<span class="nm" dir="auto" data-size="m" data-face="{face}" data-script="{script}">{esc(text)}</span>'
            else:
                el = f'<span class="fact-t"{self.face_attr(face)} dir="auto">{esc(text)}</span>'
            rows.append(f'  <div class="type-s">{el}<span class="lbl">{esc(caption)}</span></div>')
        ns = self.m.nations
        brand = next(n for n in ns if n["fc"] == "brand" and any(ord(c) > 127 for c in n["name"]))
        add("Name in the brand serif, Instrument Serif", brand["name"], "brand")
        for n in ns:
            if n["fc"] == "names" and n["sc"] == "latn":
                add("Name whole in ZN Serif", n["name"], "names")
        for label, pred in (("Other name with Canadian Syllabics, ZN Syllabics", lambda s: any(0x1400 <= ord(c) <= 0x167F for c in s)),
                            ("Other name in Cherokee, ZN Cherokee", lambda s: any(0x13A0 <= ord(c) <= 0x13FF for c in s)),
                            ("Other name in Cyrillic, ZN Sans", lambda s: any(0x400 <= ord(c) <= 0x4FF for c in s))):
            hit = next((a for n in ns for a in n["also"] if pred(a)), None)
            if hit:
                add(label, hit, self.line_face(hit), kind="line")
        title = next((f["title"] for n in ns for f in n["facts"] if any(0x900 <= ord(c) <= 0x97F for c in f["title"])), None)
        if title:
            add("Source title with Devanagari, ZN Devanagari", title, "brand", kind="line")
        okina = next((r["display"] for r in self.m.regions if "ʻ" in r["display"]), None)
        if okina:
            rows.append(f'  <div class="type-s"><span class="lbl">{esc(okina)}</span><span class="lbl">Region label with the '
                        'okina, JetBrains Mono with ZN Mono</span></div>')
        return "\n".join(rows)

    def publishers(self):
        """publisher -> {group, facts, urls: {url: [facts]}} over published facts only."""
        pubs = {}
        for n in self.m.nations:
            for f in n["facts"]:
                p = pubs.setdefault(f["publisher"], {"group": "9", "facts": 0, "urls": {}})
                p["facts"] += 1
                p["urls"].setdefault(f["url"], []).append(f)
                p["group"] = min(p["group"], f["group"])
        for name, p in pubs.items():
            p["slug"] = "p-" + sha8(name)
        return pubs

    def sources(self):
        pubs = self.publishers()
        groups = self.m.priority["groups"]
        out = []
        for g in sorted(groups):
            members = sorted((k for k, p in pubs.items() if p["group"] == g), key=lambda k: (fold(k), k))
            if not members:
                continue
            label = f"Group {g}" if g != "9" else "Unclassified"
            out.append(f'  <section class="src-g" id="g{g}" aria-labelledby="g{g}h"><p class="open-rule">{FRET}'
                       f'<span class="lbl">{esc(label)}</span></p><h2 id="g{g}h">{esc(groups[g])}</h2>')
            for k in members:
                p = pubs[k]
                last = max(f["date"] for fs in p["urls"].values() for f in fs)
                waiting = sum(1 for fs in p["urls"].values() if any(f["grace"] for f in fs))
                state = "all pages reached" if not waiting else f"{waiting} {L.plural(waiting, 'page', 'pages')} waiting for a person"
                out.append(f'    <div class="src-p" id="{p["slug"]}"><h3>{esc(k)}</h3>'
                           f'<p class="row-m">{p["facts"]} {L.plural(p["facts"], "fact", "facts")} {DOT} {len(p["urls"])} '
                           f'{L.plural(len(p["urls"]), "page", "pages")} {DOT} last checked {time_el(last)} {DOT} {state}</p>'
                           '<ul class="src-u">')
                for u, fs in sorted(p["urls"].items()):
                    out.append(f'      <li>{ext(u, esc(u))} {DOT} {len(fs)} {L.plural(len(fs), "fact", "facts")} {DOT} '
                               f'checked {time_el(max(f["date"] for f in fs))}</li>')
                out.append("    </ul></div>")
            out.append("  </section>")
        nurl = len({u for p in pubs.values() for u in p["urls"]})
        lede = (f"{L.fmt_int(len(pubs))} publishers and {L.fmt_int(nurl)} pages are cited by the facts on these pages, "
                "grouped in the order sources are preferred: nations' own pages first. Every page opens only when you follow it.")
        self.n_publishers, self.n_urls = len(pubs), nurl
        return self.sp("sources", render(self.tpl("sources"), {"lede": lede, "groups": "\n".join(out)}),
                       f"Every publisher and page cited on Indigenous nations today: {L.fmt_int(len(pubs))} publishers, "
                       f"{L.fmt_int(nurl)} pages, nations' own sites first.")

    def resources(self):
        catalog = json.loads(rd(os.path.join(self.root, "data", "nations", "resources.json")))
        groups, items = catalog["groups"], catalog["resources"]
        group_ids = [g["id"] for g in groups]
        item_ids = [r["id"] for r in items]
        if (len(set(group_ids)) != len(group_ids) or len(set(item_ids)) != len(item_ids)
                or any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", k) for k in group_ids + item_ids)
                or any(r["group"] not in group_ids or not r["links"] or not r["sources"] for r in items)):
            raise BuildError("resources: invalid ids, group, links or sources")
        known = {n['id'] for n in self.m.raw['nations']}
        for item in items:
            refs = item.get('nation_ids', [])
            if (not isinstance(refs, list) or len(refs) > 16 or len(set(refs)) != len(refs)
                    or any(not isinstance(nid, str) or nid not in known for nid in refs)):
                raise BuildError('resources: invalid canonical nation references')
        # A named composite resource must not bypass any participating nation's publication hold.
        items = [item for item in items if set(item.get('nation_ids', [])) <= self.m.by_id.keys()]
        histories = [n for n in self.m.nations if any(f["kind"] == "history" for f in n["facts"])]
        history_count = sum(f["kind"] == "history" for n in histories for f in n["facts"])
        total = len(self.m.nations)
        out = ['<div class="read n-head prose">', '<p class="eyebrow">Resources</p>',
               '<h1 class="page-h">Go further.</h1>',
               '<p class="lede">Follow official resources, then explore historical context from the nations in this growing list.</p>',
               f'<p class="lede">Our registry currently names {L.fmt_int(total)} nations. It is a growing starting point, '
               'not a complete list of the world\'s Indigenous peoples. '
               '<a href="/nations/coverage">See what is covered and where the gaps are.</a> <a href="/nations/directory">Search the broader directory of names.</a></p>',
               '<nav aria-label="On this page"><ul class="src-u">']
        for group in groups:
            out.append(f'<li><a href="#resource-{esc(group["id"])}">{esc(group["title"])}</a></li>')
        out += ['<li><a href="#history">Explore the histories already recorded</a></li>', '</ul></nav>',
                '<p class="note">These are links to the publishers\' own pages. A listing does not imply a partnership. '
                'External pages open only when you follow a link.</p>']
        for group in groups:
            gid = "resource-" + group["id"]
            out.append(f'<section class="src-g" id="{esc(gid)}" aria-labelledby="{esc(gid)}-title">'
                       f'<h2 id="{esc(gid)}-title">{esc(group["title"])}</h2><p>{esc(group["intro"])}</p>')
            for item in (r for r in items if r["group"] == group["id"]):
                out.append(f'<article class="src-p" id="resource-item-{esc(item["id"])}">'
                           f'<h3>{esc(item["title"])}</h3><p class="row-m">{esc(item["kind"])} {DOT} '
                           f'{esc(item["scope"])}</p><p>{esc(item["summary"])}</p><ul class="src-u">')
                for link in item["links"]:
                    out.append(f'<li>{ext(link["url"], esc(link["label"]))}</li>')
                out.append('</ul><p class="rc">')
                receipts = []
                for source in item["sources"]:
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["accessed"]):
                        raise BuildError("resources: source reviewed date must be YYYY-MM-DD")
                    try:
                        datetime.date.fromisoformat(source["accessed"])
                    except ValueError as exc:
                        raise BuildError("resources: invalid source reviewed date") from exc
                    receipts.append(ext(source["url"], esc(source["publisher"] + ", " + source["title"]))
                                    + ", reviewed " + time_el(source["accessed"]))
                out.append((f" {DOT} ").join(receipts) + '</p></article>')
            out.append('</section>')
        out += ['<section class="src-g" id="history" aria-labelledby="history-title">',
                '<h2 id="history-title">Explore the histories already recorded</h2>',
                f'<p>{L.fmt_int(history_count)} published historical facts across {L.fmt_int(len(histories))} '
                'nations are collected below. Open a name for a short starting point, historical context and sources.</p>',
                f'<p>{L.fmt_int(total - len(histories))} entries have no published fact tagged as history yet. '
                'That is a gap in this collection, not a statement about their history. '
                'Some facts in other categories also describe past events.</p>',
                '<p>These are excerpts, not complete histories. Dates belong to the statements they accompany; '
                'a past event does not establish the situation today. '
                '<a href="/nations/verification">What our checks can and cannot tell you.</a></p>']
        for region in self.m.regions:
            members = [n for n in histories if n["region"] == region["key"]]
            if not members:
                continue
            out.append(f'<section class="src-g" aria-labelledby="history-region-{esc(region["key"])}">'
                       f'<h3 id="history-region-{esc(region["key"])}">{esc(region["display"])}</h3>')
            for n in sorted(members, key=lambda n: (fold(n["name"]), n["id"])):
                historical = [f for f in n["facts"] if f["kind"] == "history"]
                context = [f for f in n["facts"] if f["kind"] != "history"]
                out.append(f'<details class="src-p resource-history" id="history-{esc(n["id"])}"><summary>'
                           + self.name_el(n, "span", "nm row-name") + '</summary>'
                           + f'<p class="note"{self.face_attr(n["lf"])}>{esc(n["lands"])}</p>')
                layers = ([('A starting point', context[:1])] if context else []) + [('Historical context', historical)]
                if len(context) > 1:
                    layers.append(('More from the record', context[1:]))
                for label, facts in layers:
                    out.append(f'<h4 class="kind">{esc(label)}</h4>')
                    for f in facts:
                        out.append(f'<article class="fact" id="history-fact-{esc(f["id"])}">'
                                   f'<p class="fact-t"{self.face_attr(f["fc"])}>{esc(f["text"])}</p>'
                                   f'<p class="rc">{self.receipt(f)}</p></article>')
                out.append(f'<p><a href="/nations/{esc(n["id"])}">Open the full nation page</a></p></details>')
            out.append('</section>')
        out += ['</section>', '<p class="act"><a class="pill" href="/nations#find">Find another nation</a>'
                '<a class="txt-link" href="/nations/for-nations">Corrections and additions from nations</a></p>', '</div>']
        return self.sp("resources", "\n".join(out),
                       "Official learning, advocacy and climate resources, with sourced historical context from the growing nations registry.")

    def directory_page(self):
        try:
            return D.page(self)
        except (ValueError, KeyError, TypeError) as exc:
            raise BuildError("directory: " + str(exc)) from exc

    def coverage_page(self):
        cov, lfc = self.coverage, self.m.last_full_check()
        last = L.fmt_date(lfc) if lfc else "not yet"
        cols = [("Listed", "listed"), ("Tier A", "a"), ("Tier B", "b"), ("Tier C", "c"),
                ("With pronunciation", "pronounce"), ("Facts re-checking", "rechecking")]

        def table(caption, first, rows, keyname, extra=None):
            th = "".join(f'<th scope="col">{esc(c)}</th>' for c, _ in cols)
            if extra:
                th += f'<th scope="col">{esc(extra[0])}</th>'
            out = [f'  <table class="tbl"><caption>{esc(caption)}</caption><thead><tr><th scope="col">{esc(first)}</th>'
                   f'{th}<th scope="col">Last full check</th></tr></thead><tbody>']
            for row in rows:
                cells = "".join(f'<td class="n" data-label="{esc(c)}">{row[k]}</td>' for c, k in cols)
                if extra:
                    cells += f'<td data-label="{esc(extra[0])}">{extra[1](row)}</td>'
                out.append(f'    <tr><th scope="row" data-label="{esc(first)}">{keyname(row)}</th>{cells}'
                           f'<td data-label="Last full check">{esc(last)}</td></tr>')
            out.append("  </tbody></table>")
            return "\n".join(out)

        def denom(row):
            if not row["denominator"]:
                return "denominator not yet confirmed from a primary source"
            s = row["source"]
            return f'{esc(row["denominator"])} ({ext(s["url"], esc(s["publisher"]))})'
        t1 = table("By region, thin regions first", "Region", cov["regions"],
                   lambda r: f'<a href="/nations/region/{esc(r["key"])}">{esc(r["display"])}</a>')
        t2 = table("By present-day country, thin first", "Country", cov["countries"],
                   lambda r: f'<a href="/nations/in/{esc(r["code"].lower())}">{esc(r["name"])}</a>', ("Denominator", denom))
        lede = (f"{L.fmt_int(len(self.m.nations))} nations in {len(self.m.regions)} regions and {len(self.m.by_country)} "
                f"present-day countries, with {L.fmt_int(self.m.counts['shown'])} checked facts. Thin regions come first: "
                "they are the work still to do. Tier A entries have the nation's own site and a fact from it; tier B entries "
                "have at least one checked fact; tier C entries are listed by name while facts are compiled.")
        return self.sp("coverage", render(self.tpl("coverage"), {"lede": esc(lede), "tables": D.coverage(self) + "\n" + t1 + "\n" + t2}),
                       f"Coverage of Indigenous nations today by region and country: {len(self.m.nations)} nations, "
                       "thin regions first, with denominators and their sources.")

    def credits(self):
        roll = []
        for r in sorted(self.m.regions, key=lambda r: r["display"]):
            roll.append(f'  <h3 class="lbl">{esc(r["display"])}</h3>\n  <ul class="roll">')
            for n in r["nations"]:
                roll.append(f'    <li><a href="/nations/{esc(n["id"])}">{self.name_el(n)}</a></li>')
            roll.append("  </ul>")
        pubs, groups = self.publishers(), self.m.priority["groups"]
        out = []
        for g in sorted(groups):
            members = sorted((k for k, p in pubs.items() if p["group"] == g), key=lambda k: (fold(k), k))
            if not members:
                continue
            links = ", ".join(f'<a href="/nations/sources#{pubs[k]["slug"]}">{esc(k)}</a>' for k in members)
            out.append(f'  <p><a href="/nations/sources#g{g}">{esc(groups[g])}</a>: {links}.</p>')
        return self.sp("credits", render(self.tpl("credits"), {"roll": "\n".join(roll), "publishers": "\n".join(out),
                                                               "fonts_line": self.fonts_line}),
                       "Credits for Indigenous nations today: every nation by its own name, every publisher, the people, "
                       "the fonts and the checking tool.")

    def verification(self):
        lfc, hist = self.m.last_full_check(), self.m.history
        run = hist[0] if hist else None
        c = self.m.counts
        secs = []

        def sec(label, inner):
            secs.append(f'  <section><p class="open-rule">{FRET}<span class="lbl">{esc(label)}</span></p>\n{inner}\n  </section>')
        if run:
            mode = "sample run, nothing written" if run.get("sample") else ("full check, published" if run.get("published") else "full check, waiting for review")
            rows = [("Run date", L.fmt_date(run["run_date"])), ("Mode", mode),
                    ("Pages reached", f"{run['urls_checked']} of {L.fmt_int(run['urls_total'])}"),
                    ("Facts checked", f"{run['facts_checked']} of {L.fmt_int(sum(len(n['facts']) for n in self.m.raw['nations']))}"),
                    ("Verified", str(run["verified"])), ("Hidden", str(run["stale"])), ("Waiting", str(run["unreachable"]))]
            if run.get("elapsed_s"):
                rows.append(("Duration", f"{round(run['elapsed_s'])} seconds"))
            tbl = ['  <table class="tbl"><caption>The latest run</caption><tbody>']
            for k, v in rows:
                tbl.append(f'    <tr><th scope="row" data-label="Measure">{esc(k)}</th><td data-label="Value">{esc(v)}</td></tr>')
            tbl.append("  </tbody></table>")
            if run.get("sample"):
                refused = run["unreachable"]
                s = (f"A sample run on {L.fmt_date(run['run_date'])} reached {run['urls_checked']} of "
                     f"{L.fmt_int(run['urls_total'])} source pages and found the cited words on {run['verified']} of the "
                     f"{run['facts_checked']} facts it could test. "
                     + ("" if not refused else ("One page refused the tool and waits for a person. " if refused == 1 else
                                                f"{refused} pages refused the tool and wait for a person. "))
                     + ("No full check has been published yet." if not lfc else ""))
            else:
                s = (f"The check on {L.fmt_date(run['run_date'])} reached {run['urls_checked']} of {L.fmt_int(run['urls_total'])} "
                     f"source pages: {run['verified']} facts verified, {run['stale']} hidden, {run['unreachable']} waiting for a person.")
            sec("This check", "\n".join(tbl) + f"\n  <p>{esc(s.strip())}</p>")
        else:
            sec("This check", "  <p>No check has run yet.</p>")
        # hidden and why: counts per publisher and reason
        reasons = {}
        for n in self.m.nations:
            for f in n["all_facts"]:
                if f["state"] in ("hidden", "waiting"):
                    why = ("The cited words are no longer on the page" if f["state"] == "hidden"
                           else "The page could not be reached")
                    key = (L.bare_host(f["url"]), why)
                    reasons.setdefault(key, {"n": 0, "nations": set()})
                    reasons[key]["n"] += 1
                    reasons[key]["nations"].add(n["name"])
        if reasons:
            lines = []
            for (h, why), v in sorted(reasons.items()):
                tail = f" ({', '.join(sorted(v['nations']))})" if self.m.site.get("hidden_table_names_nations") else ""
                lines.append(f"    <li>{esc(h)}: {v['n']} {L.plural(v['n'], 'fact', 'facts')}, {esc(why.lower())}{esc(tail)}</li>")
            sec("What is hidden and why", "  <ul>\n" + "\n".join(lines) + "\n  </ul>")
        else:
            sec("What is hidden and why", "  <p>Nothing is hidden. Every published fact passed its last check.</p>"
                + (f"\n  <p>{c['review']} {L.plural(c['review'], 'fact is', 'facts are')} held for an editor's review, "
                   "outside the checking tool.</p>" if c["review"] else ""))
        # waiting for a person
        waiting = {}
        for n in self.m.nations:
            for f in n["all_facts"]:
                if f["state"] in ("waiting", "grace", "human"):
                    waiting.setdefault(L.bare_host(f["url"]), []).append(f)
        if waiting:
            lines = []
            for h, fs in sorted(waiting.items()):
                hum = [f for f in fs if f["human"]]
                note = ""
                if hum:
                    d0 = max(f["date"] for f in hum)
                    exp = L.parse_date(d0) + datetime.timedelta(days=L.HUMAN_DAYS)
                    note = f" Checked by a person on {L.fmt_date(d0)}, expires {L.fmt_date(exp)}."
                lines.append(f"    <li>{esc(h)}: {len(fs)} {L.plural(len(fs), 'fact', 'facts')}.{esc(note)}</li>")
            sec("Waiting for a person", "  <ul>\n" + "\n".join(lines) + "\n  </ul>")
        else:
            sec("Waiting for a person", "  <p>No page is waiting for a person.</p>")
        # past checks
        rows = ['  <table class="tbl"><caption>The last runs, newest first</caption><thead><tr><th scope="col">Date</th>'
                '<th scope="col">Pages reached</th><th scope="col">Verified</th><th scope="col">Hidden</th>'
                '<th scope="col">Waiting</th><th scope="col">Published</th></tr></thead><tbody>']
        for h in hist[:12]:
            pub = "sample run, nothing written" if h.get("sample") else (L.fmt_date(h["published"]) if h.get("published") else "waiting for review")
            rows.append(f'    <tr><th scope="row" data-label="Date">{esc(L.fmt_date(h["run_date"]))}</th>'
                        f'<td data-label="Pages reached">{h["urls_checked"]} of {L.fmt_int(h["urls_total"])}</td>'
                        f'<td data-label="Verified">{h["verified"]}</td><td data-label="Hidden">{h["stale"]}</td>'
                        f'<td data-label="Waiting">{h["unreachable"]}</td><td data-label="Published">{esc(pub)}</td></tr>')
        rows.append("  </tbody></table>")
        sec("Past checks", "\n".join(rows))
        sec("How a check works", "\n".join(f"  <p>{esc(p)}</p>" for p in (
            "The tool introduces itself as ZOTHEOS-nations-verifier/1 (+https://zotheos.org). It obeys each site's "
            "robots.txt, sends at most one request to a site every three seconds, waits 20 seconds at most and tries twice "
            "more, and never pretends to be a browser.",
            "It reads the text of the page (for a PDF, the text of the document, with words split across lines joined), "
            "then compares the cited words with the page after the same plain steps on both sides: quotation marks and "
            "dashes made alike, soft hyphens and invisible spaces dropped, spaces collapsed, letter case ignored. It "
            "looks for an exact match first, then a match that ignores accents.",
            "A fact whose words are gone is hidden until a person restores it. Nothing hidden is ever restored by the "
            "tool alone. Changes from a check go live after review.")))
        sec("What a check cannot tell you", "  <p>A pass means the cited words are still on the cited page. It does not mean "
            "the page is right, complete or current, and it does not mean we read the words the way the nation would. "
            "Corrections from nations come first.</p>")
        sec("What the dates mean before the first full check", f"  <p>Checked {esc(L.fmt_date(self.m.compiled))} on a fact "
            "means the date its supporting words were found on the cited page while the fact was compiled. After the first "
            "full check, it means the date the weekly tool last found them.</p>")
        return self.sp("verification", render(self.tpl("verification"), {"sections": "\n".join(secs)}),
                       "The record of every check of Indigenous nations today: what was checked, what is hidden and why, "
                       "and what a check cannot tell you.")

    def for_nations(self):
        body = ("Nation:\nWhat you would like changed or removed:\n\n"
                "If you write for the nation, say so and we act within 72 hours.")
        return self.sp("for-nations", render(self.tpl("for-nations"), {
            "contact": self.contact, "mail_for_nations": mailto(self.contact, "For nations", body)}),
            "How a nation corrects, adds or removes anything on Indigenous nations today. Your word comes first.")

    def changes_page(self):
        ch = sorted(self.m.changes, key=lambda c: c["date"], reverse=True)
        if not ch:
            entries = "  <p>No corrections or removals yet.</p>"
        else:
            items = []
            for c in ch:
                if c.get("nation") and c["nation"] in self.m.by_id:
                    who = f' <a href="/nations/{esc(c["nation"])}">{esc(self.m.by_id[c["nation"]]["name"])}</a>.'
                else:
                    who = ""
                items.append(f'    <li>{time_el(c["date"])}: {esc(c["text"])}{who}</li>')
            entries = "  <ul>\n" + "\n".join(items) + "\n  </ul>"
        return self.sp("changes", render(self.tpl("changes"), {"entries": entries}),
                       "Every correction, name change, removal and restoration on Indigenous nations today, newest first.")

    # ---- everything
    def build(self, out):
        r = self.root
        self.bootstrap = self.part("bootstrap.js")
        self.fonts_brand = self.part("fonts-brand.css")
        landing = rd(os.path.join(r, "index.html"))
        if "<script>" + self.bootstrap + "</script>" not in landing:
            raise BuildError("tools/nations/partials/bootstrap.js no longer matches the landing's first-paint script; "
                             "copy it from index.html")
        if '<style id="zth-fonts">' + self.fonts_brand + "</style>" not in landing:
            raise BuildError("tools/nations/partials/fonts-brand.css no longer matches the landing's zth-fonts block")
        self.fonts_names = self.part("fonts-names.css").rstrip("\n")
        self.appearance = self.part("appearance.js")
        self.herald = self.part("herald.js").replace("  /*@FOLD@*/\n", "  " + fold_js().replace("\n", "\n  ").rstrip() + "\n")
        if "/*@FOLD@*/" in self.herald:
            raise BuildError("herald.js fold placeholder not replaced")
        self.fonts_line = ("Fonts: Instrument Serif, DM Sans and JetBrains Mono, with Tinos, Noto Sans, Cousine, Noto Sans "
                           "Cherokee, Noto Sans Canadian Aboriginal, Noto Sans Devanagari and Noto Sans Tifinagh for letters "
                           "the brand faces lack. All self-hosted under the SIL Open Font License. No letter in a name is "
                           "ever changed to fit a font.")
        lfc = self.m.last_full_check()
        self.check_short = f"Last check {L.fmt_date(lfc)}" if lfc else f"Compiled {L.fmt_date(self.m.compiled)}"
        self.check_line = self.check_short
        self.hub_description = (f"One nation named at a time, as it names itself, with one checked fact and its source. "
                                f"{L.fmt_int(len(self.m.nations))} nations, {L.fmt_int(self.m.counts['shown'])} facts, "
                                "re-checked weekly.")
        self.build_data(out)
        boot_h, app_h = b64hash(self.bootstrap), b64hash(self.appearance)
        self.page_policy = POLICY.format(scripts=f"{boot_h} {app_h}", connect="'none'")
        self.hub_policy = POLICY.format(scripts=f"{boot_h} {app_h} {b64hash(self.index_json)} {b64hash(self.herald)}",
                                        connect="'self'")
        pages = {"nations.html": self.hub()}
        for n in self.m.nations:
            pages[f"nations/{n['id']}.html"] = self.nation_page(n)
        for rg in self.m.regions:
            pages[f"nations/region/{rg['key']}.html"] = self.region_page(rg)
        for c in sorted(self.m.by_country):
            pages[f"nations/in/{c.lower()}.html"] = self.country_page(c)
        for k, text in self.support_pages().items():
            pages[f"nations/{k}.html"] = text
        nd = os.path.join(out, "nations")
        if os.path.isdir(nd):
            shutil.rmtree(nd)
        for rel, text in pages.items():
            wr(os.path.join(out, rel), text)
        self.pages = pages
        self.write_vercel(out)
        self.write_sitemap(out, pages)
        return pages

    def write_vercel(self, out):
        vp = os.path.join(out, "vercel.json")
        conf = json.load(open(vp, encoding="utf-8"))
        ours = [
            {"source": "/nations", "headers": [{"key": "Content-Security-Policy", "value": self.hub_policy}]},
            {"source": "/nations.html", "headers": [{"key": "Content-Security-Policy", "value": self.hub_policy}]},
            {"source": "/nations/(.*)", "headers": [{"key": "Content-Security-Policy", "value": self.page_policy}]},
            {"source": "/static/nations/(.*)\\.([0-9a-f]{8})\\.(json|css)",
             "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]},
            {"source": "/static/nations/(index|status|coverage|news)\\.json",
             "headers": [{"key": "Cache-Control", "value": "public, max-age=300, must-revalidate"}]},
            {"source": "/static/nations/search\\.json",
             "headers": [{"key": "Cache-Control", "value": "public, max-age=3600, must-revalidate"}]},
        ]
        mine = {e["source"] for e in ours}
        conf["headers"] = [e for e in conf.get("headers", []) if e.get("source") not in mine] + ours
        reds = [{"source": f"/nations/{old}", "destination": f"/nations/{new}", "permanent": True}
                for old, new in sorted(self.m.redirects.items())]
        others = [x for x in conf.get("redirects", []) if not x.get("source", "").startswith("/nations/")]
        if reds or others:
            conf["redirects"] = others + reds
        else:
            conf.pop("redirects", None)
        wr(vp, json.dumps(conf, indent=2) + "\n")

    def write_sitemap(self, out, pages):
        sp = os.path.join(out, "sitemap.xml")
        text = rd(sp)
        text = re.sub(r"\n  <!-- nations:start -->.*?<!-- nations:end -->", "", text, flags=re.S)
        locs = ["/nations"] + [f"/nations/{k}" for k, _ in SUPPORT] + \
               [f"/nations/region/{r['key']}" for r in self.m.regions] + \
               [f"/nations/in/{c.lower()}" for c in sorted(self.m.by_country)] + \
               [f"/nations/{n['id']}" for n in sorted(self.m.nations, key=lambda n: n["id"])]
        block = "\n  <!-- nations:start -->\n" + "\n".join(f"  <url><loc>{SITE}{l}</loc></url>" for l in locs) + \
                "\n  <!-- nations:end -->"
        text = text.replace("\n</urlset>", block + "\n</urlset>")
        wr(sp, text)


def L_meta(policy):
    parts = [d.strip() for d in policy.split(";") if d.strip()]
    return "; ".join(d for d in parts if d.split()[0] not in ("frame-ancestors", "report-uri", "sandbox"))


# ------------------------------------------------------------------------------------------------ scratch, gates, sync
COPY_DIRS = ["data", "tools", "game", "static/fonts", "static/nations", "nations"]
COPY_FILES = ["index.html", "download.html", "vercel.json", "sitemap.xml", "robots.txt", "nations.html",
              ".vercelignore", "zotheos_icon.ico"]


def scratch_copy(root):
    tmp = tempfile.mkdtemp(prefix="nations_build_")
    ign = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
    for d in COPY_DIRS:
        if os.path.isdir(os.path.join(root, d)):
            shutil.copytree(os.path.join(root, d), os.path.join(tmp, d), ignore=ign)
    for f in os.listdir(os.path.join(root, "static")):
        p = os.path.join(root, "static", f)
        if os.path.isfile(p) and not f.endswith((".mp4", ".mp3")):
            os.makedirs(os.path.join(tmp, "static"), exist_ok=True)
            shutil.copy2(p, os.path.join(tmp, "static", f))
    for f in COPY_FILES:
        if os.path.isfile(os.path.join(root, f)):
            shutil.copy2(os.path.join(root, f), os.path.join(tmp, f))
    return tmp


def run(tmp, *args, quiet=False):
    p = subprocess.run([sys.executable, *args], cwd=tmp, capture_output=True, text=True, encoding="utf-8")
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def gzlen(text):
    return len(gzip.compress(text.encode("utf-8"), compresslevel=9, mtime=0))


def gates(tmp, b):
    fails, notes = [], []
    steps = [("nations_lint", ["tools/nations_lint.py", "--build-date", b.m.build_date]), ("lint_copy", ["tools/lint_copy.py"]),
             ("fonts_check", ["tools/fonts_check.py"]), ("csp_sync --check", ["tools/csp_sync.py", "--check"]),
             ("nations_links", ["tools/nations_links.py"])]
    for name, args in steps:
        code, out = run(tmp, *args)
        last = out.strip().splitlines()[-1] if out.strip() else ""
        notes.append(f"  {name}: {last}")
        if code != 0:
            fails.append(f"{name} failed:\n{out[-4000:]}")
    banned = ["\u2014", "\u2013", "speechSynthesis", "SpeechSynthesisUtterance", "http://", "googleapis", "formspree",
              "Bhuri Bai"]
    for rel, text in b.pages.items():
        for word in banned:
            if word in text:
                fails.append(f"{rel}: contains {word!r}")
    hub_gz = gzlen(b.pages["nations.html"])
    nation_files = {f"nations/{n['id']}.html" for n in b.m.nations}
    page_gz = max(gzlen(t) for k, t in b.pages.items() if k in nation_files)
    other = sorted(((gzlen(t), k) for k, t in b.pages.items() if k not in nation_files and k != "nations.html"), reverse=True)[:3]
    notes.append("  largest support pages: " + ", ".join(f"{k} {v:,} B gz" for v, k in other))
    herald_raw = len(b.part("herald.js").encode("utf-8"))
    css_raw, css_gz = len(b.css_text.encode("utf-8")), gzlen(b.css_text)
    notes.append(f"  sizes: hub {hub_gz:,} B gz; largest nation page {page_gz:,} B gz; herald.js {herald_raw:,} B raw; "
                 f"stylesheet {css_raw:,} B raw, {css_gz:,} B gz")
    for label, val, lim in (("hub", hub_gz, BUDGET["hub_gz"]), ("a nations page", page_gz, BUDGET["page_gz"]),
                            ("herald.js", herald_raw, BUDGET["herald_raw"]), ("stylesheet (gz)", css_gz, BUDGET["css_gz"])):
        if val > lim:
            fails.append(f"size budget: {label} is {val:,} B, over {lim:,} B")
    return fails, notes


def contrast_check(root):
    """WCAG AA for the text tokens on each theme's page ground (14, Accessibility)."""
    css = rd(os.path.join(root, "tools", "nations", "partials", "tokens.css"))
    blocks = dict(re.findall(r"(:root:not\(\[data-theme\]\)|\[data-theme=\"\w+\"\]|:root)\s*\{(.*?)\}", css, re.S))
    def parse(b):
        return dict(re.findall(r"(--[\w-]+):\s*([^;]+);", b))
    base = parse(blocks[":root"])
    themes = {"maya": base, "codex": {**base, **parse(blocks['[data-theme="codex"]'])},
              "skeleton": {**base, **parse(blocks['[data-theme="skeleton"]'])},
              "mono": {**base, **parse(blocks[":root:not([data-theme])"])}}
    def resolve(t, v):
        for _ in range(4):
            m = re.match(r"var\((--[\w-]+)\)", v.strip())
            if not m:
                break
            v = t[m.group(1)]
        return v.strip()
    def lum(hexv):
        h = hexv.lstrip("#")
        rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    bad, report = [], []
    for name, t in themes.items():
        bg = lum(resolve(t, t["--page-bg"]))
        for tok in ("--ink", "--ink-2", "--ink-3", "--ink-low"):
            fg = lum(resolve(t, t[tok]))
            ratio = (max(fg, bg) + 0.05) / (min(fg, bg) + 0.05)
            report.append(f"{name} {tok} {ratio:.1f}")
            if ratio < 4.5:
                bad.append(f"contrast: {name} {tok} is {ratio:.2f}:1 on the page ground (AA needs 4.5)")
    return bad, report


def sync(tmp, root):
    for rel in GENERATED:
        src, dst = os.path.join(tmp, rel), os.path.join(root, rel)
        if os.path.isdir(src):
            if rel == "static/fonts":
                for f in os.listdir(src):
                    s_, d_ = os.path.join(src, f), os.path.join(dst, f)
                    if not os.path.exists(d_) or not filecmp.cmp(s_, d_, shallow=False):
                        shutil.copy2(s_, d_)
                for f in os.listdir(dst):
                    if not os.path.exists(os.path.join(src, f)):
                        os.remove(os.path.join(dst, f))
                continue
            if os.path.isdir(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        elif os.path.isfile(src):
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)
            shutil.copy2(src, dst)


def diff(tmp, root):
    out = []
    for rel in GENERATED:
        a, b = os.path.join(tmp, rel), os.path.join(root, rel)
        if os.path.isdir(a) or os.path.isdir(b):
            fa = {os.path.relpath(os.path.join(d, f), a) for d, _, fs in os.walk(a) for f in fs} if os.path.isdir(a) else set()
            fb = {os.path.relpath(os.path.join(d, f), b) for d, _, fs in os.walk(b) for f in fs} if os.path.isdir(b) else set()
            for f in sorted(fa - fb):
                out.append(f"missing from the tree: {rel}/{f}")
            for f in sorted(fb - fa):
                out.append(f"stale in the tree: {rel}/{f}")
            for f in sorted(fa & fb):
                if not filecmp.cmp(os.path.join(a, f), os.path.join(b, f), shallow=False):
                    out.append(f"differs: {rel}/{f}")
        elif os.path.isfile(a) != os.path.isfile(b) or (os.path.isfile(a) and not filecmp.cmp(a, b, shallow=False)):
            out.append(f"differs: {rel}")
    return out


def seed_last_verified(root):
    d = os.path.join(root, "data", "nations")
    raw = rd(os.path.join(d, "nations.json"))
    doc = json.loads(raw)
    n = 0
    for nat in doc["nations"]:
        for f in nat["facts"]:
            if f.get("status") == "verified" and "last_verified" not in f:
                f["last_verified"] = f["checked"]
                n += 1
    wr(os.path.join(d, "nations.json"), json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    with open(os.path.join(d, "nations.min.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"seeded last_verified on {n} facts")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=L.ROOT)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--seed-last-verified", action="store_true")
    ap.add_argument("--build-date", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--local-links", action="store_true")
    ap.add_argument("--game-json", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep the scratch directory (debugging)")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.root)
    if a.seed_last_verified:
        return seed_last_verified(root)
    code, out = run(root, os.path.join("data", "nations", "tools", "validate.py"))
    if code != 0:
        print(out[-3000:])
        print("nations_build: validate.py failed; nothing written")
        return 1
    tmp = scratch_copy(root)
    try:
        code, out = run(tmp, "tools/nations_fonts.py", "--root", tmp, "--no-record",
                        *(["--build-date", a.build_date] if a.build_date else []))
        if code != 0:
            print(out)
            raise BuildError("nations_fonts.py failed")
        fonts_report = out.rstrip()
        run(tmp, "tools/fonts_check.py", "--root", tmp, "--record")
        b = Builder(tmp, a.build_date, a.game_json)
        pages = b.build(tmp)
        code, out = run(tmp, "tools/csp_sync.py")
        if code != 0:
            raise BuildError("csp_sync.py failed:\n" + out)
        fails, notes = gates(tmp, b)
        cbad, creport = contrast_check(tmp)
        fails += cbad
        m = b.m
        tiers = {t: sum(n["tier"] == t for n in m.nations) for t in "ABC"}
        print(f"nations_build: build date {m.build_date}; {len(pages)} pages; {len(m.nations)} nations "
              f"(tier A {tiers['A']}, B {tiers['B']}, C {tiers['C']}); facts shown {m.counts['shown']}, under review "
              f"{m.counts['review']}, re-checking {m.counts['rechecking']} (grace {m.counts['grace']}, person "
              f"{m.counts['human']})")
        print(f"  whole-name fallbacks: {', '.join(n['name'] for n in m.nations if n['fc'] == 'names')}")
        shard_sizes = [(f, os.path.getsize(os.path.join(tmp, 'static', 'nations', f))) for f in
                       sorted(os.listdir(os.path.join(tmp, 'static', 'nations')))]
        print("  data: " + ", ".join(f"{f} {s:,} B" for f, s in shard_sizes if not f.endswith(".css")))
        print("  fonts:\n" + fonts_report)
        print("\n".join(notes))
        print("  contrast: " + ", ".join(creport))
        if fails:
            for f in fails:
                print("GATE " + f)
            print("nations_build: FAIL; nothing written")
            return 1
        if a.check:
            d = diff(tmp, root)
            for x in d[:60]:
                print("CHECK " + x)
            print("nations_build --check: " + ("FAIL (the committed output is not the build of the committed data)" if d else "ok"))
            return 1 if d else 0
        if a.out:
            dest = os.path.abspath(a.out)
            sync(tmp, dest) if os.path.isdir(dest) else shutil.copytree(tmp, dest)
            if a.local_links:
                for dp, _, fs in os.walk(dest):
                    for f in fs:
                        if f.endswith(".html") and ("nations" in dp or f == "nations.html"):
                            p = os.path.join(dp, f)
                            t = rd(p)
                            t = re.sub(r'href="(/nations(?:/[a-z0-9/-]+)?)(#[\w-]+)?"', lambda mm: f'href="{mm.group(1)}.html{mm.group(2) or ""}"', t)
                            wr(p, t)
            print(f"nations_build: written to {dest}")
            return 0
        sync(tmp, root)
        print("nations_build: ok, outputs written")
        return 0
    except BuildError as e:
        print("nations_build: " + str(e))
        print("nations_build: FAIL; nothing written")
        return 1
    finally:
        if not a.keep:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print("scratch kept at " + tmp)


if __name__ == "__main__":
    sys.exit(main())
