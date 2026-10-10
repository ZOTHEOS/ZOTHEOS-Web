#!/usr/bin/env python3.10
"""ZOTHEOS nations refresh: re-fetch every cited source and re-check its evidence phrase.

Runs server side or in CI only. Visitors' browsers never contact these hosts.

For each unique source.url in nations.json:
  * fetch politely: honest user agent, robots.txt obeyed, at most 1 request per host
    per --host-interval seconds (default 1.0), timeout, bounded retries with backoff,
    Retry-After honoured, 8 MB cap, no browser spoofing;
  * extract visible text (HTML without script/style/noscript/template/svg; PDF via
    pypdf when installed, with line-break hyphenation joined);
  * normalise page text and evidence identically (html unescape, NFKC, drop soft
    hyphen and zero-width characters, unify quotes and dashes, collapse whitespace,
    casefold) and test containment: pass 1 exact, pass 2 with diacritics stripped
    (comparison only), pass 3 with punctuation ignored;
  * set each fact's status (verified | stale | unreachable) and checked date.

  verified     evidence phrase found on the cited page
  stale        page answered but the phrase is gone, or 404/410, or the page now
               redirects to a different site; the site should hide the fact until a
               person restores it (never auto-restored)
  unreachable  timeout, DNS/TLS error, 5xx, 401/403/429, robots.txt disallow,
               unsupported format, or a JavaScript shell with no static text;
               nothing is concluded about the fact (human lane)

Writes nations.json (and nations.min.json) back unless --dry-run, plus
refresh_report.json and refresh_report.md.

Usage:
  py -3.10 tools/nations_refresh.py [--dry-run] [--limit N] [--file nations.json]
         [--host-interval 1.0] [--timeout 20] [--retries 2] [--run-date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import html
import io
import json
import os
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import zlib
from collections import Counter, OrderedDict, defaultdict
from html.parser import HTMLParser

UA = "ZOTHEOS-nations-verifier/1 (+https://zotheos.org)"
MAX_BYTES = 8 * 1024 * 1024
MIN_STATIC_TEXT = 400  # below this the page is a JavaScript shell, not a readable source
SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "head"}
BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "tr", "td", "th", "h1", "h2", "h3", "h4", "h5", "h6",
              "section", "article", "header", "footer", "nav", "aside", "main", "table", "blockquote",
              "dd", "dt", "dl", "figcaption", "figure", "pre", "hr", "option", "label"}
SECOND_LEVEL = {"co", "com", "org", "gov", "edu", "ac", "net", "gob", "gv", "or", "ne", "go", "nic", "mil", "govt", "iwi", "maori"}


# ---------------------------------------------------------------- normalisation
_QUOTES_1 = dict.fromkeys(map(ord, "‘’‛ʻʼ′´`"), "'")
_QUOTES_2 = dict.fromkeys(map(ord, "“”„″«»"), '"')
_DASHES = dict.fromkeys(list(range(0x2010, 0x2016)) + [0x2212], "-")
_DROP = dict.fromkeys(map(ord, "­​‌‍﻿"), None)


def normalise(s: str, pdf: bool = False) -> str:
    s = html.unescape(s)
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(_DROP).translate(_QUOTES_1).translate(_QUOTES_2).translate(_DASHES)
    if pdf:
        s = re.sub(r"(\w) ?-\s*\n\s*(\w)", r"\1\2", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.casefold()


def strip_marks(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return unicodedata.normalize("NFC", "".join(c for c in s if not unicodedata.combining(c)))


def no_punct(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def match(evidence: str, page_norm: str, page_marks: str, page_punct: str) -> str | None:
    e = normalise(evidence)
    if e and e in page_norm:
        return "exact"
    e2 = strip_marks(e)
    if e2 and e2 in page_marks:
        return "diacritics differ on page"
    e3 = no_punct(e2)
    if e3 and e3 in page_punct:
        return "punctuation differs on page"
    return None


def near_match(evidence: str, page_punct: str) -> tuple[float, str] | None:
    toks = no_punct(strip_marks(normalise(evidence))).split()
    words = page_punct.split()
    if not toks or len(words) < len(toks):
        return None
    want = set(toks)
    best, best_i = 0.0, -1
    n = len(toks)
    for i in range(0, len(words) - n + 1):
        win = words[i:i + n]
        score = len(want & set(win)) / len(want | set(win))
        if score > best:
            best, best_i = score, i
    if best >= 0.5:
        return round(best, 2), " ".join(words[best_i:best_i + n])
    return None


# ---------------------------------------------------------------- extraction
class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0
        self.title: list[str] = []
        self.in_title = False
        self.meta: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        if tag in SKIP_TAGS and tag != "head":
            self.skip += 1
        if tag == "meta":
            a = dict(attrs)
            if (a.get("name") or a.get("property") or "").lower() in ("description", "og:description", "og:title"):
                if a.get("content"):
                    self.meta.append(a["content"])
        if tag in BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag in SKIP_TAGS and tag != "head" and self.skip:
            self.skip -= 1
        if tag in BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data):
        if self.in_title:
            self.title.append(data)
            return
        if not self.skip:
            self.parts.append(data)

    def text(self) -> str:
        return " ".join(["".join(self.title)] + self.meta + ["".join(self.parts)])


def html_to_text(raw: str) -> tuple[str, int]:
    """Return (title + meta + visible text, length of visible body text alone)."""
    p = TextExtractor()
    try:
        p.feed(raw)
        p.close()
    except Exception:  # malformed markup: keep what was parsed
        pass
    body = re.sub(r"\s+", " ", "".join(p.parts)).strip()
    return p.text(), len(body)


def pdf_to_text(data: bytes) -> str | None:
    try:
        import pypdf  # optional dependency
    except ImportError:
        return None
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return None


def decode(body: bytes, ctype: str) -> str:
    m = re.search(r"charset=([\w-]+)", ctype or "", re.I)
    enc = m.group(1) if m else None
    if not enc:
        m2 = re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", body[:4096], re.I)
        enc = m2.group(1).decode("ascii", "ignore") if m2 else "utf-8"
    try:
        return body.decode(enc, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


# ---------------------------------------------------------------- polite fetching
def reg_domain(host: str) -> str:
    parts = (host or "").lower().rstrip(".").split(".")
    if parts and parts[0] == "www":
        parts = parts[1:]
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


class Fetcher:
    def __init__(self, interval: float, timeout: float, retries: int, obey_robots: bool = True):
        self.interval = interval
        self.timeout = timeout
        self.retries = retries
        self.obey_robots = obey_robots
        self.next_ok: dict[str, float] = defaultdict(float)
        self.robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self.requests = 0

    def _wait(self, host: str) -> None:
        now = time.monotonic()
        if self.next_ok[host] > now:
            time.sleep(self.next_ok[host] - now)
        self.next_ok[host] = time.monotonic() + self.interval

    def _open(self, url: str, host: str):
        self._wait(host)
        self.requests += 1
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en,es;q=0.8,fr;q=0.6,pt;q=0.5,*;q=0.3",
        })
        return urllib.request.urlopen(req, timeout=self.timeout)

    def allowed(self, url: str) -> bool:
        if not self.obey_robots:
            return True
        u = urllib.parse.urlsplit(url)
        host = u.netloc.lower()
        if host not in self.robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                with self._open(f"{u.scheme}://{host}/robots.txt", host) as resp:
                    body = resp.read(512 * 1024)
                    if resp.headers.get("Content-Encoding") == "gzip":
                        body = gzip.decompress(body)
                    rp.parse(body.decode("utf-8", errors="replace").splitlines())
                self.robots[host] = rp
            except urllib.error.HTTPError as e:
                # RFC 9309: 4xx means no restrictions; 5xx means assume full disallow
                self.robots[host] = None if 400 <= e.code < 500 else False
            except Exception:
                self.robots[host] = None
        rp = self.robots[host]
        if rp is None:
            return True
        if rp is False:
            return False
        return rp.can_fetch(UA, url)

    def fetch(self, url: str) -> dict:
        u = urllib.parse.urlsplit(url)
        host = u.netloc.lower()
        out = {"url": url, "final_url": None, "http": None, "outcome": None, "note": "", "text": None, "pdf": False}
        if u.scheme != "https":
            out.update(outcome="unreachable", note="not https")
            return out
        if not self.allowed(url):
            out.update(outcome="unreachable", note="robots.txt disallows this path")
            return out
        attempt = 0
        while True:
            attempt += 1
            try:
                with self._open(url, host) as resp:
                    out["http"] = resp.status
                    out["final_url"] = resp.geturl()
                    body = resp.read(MAX_BYTES + 1)
                    if len(body) > MAX_BYTES:
                        out.update(outcome="unreachable", note="page larger than 8 MB")
                        return out
                    enc = (resp.headers.get("Content-Encoding") or "").lower()
                    if enc == "gzip":
                        body = gzip.decompress(body)
                    elif enc == "deflate":
                        body = zlib.decompress(body, -zlib.MAX_WBITS)
                    ctype = resp.headers.get("Content-Type") or ""
                if reg_domain(urllib.parse.urlsplit(out["final_url"]).netloc) != reg_domain(host):
                    out.update(outcome="stale", note=f"redirects to another site: {out['final_url']}")
                    return out
                if "pdf" in ctype.lower() or body[:5] == b"%PDF-":
                    out["pdf"] = True
                    text = pdf_to_text(body)
                    if text is None:
                        out.update(outcome="unreachable", note="PDF text could not be extracted (pypdf missing or failed)")
                        return out
                else:
                    text, body_len = html_to_text(decode(body, ctype))
                    if body_len < MIN_STATIC_TEXT:
                        out.update(outcome="unreachable",
                                   note=f"no static text ({body_len} chars): JavaScript-rendered page, needs the human lane")
                        return out
                out.update(outcome="fetched", text=text)
                return out
            except urllib.error.HTTPError as e:
                out["http"] = e.code
                if e.code in (404, 410):
                    out.update(outcome="stale", note=f"HTTP {e.code}")
                    return out
                retryable = e.code in (429, 500, 502, 503, 504)
                if retryable and attempt <= self.retries:
                    ra = e.headers.get("Retry-After") if e.headers else None
                    delay = min(float(ra), 30.0) if ra and ra.isdigit() else 2.0 * attempt
                    time.sleep(delay)
                    continue
                out.update(outcome="unreachable", note=f"HTTP {e.code}")
                return out
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as e:
                if attempt <= self.retries:
                    time.sleep(2.0 * attempt)
                    continue
                reason = getattr(e, "reason", e)
                out.update(outcome="unreachable", note=f"network: {str(reason)[:160]}")
                return out
            except Exception as e:  # decoding or parsing failure
                out.update(outcome="unreachable", note=f"error: {type(e).__name__}: {str(e)[:120]}")
                return out


# ---------------------------------------------------------------- main
def plan_urls(doc: dict) -> "OrderedDict[str, list[tuple[dict, dict]]]":
    """Unique URLs, ordered round robin across regions so a capped run samples widely."""
    per_region: dict[str, OrderedDict] = defaultdict(OrderedDict)
    for n in doc["nations"]:
        for f in n["facts"]:
            per_region[n["region"]].setdefault(f["source"]["url"], []).append((n, f))
    order: OrderedDict[str, list] = OrderedDict()
    queues = {r: list(d.items()) for r, d in sorted(per_region.items())}
    while any(queues.values()):
        for r in list(queues):
            while queues[r]:
                url, items = queues[r].pop(0)
                if url in order:
                    order[url].extend(items)
                    continue
                order[url] = list(items)
                break
    return order


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=os.path.join(os.path.dirname(here), "nations.json"))
    ap.add_argument("--report-dir", default=here)
    ap.add_argument("--limit", type=int, default=0, help="max unique source URLs to fetch (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="check and report, but do not write nations.json")
    ap.add_argument("--host-interval", type=float, default=1.0)
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--run-date", default=dt.datetime.now(dt.timezone.utc).date().isoformat())
    ap.add_argument("--ignore-robots", action="store_true", help="testing only; never in production")
    args = ap.parse_args()

    with open(args.file, encoding="utf-8") as fh:
        doc = json.load(fh, object_pairs_hook=OrderedDict)
    plan = plan_urls(doc)
    total_urls = len(plan)
    urls = list(plan.items())
    if args.limit and args.limit > 0:
        urls = urls[: args.limit]
    # interleave hosts so the per-host interval rarely blocks
    by_host: dict[str, list] = defaultdict(list)
    for url, items in urls:
        by_host[urllib.parse.urlsplit(url).netloc.lower()].append((url, items))
    schedule = []
    while any(by_host.values()):
        for h in list(by_host):
            if by_host[h]:
                schedule.append(by_host[h].pop(0))

    fetcher = Fetcher(args.host_interval, args.timeout, args.retries, obey_robots=not args.ignore_robots)
    t0 = time.monotonic()
    url_rows, fact_rows = [], []
    status_count = Counter()
    for k, (url, items) in enumerate(schedule, 1):
        res = fetcher.fetch(url)
        if res["outcome"] == "fetched":
            text = res["text"] or ""
            pn = normalise(text, pdf=res["pdf"])
            pm = strip_marks(pn)
            pp = no_punct(pm)
        for n, f in items:
            row = {"nation": n["id"], "fact": f.get("id"), "url": url, "evidence": f["evidence"]}
            if res["outcome"] == "fetched":
                how = match(f["evidence"], pn, pm, pp)
                if how:
                    status, note = "verified", ("" if how == "exact" else how)
                else:
                    status, note = "stale", "evidence phrase not found on page"
                    nm = near_match(f["evidence"], pp)
                    if nm:
                        row["near_match"] = {"score": nm[0], "window": nm[1]}
            else:
                status, note = res["outcome"], res["note"]
            row.update(status=status, note=note, previous=f.get("status"))
            fact_rows.append(row)
            status_count[status] += 1
            f["status"] = status
            f["checked"] = args.run_date
        url_rows.append({"url": url, "http": res["http"], "outcome": res["outcome"], "note": res["note"],
                         "final_url": res["final_url"], "facts": len(items)})
        print(f"[{k}/{len(schedule)}] {res['outcome']:<11} {res['http'] or '-':>4} {url[:90]}", flush=True)

    elapsed = round(time.monotonic() - t0, 1)
    unchecked = sum(len(v) for u, v in plan.items()) - len(fact_rows)
    report = OrderedDict([
        ("run_date", args.run_date), ("dry_run", args.dry_run), ("user_agent", UA),
        ("host_interval_s", args.host_interval), ("timeout_s", args.timeout), ("retries", args.retries),
        ("robots", not args.ignore_robots), ("urls_total", total_urls), ("urls_checked", len(schedule)),
        ("requests_sent", fetcher.requests), ("elapsed_s", elapsed),
        ("facts_checked", len(fact_rows)), ("facts_unchecked", unchecked),
        ("status", dict(status_count)),
        ("urls", url_rows), ("facts", fact_rows),
    ])
    os.makedirs(args.report_dir, exist_ok=True)
    with open(os.path.join(args.report_dir, "refresh_report.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    lines = [f"# Nations refresh {'(dry run) ' if args.dry_run else ''}{args.run_date}", "",
             f"- URLs checked: {len(schedule)} of {total_urls} ({fetcher.requests} requests incl. robots.txt, {elapsed} s)",
             f"- Facts checked: {len(fact_rows)} (unchecked this run: {unchecked})",
             f"- Status: " + ", ".join(f"{k} {v}" for k, v in sorted(status_count.items())), "",
             "| outcome | http | facts | url | note |", "|---|---|---|---|---|"]
    for r in url_rows:
        lines.append(f"| {r['outcome']} | {r['http'] or ''} | {r['facts']} | {r['url']} | {r['note']} |")
    stale = [r for r in fact_rows if r["status"] == "stale"]
    if stale:
        lines += ["", "## Stale facts (hidden until a person restores them)", ""]
        for r in stale:
            nm = r.get("near_match")
            hint = f" Near match ({nm['score']}): \"{nm['window']}\"" if nm else ""
            lines.append(f"- `{r['fact']}`: {r['note']}.{hint}")
    with open(os.path.join(args.report_dir, "refresh_report.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    if not args.dry_run:
        with open(args.file, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        mini = os.path.join(os.path.dirname(args.file), "nations.min.json")
        with open(mini, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"done: {dict(status_count)}; {'dry run, nations.json untouched' if args.dry_run else 'nations.json updated'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
