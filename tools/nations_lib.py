"""Shared model for the /nations build and its gates (DESIGN_NATIONS.md). Stdlib only, except the font readers,
which need fontTools (and brotli for woff2), pinned in tools/requirements-nations.txt.

The model is the published view of data/nations/nations.json: sidecars loaded, overrides applied last, each fact's
display state derived from the verifier's three states (9.1), tiers computed (ARCHITECTURE 2.3), typographic
decisions made per string (11.2, 11.5), and the rotation functions (6.1, 6.2) mirrored exactly by herald.js.
"""
import datetime as dt
import json
import os
import re
import unicodedata
import urllib.parse

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

SECOND_LEVEL = {"co", "com", "org", "gov", "edu", "ac", "net", "gob", "gv", "or", "ne", "go", "nic", "mil", "govt",
                "iwi", "maori"}
RESERVED_IDS = {"index", "region", "in", "api", "static", "about", "sources", "coverage", "credits", "verification",
                "for-nations", "paths-to-action", "changes", "news", "search", "today"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PREF_KINDS = ("today", "achievement")
GRACE_DAYS = 14
HUMAN_DAYS = 90
OVERDUE_DAYS = 14
SIZE_CLASSES = ((10, "xl"), (18, "l"), (30, "m"), (44, "s"))
CHER = ((0x13A0, 0x13FF), (0xAB70, 0xABBF))
CANS = ((0x1400, 0x167F), (0x18B0, 0x18FF), (0x11AB0, 0x11ABF))
TFNG = ((0x2D30, 0x2D7F),)


def path(*parts, root=None):
    return os.path.join(root or ROOT, *parts)


def load_json(p, default=None):
    if default is not None and not os.path.isfile(p):
        return default
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


# ------------------------------------------------------------------------------------------------ text helpers
def host(url):
    return urllib.parse.urlsplit(url or "").netloc.lower()


def bare_host(url):
    h = host(url)
    return h[4:] if h.startswith("www.") else h


def reg_domain(h):
    parts = (h or "").lower().rstrip(".").split(".")
    if parts and parts[0] == "www":
        parts = parts[1:]
    if len(parts) >= 3 and len(parts[-1]) == 2 and parts[-2] in SECOND_LEVEL:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def clusters(s):
    """Grapheme clusters, close enough for this data: a base and every following mark, joiner or selector."""
    out = []
    for c in s:
        cat = unicodedata.category(c)
        if out and (cat in ("Mn", "Me", "Mc") or c in "\u200d\u034f" or 0xFE00 <= ord(c) <= 0xFE0F):
            out[-1] += c
        else:
            out.append(c)
    return out


def in_ranges(cp, ranges):
    return any(a <= cp <= b for a, b in ranges)


def script_of(s):
    for c in s:
        cp = ord(c)
        if in_ranges(cp, CHER):
            return "cher"
        if in_ranges(cp, CANS):
            return "cans"
        if in_ranges(cp, TFNG):
            return "tfng"
    return "latn"


def has_mark(s):
    return any(unicodedata.category(c) == "Mn" for c in s)


def size_class(name):
    n = len(clusters(name))
    for limit, cls in SIZE_CLASSES:
        if n <= limit:
            return cls
    return "xs"


def parse_date(s):
    return dt.date.fromisoformat(s)


def fmt_date(s):
    d = parse_date(s) if isinstance(s, str) else s
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def days_between(a, b):
    return (parse_date(b) - parse_date(a)).days


def fmt_int(n):
    return f"{n:,}"


def plural(n, one, many):
    return one if n == 1 else many


def cut_words(s, n):
    words = s.split()
    return " ".join(words[:n]) + ("\u00a0..." if len(words) > n else "")   # the ellipsis never starts a line


def cut_chars(s, n):
    if len(s) <= n:
        return s
    cut = s[:n].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + " ..."


# ------------------------------------------------------------------------------------------------ rotation (mirrored in herald.js)
M32 = 0xFFFFFFFF


def imul(a, b):
    return (a * b) & M32


def fnv1a32(s):
    h = 0x811C9DC5
    for b in s.encode("utf-8"):
        h ^= b
        h = imul(h, 0x01000193)
    return h


def mix32(x):
    x &= M32
    x ^= x >> 16
    x = imul(x, 0x7FEB352D)
    x ^= x >> 15
    x = imul(x, 0x846CA68B)
    x ^= x >> 16
    return x & M32


def ring_seed(date_iso, version):
    return fnv1a32(f"{date_iso}|{version}")


def ring_pick(seed, region_index, count):
    return mix32((seed ^ imul(region_index + 1, 0x9E3779B1)) & M32) % count


def day_number(date_iso):
    return (parse_date(date_iso) - dt.date(1970, 1, 1)).days


def pick_fact(card_id, facts, day):
    """facts: list of dicts with 'k' (kind). Ring cards prefer today and achievement facts (6.1)."""
    pref = [f for f in facts if f["k"] in PREF_KINDS]
    pool = pref or facts
    return pool[(day + fnv1a32(card_id)) % len(pool)]


def feistel4(x, n, key):
    """A keyed permutation of range(n): four Feistel rounds on the smallest even bit width, cycle-walked."""
    if n <= 1:
        return 0
    bits = max(2, (n - 1).bit_length())
    if bits % 2:
        bits += 1
    half = bits // 2
    mask = (1 << half) - 1
    while True:
        left, right = x >> half, x & mask
        for r in range(4):
            f = mix32((right ^ key ^ imul(r + 1, 0x85EBCA6B)) & M32) & mask
            left, right = right, left ^ f
        x = (left << half) | right
        if x < n:
            return x


# ------------------------------------------------------------------------------------------------ fonts
def parse_font_faces(block):
    """[(family, style, url, [(lo, hi), ...]), ...] from an @font-face block."""
    out = []
    for m in re.finditer(r"@font-face\s*\{(.*?)\}", block, re.S):
        body = m.group(1)
        fam = re.search(r"font-family:\s*'([^']+)'", body)
        sty = re.search(r"font-style:\s*(\w+)", body)
        url = re.search(r"url\(\s*['\"]?([^'\")]+)", body)
        rng = re.search(r"unicode-range:\s*([^;]+);", body)
        ranges = []
        if rng:
            for part in rng.group(1).split(","):
                part = part.strip().upper().replace("U+", "")
                if "-" in part:
                    a, b = part.split("-")
                    ranges.append((int(a, 16), int(b, 16)))
                elif part:
                    ranges.append((int(part, 16), int(part, 16)))
        out.append((fam.group(1) if fam else "", sty.group(1) if sty else "normal", url.group(1) if url else "",
                    ranges or [(0, 0x10FFFF)]))
    return out


_CMAPS = {}


def cmap(file_path):
    if file_path not in _CMAPS:
        from fontTools.ttLib import TTFont  # needs fontTools (+ brotli for woff2)
        f = TTFont(file_path, lazy=True)
        _CMAPS[file_path] = set(f.getBestCmap().keys())
        f.close()
    return _CMAPS[file_path]


def family_cover(block, family, root, style="normal"):
    """Code points a family really draws: each face's cmap intersected with its declared unicode-range."""
    cover = set()
    for fam, sty, url, ranges in parse_font_faces(block):
        if fam != family or sty != style:
            continue
        cm = cmap(os.path.join(root, url.lstrip("/")))
        cover |= {cp for cp in cm if in_ranges(cp, ranges)}
    return cover


def brand_block(root):
    html = read(os.path.join(root, "index.html"))
    m = re.search(r'<style id="zth-fonts">(.*?)</style>', html, re.S)
    if not m:
        raise SystemExit("index.html has no zth-fonts block")
    return m.group(1)


class BrandCover:
    def __init__(self, root):
        b = brand_block(root)
        self.serif = family_cover(b, "Instrument Serif", root)
        self.sans = family_cover(b, "DM Sans", root)
        self.mono = family_cover(b, "JetBrains Mono", root)

    def serif_ok(self, s):
        return all(ord(c) in self.serif for c in s) and not has_mark(s)

    def sans_ok(self, s):
        return all(ord(c) in self.sans for c in s)


# ------------------------------------------------------------------------------------------------ the model
class Model:
    """Everything the pages, shards and gates need, computed once."""

    def __init__(self, root=None, build_date=None):
        self.root = root or ROOT
        d = path("data", "nations", root=self.root)
        self.raw = load_json(os.path.join(d, "nations.json"))
        self.regions_conf = load_json(os.path.join(d, "regions.json"))
        self.countries = load_json(os.path.join(d, "countries.json"))
        self.overrides = load_json(os.path.join(d, "overrides.json"))
        self.pron_pub = load_json(os.path.join(d, "pronounce_publishers.json"))
        self.site = load_json(os.path.join(d, "site.json"))
        self.changes = load_json(os.path.join(d, "changes.json"), [])
        self.redirects = load_json(os.path.join(d, "redirects.json"), {})
        self.human = load_json(os.path.join(d, "verify", "human.json"), {})
        self.history = load_json(os.path.join(d, "verify", "history.json"), [])
        self.universe = load_json(os.path.join(d, "universe.json"), {"countries": {}, "global": []})
        self.priority = load_json(os.path.join(d, "source_priority.json"))
        self.news_flags = load_json(path("data", "news", "flags.json", root=self.root), {"shelf_visible": False})
        self.news_sources = load_json(path("data", "news", "sources.json", root=self.root), {"outlets": []})
        self.news_items = load_json(path("data", "news", "headlines.json", root=self.root), {"gathered": None, "items": []})
        self.version = int(self.raw["version"])
        self.major = 1
        self.compiled = self.raw["generated"]
        facts = [f for n in self.raw["nations"] for f in n["facts"]]
        self.build_date = build_date or max(f["checked"] for f in facts)
        self.errors = []
        self._apply()

    # ---- overrides, states, tiers
    def _apply(self):
        ov = self.overrides
        hidden_facts = {e["fact"] for e in ov.get("hide_fact", [])}
        gone = {e["nation"] for e in ov.get("hide_nation", [])} | {e["nation"] for e in ov.get("takedown", [])}
        self.blocked_ids = {e["nation"] for e in ov.get("takedown", [])}
        renames = {e["nation"]: e["name"] for e in ov.get("rename", [])}
        drop_also = {}
        for e in ov.get("drop_also", []):
            drop_also.setdefault(e["nation"], set()).add(e["also"])
        drop_pron = {e["nation"] for e in ov.get("drop_pronounce", [])}
        order = self.regions_conf["order"]
        rdisp = self.regions_conf["regions"]
        data_regions = {n["region"] for n in self.raw["nations"]}
        for r in data_regions - set(rdisp):
            self.errors.append(f"region {r} is used by nations but has no entry in regions.json")
        for r in set(rdisp) - data_regions:
            self.errors.append(f"regions.json entry {r} is used by no nation")
        if set(order) != set(rdisp):
            self.errors.append("regions.json order and regions differ")
        used_cc = {c for n in self.raw["nations"] for c in n["countries"]}
        for c in sorted(used_cc - set(self.countries)):
            self.errors.append(f"country code {c} has no entry in countries.json")
        for c in sorted(set(self.countries) - used_cc):
            self.errors.append(f"countries.json entry {c} is used by no nation")
        own_domains = {reg_domain(host(n["official_url"])) for n in self.raw["nations"] if n.get("official_url")}
        self.own_domains = own_domains
        self.nations = []
        self.counts = {"shown": 0, "review": 0, "rechecking": 0, "waiting": 0, "hidden": 0, "grace": 0, "human": 0,
                       "verified_status": 0}
        for raw in self.raw["nations"]:
            if raw["id"] in gone:
                continue
            n = {
                "id": raw["id"], "region": raw["region"], "name": renames.get(raw["id"], raw["name"]),
                "also": [a for a in raw.get("also", []) if a not in drop_also.get(raw["id"], set())],
                "also_search": list(raw.get("also_search", [])), "lands": raw["lands"],
                "countries": list(raw["countries"]), "official_url": raw.get("official_url"),
                "name_source_url": raw["name_source_url"], "pronounce": None,
            }
            pr = raw.get("pronounce")
            if pr and raw["id"] not in drop_pron:
                h = bare_host(pr["source_url"])
                if n["official_url"] and reg_domain(host(pr["source_url"])) == reg_domain(host(n["official_url"])):
                    credit = f"{n['name']}, on its own site"
                elif h in self.pron_pub:
                    credit = self.pron_pub[h]
                else:
                    credit = None
                if h not in self.pron_pub:
                    self.errors.append(f"nation {raw['id']}: pronunciation host {h} has no entry in pronounce_publishers.json")
                n["pronounce"] = {"text": pr["text"], "url": pr["source_url"], "publisher": credit or h}
            pub, review, recheck, waiting = [], 0, 0, 0
            for f in raw["facts"]:
                if f["status"] == "verified":
                    self.counts["verified_status"] += 1
                st, rec, extra = self.fact_state(f, hidden_facts)
                ff = {"id": f["id"], "text": f["text"], "kind": f["kind"], "as_of": f.get("as_of"),
                      "title": f["source"]["title"], "publisher": f["source"]["publisher"], "url": f["source"]["url"],
                      "state": st, "date": rec, "checked": f["checked"], "human": st == "human", "grace": st == "grace",
                      "group": self.url_group(f["source"]["url"])}
                if st in ("ok", "grace", "human"):
                    pub.append(ff)
                    self.counts["shown"] += 1
                    if st in ("grace", "human"):
                        self.counts[st] += 1
                elif st == "review":
                    review += 1
                    self.counts["review"] += 1
                else:
                    recheck += 1
                    self.counts["rechecking"] += 1
                    self.counts["waiting" if st == "waiting" else "hidden"] += 1
                    waiting += st == "waiting"
                ff["note"] = extra
                n.setdefault("all_facts", []).append(ff)
            pub.sort(key=lambda f: (f["as_of"] is None, -(int(f["as_of"]) if f["as_of"] else 0), f["id"]))
            n["facts"] = pub
            n["review"] = review
            n["rechecking"] = recheck
            n["tier"] = self.tier(n)
            self.nations.append(n)
        self.by_id = {n["id"]: n for n in self.nations}
        self.regions = []
        for i, key in enumerate(order):
            members = [n for n in self.nations if n["region"] == key]
            members.sort(key=lambda n: (fold_key(n["name"]), n["id"]))
            ab = sorted((n for n in members if n["tier"] in ("A", "B")), key=lambda n: n["id"])
            self.regions.append({"key": key, "display": rdisp[key]["display"], "index": i, "nations": members,
                                 "ab": ab, "countries": sorted({c for n in members for c in n["countries"]},
                                                               key=lambda c: self.countries.get(c, c))})
        self.region_by_key = {r["key"]: r for r in self.regions}
        self.by_country = {}
        for n in self.nations:
            for c in n["countries"]:
                self.by_country.setdefault(c, []).append(n)
        for c in self.by_country:
            self.by_country[c].sort(key=lambda n: (fold_key(n["name"]), n["id"]))

    def fact_state(self, f, hidden_facts):
        """(display state, receipt date, extra) from the verifier's state (DESIGN_NATIONS 9.1)."""
        if f["id"] in hidden_facts:
            return "review", None, None
        st, b = f["status"], self.build_date
        if st == "verified":
            return "ok", f.get("last_verified") or f["checked"], None
        if st == "unreachable":
            hr = self.human.get(f["id"])
            if hr and 0 <= days_between(hr["date"], b) < HUMAN_DAYS:
                return "human", hr["date"], None
            lv = f.get("last_verified")
            if lv and days_between(lv, b) <= GRACE_DAYS:
                return "grace", lv, f["checked"]
            return "waiting", None, None
        return "hidden", None, None

    def tier(self, n):
        pub = n["facts"]
        o = n["official_url"]
        if o:
            od = reg_domain(host(o))
            if (reg_domain(host(n["name_source_url"])) == od and len(pub) >= 2
                    and any(reg_domain(host(f["url"])) == od for f in pub)):
                return "A"
        if pub:
            return "B"
        return "C"

    def url_group(self, url):
        d = reg_domain(host(url))
        if d in self.own_domains:
            return "1"
        for g, doms in self.priority["domains"].items():
            if d in doms or host(url) in doms or bare_host(url) in doms:
                return g
        h = bare_host(url)
        for g, sufs in self.priority["suffixes"].items():
            if any(h.endswith(s) for s in sufs):
                return g
        return "9"

    # ---- rotation
    def ring(self, date_iso=None):
        date_iso = date_iso or self.build_date
        seed = ring_seed(date_iso, self.version)
        day = day_number(date_iso)
        out = []
        for r in self.regions:
            if not r["ab"]:
                continue
            n = r["ab"][ring_pick(seed, r["index"], len(r["ab"]))]
            facts = [{"k": f["kind"], "f": f} for f in n["facts"]]
            out.append((r, n, pick_fact(n["id"], facts, day)["f"]))
        return out

    # ---- status
    def last_full_check(self):
        for run in self.history:
            if not run.get("sample") and run.get("published"):
                return run["run_date"]
        return None


def fold_key(s):
    from nations_fold import fold
    return fold(s)
