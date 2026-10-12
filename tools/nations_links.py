#!/usr/bin/env python3
"""Every link on the nations pages goes where it says (DESIGN_NATIONS 16.5). Exit 1 on any failure.

  - every internal href and src in nations.html and nations/** resolves: a built page (clean URL or .html), a static
    file, a landing page anchor that exists in index.html, or an anchor that exists on the target nations page
  - every external href is https, and appears in data/nations/nations.json (source URLs, official sites,
    pronunciation sources), in data/nations/universe.json (denominator and global-figure sources), in the visible
    news shelf's headlines, in the curated resources catalog, or is the repository link when site.json repo_public is true
  - formspree.io is never linked; every external anchor carries rel="noopener noreferrer"
  - every mailto: uses site.json's contact address
Usage: py -3.10 tools/nations_links.py [--root DIR]
"""
import argparse
import glob
import json
import os
import re
import sys
import urllib.parse
from html.parser import HTMLParser


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and "href" in a:
            self.links.append(("href", a["href"], a.get("rel") or "", a.get("target"), self.getpos()[0]))
        for k in ("src",):
            if k in a and tag in ("img", "script", "source", "audio", "video", "iframe"):
                self.links.append((k, a[k], "", None, self.getpos()[0]))
        if tag == "link" and a.get("href"):
            self.links.append(("link", a["href"], "", None, self.getpos()[0]))


def parse(path):
    p = Links()
    with open(path, encoding="utf-8") as f:
        p.feed(f.read())
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    a = ap.parse_args(argv)
    root = a.root
    pages = (["nations.html"] if os.path.isfile(os.path.join(root, "nations.html")) else []) + sorted(
        os.path.relpath(p, root).replace(os.sep, "/") for p in glob.glob(os.path.join(root, "nations", "**", "*.html"), recursive=True))
    if not pages:
        print("nations_links: no nations pages built; nothing to check")
        return 0
    data = json.load(open(os.path.join(root, "data", "nations", "nations.json"), encoding="utf-8"))
    site = json.load(open(os.path.join(root, "data", "nations", "site.json"), encoding="utf-8"))
    allowed = set()
    for n in data["nations"]:
        allowed.add(n["name_source_url"])
        if n.get("official_url"):
            allowed.add(n["official_url"])
        if n.get("pronounce"):
            allowed.add(n["pronounce"]["source_url"])
        for f in n["facts"]:
            allowed.add(f["source"]["url"])
    up = os.path.join(root, "data", "nations", "universe.json")
    if os.path.isfile(up):
        u = json.load(open(up, encoding="utf-8"))
        for c in u.get("countries", {}).values():
            allowed.add(c["source"]["url"])
        for g in u.get("global", []):
            allowed.add(g["url"])
    rp = os.path.join(root, "data", "nations", "resources.json")
    if os.path.isfile(rp):
        catalog = json.load(open(rp, encoding="utf-8"))
        for resource in catalog.get("resources", []):
            allowed |= {link["url"] for link in resource.get("links", [])}
            allowed |= {source["url"] for source in resource.get("sources", [])}
    cp = os.path.join(root, "data", "nations", "context_links.json")
    if os.path.isfile(cp):
        catalog = json.load(open(cp, encoding="utf-8"))
        allowed |= {entry["url"] for entry in catalog.get("links", [])}
    dp = os.path.join(root, "data", "nations", "research", "directory_sources.json")
    if os.path.isfile(dp):
        catalog = json.load(open(dp, encoding="utf-8"))
        allowed |= {source["url"] for source in catalog.get("sources", [])}
    fp = os.path.join(root, "data", "nations", "research", "us_federal_directory.json")
    if os.path.isfile(fp):
        directory = json.load(open(fp, encoding="utf-8"))
        allowed.add(directory["source"]["url"])
        for entry in directory.get("entities", []):
            if entry.get("official_url") and entry.get("official_url_review", {}).get("status") == "verified":
                allowed.add(entry["official_url"])
    np_ = os.path.join(root, "static", "nations", "news.json")
    if os.path.isfile(np_):
        news = json.load(open(np_, encoding="utf-8"))
        if news.get("shelf"):
            allowed |= {i["link"] for i in news.get("items", [])}
    if site.get("repo_public") and site.get("repo_url"):
        allowed.add(site["repo_url"])
    contact = site["contact"]
    ids_cache = {}

    def ids_of(rel):
        if rel not in ids_cache:
            ids_cache[rel] = parse(os.path.join(root, rel)).ids if os.path.isfile(os.path.join(root, rel)) else None
        return ids_cache[rel]

    def resolve(path):
        """URL path -> file relative to root, as Vercel's cleanUrls would serve it (or None)."""
        p = urllib.parse.unquote(path).lstrip("/")
        if p == "":
            return "index.html"
        for cand in (p, p + ".html", p.rstrip("/") + "/index.html"):
            if os.path.isfile(os.path.join(root, cand)):
                return cand
        return None

    bad, n_int, n_ext, n_mail = [], 0, 0, 0
    for rel in pages:
        lp = parse(os.path.join(root, rel))
        for kind, href, rel_attr, target, line in lp.links:
            where = f"{rel}:{line}"
            if href.startswith("mailto:"):
                n_mail += 1
                addr = href[7:].split("?")[0]
                if addr != contact:
                    bad.append(f"{where}: mailto {addr} is not site.json's contact {contact}")
                continue
            if "formspree" in href:
                bad.append(f"{where}: links formspree.io")
                continue
            if href.startswith("http://"):
                bad.append(f"{where}: plain http link {href}")
                continue
            if href.startswith("https://zotheos.org/") or href == "https://zotheos.org":
                href = href[len("https://zotheos.org"):] or "/"
                if kind == "href":
                    bad.append(f"{where}: a link to this site should be a path, not {href}")
            if href.startswith("https://"):
                n_ext += 1
                if href not in allowed:
                    bad.append(f"{where}: external link {href} is not a cited source, official site or allowlisted page")
                if kind == "href" and set(rel_attr.split()) != {"noopener", "noreferrer"}:
                    bad.append(f"{where}: external link without rel=\"noopener noreferrer\": {href}")
                continue
            if href.startswith("#"):
                n_int += 1
                if href[1:] and href[1:] not in lp.ids:
                    bad.append(f"{where}: anchor {href} does not exist on this page")
                continue
            if href.startswith("/"):
                n_int += 1
                path, _, frag = href.partition("#")
                path = path.split("?")[0]
                target_file = resolve(path)
                if target_file is None:
                    bad.append(f"{where}: {href} does not resolve to a built page or file")
                elif frag:
                    ids = ids_of(target_file)
                    if ids is not None and frag not in ids:
                        bad.append(f"{where}: {href}: no element with id {frag} in {target_file}")
                continue
            bad.append(f"{where}: unexpected link form {href!r}")
    for b in bad[:60]:
        print("LINK " + b)
    if len(bad) > 60:
        print(f"LINK ... and {len(bad) - 60} more")
    print(f"nations_links: {'FAIL' if bad else 'ok'} ({len(pages)} pages, {n_int:,} internal, {n_ext:,} external, "
          f"{n_mail:,} mailto)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
