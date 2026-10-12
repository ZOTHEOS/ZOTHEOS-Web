#!/usr/bin/env python3
"""Headlines for the /nations news shelf, from Indigenous-led outlets only (DESIGN_NATIONS 19, ARCHITECTURE 6).

While data/news/flags.json has "shelf_visible": false, this polls nothing and exits (no outlet is contacted before
the owner decides who signs the courtesy letters). --force runs anyway, for the owner's own test; --feed-dir reads
<outlet id>.xml files from a folder instead of the network (tests).

Kept per headline: title, outlet, date, link, and the feed's language. Discarded: descriptions, content, images,
authors. Titles: tags stripped, entities decoded, whitespace collapsed, an em or en dash turned into a spaced hyphen
(no word is changed), capped at 160 characters. Links: https only, host on that outlet's allowlist (a hijacked feed
cannot send readers elsewhere), tracking parameters removed, deduplicated by canonical link. Dates: items more than
a day ahead are dropped, and so is anything older than 30 days. At most 10 per outlet, interleaved round robin by
region. Writes data/news/headlines.json; the build reads it only when the shelf is visible.

Usage: py -3.10 tools/news_fetch.py [--force] [--feed-dir DIR] [--now YYYY-MM-DDTHH:MM]
"""
import argparse
import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "ZOTHEOS-nations-news/1 (+https://zotheos.org)"
MAX_TITLE, PER_OUTLET, WINDOW_DAYS = 160, 10, 30
TRACKING = re.compile(r"^(utm_\w+|fbclid|gclid|mc_cid|mc_eid|ref|cmpid|ocid)$", re.I)
ATOM = "{http://www.w3.org/2005/Atom}"


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, d):
        self.parts.append(d)


def clean_title(raw):
    p = _Text()
    p.feed(html.unescape(raw or ""))
    p.close()
    t = " ".join("".join(p.parts).split())
    t = re.sub(r"\s*[\u2013\u2014]\s*", " - ", t)
    if len(t) > MAX_TITLE:
        t = t[:MAX_TITLE - 3].rsplit(" ", 1)[0].rstrip(",;:") + "..."
    return t


def canonical(link, allow):
    u = urllib.parse.urlsplit((link or "").strip())
    if u.scheme != "https" or not u.netloc:
        return None
    host = u.hostname.lower() if u.hostname else ""
    if host not in {a.lower() for a in allow}:
        return None
    q = [(k, v) for k, v in urllib.parse.parse_qsl(u.query, keep_blank_values=True) if not TRACKING.match(k)]
    path = u.path or "/"
    return urllib.parse.urlunsplit(("https", host, path, urllib.parse.urlencode(sorted(q)), ""))


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def parse_feed(xml_bytes):
    """[(title, link, date, lang)] from RSS 2.0 or Atom."""
    root = ET.fromstring(xml_bytes)
    out = []
    if root.tag == ATOM + "feed":
        lang = root.get("{http://www.w3.org/XML/1998/namespace}lang")
        for e in root.findall(ATOM + "entry"):
            link = ""
            for l in e.findall(ATOM + "link"):
                if l.get("rel", "alternate") == "alternate":
                    link = l.get("href", "")
                    break
            date = (e.findtext(ATOM + "published") or e.findtext(ATOM + "updated") or "")
            out.append((e.findtext(ATOM + "title") or "", link, date, lang))
        return out
    ch = root.find("channel")
    if ch is None:
        return out
    lang = ch.findtext("language")
    for it in ch.findall("item"):
        out.append((it.findtext("title") or "", it.findtext("link") or "", it.findtext("pubDate") or "", lang))
    return out


def gather(sources, now, fetch):
    by_outlet = []
    for o in sources["outlets"]:
        if not o.get("enabled") or not o.get("leadership"):
            continue
        try:
            raw = fetch(o)
        except Exception as e:  # one outlet failing never stops the others
            print(f"  {o['id']}: not read ({type(e).__name__})")
            continue
        try:
            rows = parse_feed(raw)
        except ET.ParseError:
            print(f"  {o['id']}: feed is not valid XML")
            continue
        seen, items = set(), []
        for title, link, date, lang in rows:
            t, c, d = clean_title(title), canonical(link, o.get("allow", [])), parse_date(date)
            if not t or not c or not d:
                continue
            if d > now + dt.timedelta(days=1) or d < now - dt.timedelta(days=WINDOW_DAYS) or c in seen:
                continue
            seen.add(c)
            items.append({"title": t, "link": c, "outlet": o["name"], "date": d.date().isoformat(),
                          "lang": (lang or o.get("lang") or "en").split("-")[0].lower(), "region": o.get("region"),
                          "_ts": d.timestamp()})
        items.sort(key=lambda x: -x["_ts"])
        by_outlet.append((o.get("region") or "", items[:PER_OUTLET]))
    # round robin by region, then by outlet within it
    regions = {}
    for reg, items in by_outlet:
        regions.setdefault(reg, []).append(items)
    queues = [[x for lst in zip_longest_lists(lists) for x in lst] for _, lists in sorted(regions.items())]
    out, links = [], set()
    while any(queues):
        for q in queues:
            if q:
                x = q.pop(0)
                if x["link"] not in links:
                    links.add(x["link"])
                    x.pop("_ts", None)
                    out.append(x)
    return out


def zip_longest_lists(lists):
    n = max((len(l) for l in lists), default=0)
    return [[l[i] for l in lists if i < len(l)] for i in range(n)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--force", action="store_true", help="poll even while the shelf is hidden (owner testing)")
    ap.add_argument("--feed-dir", default=None, help="read <outlet id>.xml from this folder instead of the network")
    ap.add_argument("--now", default=None, help="UTC time to judge dates against, YYYY-MM-DDTHH:MM (tests)")
    a = ap.parse_args(argv)
    news = os.path.join(a.root, "data", "news")
    flags = json.load(open(os.path.join(news, "flags.json"), encoding="utf-8"))
    if not flags.get("shelf_visible") and not a.force:
        print("news_fetch: the shelf is hidden (data/news/flags.json); no outlet polled, nothing written")
        return 0
    sources = json.load(open(os.path.join(news, "sources.json"), encoding="utf-8"))
    now = (dt.datetime.fromisoformat(a.now).replace(tzinfo=dt.timezone.utc) if a.now
           else dt.datetime.now(dt.timezone.utc))

    def fetch(o):
        if a.feed_dir:
            with open(os.path.join(a.feed_dir, o["id"] + ".xml"), "rb") as f:
                return f.read()
        req = urllib.request.Request(o["feed"], headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read(4 * 1024 * 1024)
    items = gather(sources, now, fetch)
    doc = {"gathered": now.strftime("%d %b %Y, %H:%M UTC").lstrip("0"), "items": items}
    with open(os.path.join(news, "headlines.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"news_fetch: {len(items)} headlines from {len({i['outlet'] for i in items})} outlets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
