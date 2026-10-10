#!/usr/bin/env python3
"""ZOTHEOS website release desk (stdlib only): one command per job on zotheos.org's two pages.

  status "<text>" [--date YYYY-MM-DD|today]
        The one-line development status. Rewrites the landing's hero status chip ("Windows desktop: <text> .
        Updated <date>") and the release page's status card (its state label and its "Development update" date).
        It is one line on a phone: 22 characters at most; past 17 the smallest phones (320 px) cut the end of the
        line with an ellipsis (measured: 17 fit). Without --date the "Updated" date stays where it is.
  log --title "<title>" --body "<paragraph>" [--body "<paragraph>" ...] [--body-file notes.txt] [--date YYYY-MM-DD]
        Adds a dated entry to the updates log on /download.html, newest first. The status dates move to the
        entry's date when it is the newest (--keep-date leaves them). --status "<text>" also sets the status line.
  Moving the dates: the release page's summary (the sentence under its heading, also its search description) and
        the other fixed development copy sit under that date. A run that moves the date prints that copy with
        file:line and needs --summary "<new summary>" or --summary-unchanged (you read it, it is still true).
  go-live --version 1.0.0 --url /download/ZOTHEOS_Setup_1.0.0_x64.exe --size "904 MB" --sha256 <64 hex>
        The installer is public. Flips both pages to data-release="available": the primary reads "Download for
        Windows" with version and size and points at the installer; the release page shows file, size, checksum.
        A site path (/...) must exist in this repo (--allow-missing when another step deploys it).
        --installer <local file> measures --size and --sha256 for you, and refuses when a --size or --sha256 you
        also pass disagrees with the file. It prints the copy that becomes visible, for you to confirm.
  prerelease [--clear-details]
        Back to "Join the release list" (the rollback). The release details stay filled in (hidden) for the next
        go-live; --clear-details resets them to placeholders, for an installer that was pulled.
  show  (or no command)
        What the site says right now. Writes nothing.
  check
        Every guard (CSP hashes, copy lint, release switch, updates log structure, status slots agree), on the repo
        as it is. Writes nothing.

Every writing command builds the new pages in a temporary copy first, runs tools/csp_sync.py (re-hashes inline
scripts into both CSPs), tools/lint_copy.py (no em dash in visible copy) and the other guards there, and prints a
diff summary. Only when all of that passes are index.html, download.html and vercel.json written. --dry-run stops
before writing. The tool refuses when a page changed under it while it ran.

Run from PowerShell or cmd:  py -3.10 tools\\release.py <command> ...   (docs/RELEASING.md is the guide)
In Git Bash, prefix MSYS_NO_PATHCONV=1 so a --url that starts with / is not rewritten into a Windows path.
"""
import argparse
import datetime
import difflib
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from html.parser import HTMLParser

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
sys.dont_write_bytecode = True   # no tools/__pycache__ in the repo
import release_switch as rs  # noqa: E402  (the release switch: state, details, JSON-LD, its own check)

PAGES = ("index.html", "download.html")
FILES = PAGES + ("vercel.json",)
DASH = "\u2014"
STATUS_MAX = 22        # the chip is one nowrap line: 22 characters fit beside the longest date on a 360 px phone
STATUS_SAFE = 17       # and 17 fit on the smallest phones (320 px, longest date, measured); past that: an ellipsis
TITLE_MAX = 90
SUMMARY_MAX = 260
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
UNITS = {"KB": 1024, "MB": 1048576, "GB": 1073741824}

STATUS_RE = re.compile(r'(<span\b[^>]*\bdata-rel="status"[^>]*>)([^<]*)(</span>)')
DATE_RE = re.compile(r'(<time\b[^>]*\bdata-rel="date"[^>]*>)([^<]*)(</time>)')
SUMMARY_RE = re.compile(r'(<p\b[^>]*\bdata-rel="summary"[^>]*>)([^<]*)(</p>)')
DESC_PRE_RE = re.compile(r'(<meta name="description"[^>]*\bdata-rs-pre=")([^"]*)(")')
LOG_OPEN_RE = re.compile(r'<ol\b[^>]*\bid="updates"[^>]*>\n')
ENTRY_RE = re.compile(r'( *)<li class="update" id="([^"]+)">.*?\n\1</li>\n', re.S)
ENTRY_ANY_RE = re.compile(r'<li\b[^>]*\bclass="[^"]*\bupdate\b[^"]*"')
ENTRY_DATE_RE = re.compile(r'<time datetime="(\d{4}-\d{2}-\d{2})">')
ENTRY_TITLE_RE = re.compile(r'<h3>([^<]*)</h3>')
LONG_DATE = r'(?:%s) \d{1,2}, \d{4}' % "|".join(MONTHS)
META_DATE_RE = re.compile(r'(\b(?:data-rs-pre|content)=")(%s)(:)' % LONG_DATE)
SITE_PATH_RE = re.compile(r'^/(?![/\\])[^\s"<>\\]+$')
HTTPS_RE = re.compile(r'^https://[^\s"<>/\\][^\s"<>\\]*$')


class Refused(Exception):
    pass


# -- small helpers ---------------------------------------------------------------------------------------------------
def read(root, name):
    with open(os.path.join(root, name), encoding="utf-8", newline="") as f:
        return f.read()


def write(root, name, text):
    with open(os.path.join(root, name), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def fmt_date(d, style):
    if style == "short":
        return f"{MONTHS[d.month - 1][:3]} {d.day}, {d.year}"
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def parse_date(s, allow_future=False):
    today = datetime.date.today()
    if s is None or s.strip().lower() == "today":
        return today
    try:
        d = datetime.date.fromisoformat(s)
    except ValueError:
        raise Refused(f"--date {s!r} is not a date: use YYYY-MM-DD, for example 2026-10-12, or today")
    if d > today + datetime.timedelta(days=1) and not allow_future:
        raise Refused(f"--date {d.isoformat()} is in the future (today is {today.isoformat()}). A dated update says what "
                      "is true on that day, and the newest date stays on top of the log. Pass --future only if you "
                      "really mean it.")
    return d


def clean_copy(label, text, limit=None):
    """Visible copy from the command line: one line, no em dash, within its length."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        raise Refused(f"{label} is empty")
    if DASH in text:
        raise Refused(f"{label} has an em dash. The site never shows one: use a comma, a colon or a period.")
    if limit and len(text) > limit:
        raise Refused(f"{label} is {len(text)} characters; keep it to {limit}. Put the detail in a log entry.")
    return text


def status_text(raw, label, lines):
    """The status line as the chip shows it: no "Windows desktop:" prefix (the chip has it), within its length."""
    text = clean_copy(label, re.sub(r"^\s*windows desktop\s*:\s*", "", raw or "", flags=re.I), STATUS_MAX)
    if len(text) > STATUS_SAFE:
        lines.append(f"note: {len(text)} characters fit phones from 360 px; on the smallest (320 px) the chip ends "
                     f"in an ellipsis and the date is cut short. {STATUS_SAFE} or fewer fit everywhere")
    return text


def read_notes(path):
    """A notes file as text: UTF-8 (with or without a BOM) or UTF-16 (what Windows PowerShell 5.1 writes with > or
    Out-File)."""
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        raise Refused(f"--body-file {path!r} could not be read: {e.strerror or e}")
    try:
        if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
            return raw.decode("utf-16")
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Refused(f"--body-file {path!r} is not UTF-8 text. Save it as UTF-8 (in PowerShell: "
                      "Set-Content notes.txt -Encoding utf8, or Save As UTF-8 in your editor).")


def size_bytes(size):
    m = re.fullmatch(r"(\d+(?:\.\d+)?) (KB|MB|GB)", size)
    value, unit = m.group(1), UNITS[m.group(2)]
    decimals = len(value.split(".", 1)[1]) if "." in value else 0
    return float(value) * unit, 0.5 * unit / (10 ** decimals)   # the size, and what rounding it for display allows


def run_tool(args):
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip()


# -- what the pages say now ------------------------------------------------------------------------------------------
def statuses(s):
    return [html.unescape(m.group(2)) for m in STATUS_RE.finditer(s)]


def date_slots(s):
    out = []
    for m in DATE_RE.finditer(s):
        a = re.search(r'\bdatetime="([^"]*)"', m.group(1))
        out.append(a.group(1) if a else "")
    return out


def status_date(s):
    for v in date_slots(s):
        try:
            return datetime.date.fromisoformat(v)
        except ValueError:
            return None
    return None


def entries(s):
    out = []
    for m in ENTRY_RE.finditer(s):
        d = ENTRY_DATE_RE.search(m.group(0))
        t = ENTRY_TITLE_RE.search(m.group(0))
        out.append({"id": m.group(2), "date": d.group(1) if d else "", "title": html.unescape(t.group(1)) if t else "",
                    "start": m.start(), "end": m.end(), "nested": len(ENTRY_ANY_RE.findall(m.group(0)))})
    return out


class _Claims(HTMLParser):
    """The fixed copy one release state shows: the text of every .rs-pre (or .rs-avail) block, grouped by the block
    element that holds it, with its line. Groups that are only link or button labels, the dated log (.rs-history)
    and short labels are left out: what is listed is the sentences a reader takes as the state of things."""

    BLOCK = {"p", "li", "h1", "h2", "h3", "h4", "dd", "dt", "div", "section", "ul", "ol", "dl"}
    VOID = rs._Shown.VOID

    def __init__(self, cls):
        super().__init__(convert_charrefs=True)
        self.cls, self.stack, self.groups, self.order = cls, [], {}, []

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        variant = self.cls in classes
        self.stack.append({"tag": tag, "variant": variant, "skip": "rs-history" in classes or tag in ("script", "style"),
                           "link": tag in ("a", "button"), "block": tag in self.BLOCK, "line": self.getpos()[0], "id": object()})

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if any(e["skip"] for e in self.stack):
            return
        roots = [i for i, e in enumerate(self.stack) if e["variant"]]
        if not roots:
            return
        group = next(e for e in reversed(self.stack[roots[0]:]) if e["block"] or e["variant"])
        if group["id"] not in self.groups:
            self.groups[group["id"]] = [group["line"], [], 0]
            self.order.append(group["id"])
        g = self.groups[group["id"]]
        g[1].append(data)
        if not any(e["link"] for e in self.stack):
            g[2] += len(data.strip())   # what is said outside link labels


def claims(pages, st):
    """[(file, line, text)] of the fixed copy shown in state st: the variant blocks, the meta descriptions, and the
    landing's JSON-LD description."""
    cls, attr = ("rs-avail", "data-rs-avail") if st == "available" else ("rs-pre", "data-rs-pre")
    out = []
    for name in PAGES:
        s = pages[name]
        p = _Claims(cls)
        p.feed(s)
        p.close()
        for gid in p.order:
            line, parts, prose = p.groups[gid]
            text = re.sub(r"\s+", " ", "".join(parts)).strip()
            if len(text) >= 40 and prose >= 30:
                out.append((name, line, text))
        for m in re.finditer(r'<meta\b[^>]*\b%s="([^"]*)"' % attr, s):
            text = rs.unesc(m.group(1)).replace("{version}", "<version>").replace("{size}", "<size>")
            out.append((name, s.count("\n", 0, m.start()) + 1, "(search/preview text) " + text))
        if name == "index.html":
            m = re.search(r'"description": "%s' % re.escape(rs.JSONLD[st]["description"][:40]), s)
            line = s.count("\n", 0, m.start()) + 1 if m else 0
            out.append((name, line, "(JSON-LD) " + rs.JSONLD[st]["description"]))
    return out


def print_claims(pages, st, heading):
    print(f"\n{heading}")
    for name, line, text in claims(pages, st):
        print(f"  {name}:{line}  {text if len(text) <= 150 else text[:147] + '...'}")


# -- edits (pure functions: text in, text out) -----------------------------------------------------------------------
def set_status(pages, text):
    for name in PAGES:
        s, n = STATUS_RE.subn(lambda m: m.group(1) + html.escape(text, quote=False) + m.group(3), pages[name])
        if n == 0:
            raise Refused(f'{name} has no data-rel="status" slot. Restore it from git (docs/RELEASING.md).')
        pages[name] = s


def set_date(pages, d, move_meta):
    for name in PAGES:
        def one(m):
            tag = m.group(1)
            style = "short" if 'data-fmt="short"' in tag else "long"
            tag = re.sub(r'\bdatetime="[^"]*"', f'datetime="{d.isoformat()}"', tag)
            return tag + fmt_date(d, style) + m.group(3)
        s, n = DATE_RE.subn(one, pages[name])
        if n == 0:
            raise Refused(f'{name} has no data-rel="date" slot. Restore it from git (docs/RELEASING.md).')
        # A search description that opens with a date ("October 4, 2026: ...") follows it, but only once the summary
        # under that date has been confirmed (--summary-unchanged) or rewritten (--summary).
        if move_meta:
            s = META_DATE_RE.sub(lambda m: m.group(1) + fmt_date(d, "long") + m.group(3), s)
        pages[name] = s


def set_summary(pages, text, d):
    """The release page's summary: the sentence under its heading, and its search description (dated)."""
    s = pages["download.html"]
    s, n = SUMMARY_RE.subn(lambda m: m.group(1) + html.escape(text, quote=False) + m.group(3), s, count=1)
    if n == 0:
        raise Refused('download.html has no data-rel="summary" paragraph. Restore it from git (docs/RELEASING.md).')
    meta = f"{fmt_date(d, 'long')}: {text}"
    s, n = DESC_PRE_RE.subn(lambda m: m.group(1) + rs.esc(meta) + m.group(3), s, count=1)
    if n == 0:
        raise Refused('download.html has no <meta name="description" ... data-rs-pre="...">. Restore it from git.')
    pages["download.html"] = rs.apply_variants(s, rs.state(s))


def render_entry(entry_id, d, title, paras, indent):
    # The heading comes first so heading navigation lands on the entry and then reads its date; CSS shows the date
    # above the title.
    i, j = indent, indent + "  "
    lines = [f'{i}<li class="update" id="{entry_id}"><span class="rim-glint" aria-hidden="true"></span>',
             f'{j}<h3>{html.escape(title, quote=False)}</h3>',
             f'{j}<p class="status-date"><time datetime="{d.isoformat()}">{fmt_date(d, "long")}</time></p>']
    lines += [f'{j}<p>{html.escape(p, quote=False)}</p>' for p in paras]
    lines.append(f'{i}</li>')
    return "\n".join(lines) + "\n"


def add_entry(pages, d, title, paras):
    s = pages["download.html"]
    m = LOG_OPEN_RE.search(s)
    if not m:
        raise Refused('download.html has no updates log (<ol ... id="updates">). Restore it from git.')
    have = entries(s)
    if any(e["date"] == d.isoformat() and e["title"] == title for e in have):
        raise Refused(f'the log already has "{title}" on {d.isoformat()}; nothing to add. To change an entry, edit '
                      "it in download.html (docs/RELEASING.md).")
    ids = {e["id"] for e in have}
    entry_id, n = f"update-{d.isoformat()}", 2
    while entry_id in ids:
        entry_id, n = f"update-{d.isoformat()}-{n}", n + 1
    ol_indent = re.match(r" *", s[s.rfind("\n", 0, m.start()) + 1:]).group(0)
    block = render_entry(entry_id, d, title, paras, ol_indent + "  ")
    # Newest first: in front of the first entry that is not newer than this one (same day: the new one leads).
    at = next((e["start"] for e in have if e["date"] <= d.isoformat()), None)
    if at is None:
        at = have[-1]["end"] if have else m.end()
    pages["download.html"] = s[:at] + block + s[at:]
    return entry_id, at == (have[0]["start"] if have else m.end())


def switch(pages, state, details):
    for name in PAGES:
        s = rs.set_state(pages[name], state)
        if details:
            s = rs.fill(s, details)
        s = rs.apply_variants(s, state)
        if name == "index.html":
            s = rs.apply_jsonld(s, state)
        pages[name] = s


# -- the pipeline: stage, guard, summarise, write --------------------------------------------------------------------
def short(line, at=0, width=150):
    line = line.rstrip("\n").strip()
    if len(line) <= width:
        return line
    lo = max(0, min(at, len(line)) - 50)
    return ("..." if lo else "") + line[lo:lo + width] + ("..." if lo + width < len(line) else "")


def diff_summary(name, old, new, limit=40):
    a, b = old.splitlines(True), new.splitlines(True)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    plus = minus = 0
    shown = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        minus += i2 - i1
        plus += j2 - j1
        pairs = list(zip(a[i1:i2], b[j1:j2])) if tag == "replace" and i2 - i1 == j2 - j1 else []
        if pairs:
            for x, y in pairs:
                k = len(os.path.commonprefix([x.strip(), y.strip()]))
                shown += [f"    L{i1 + 1}- {short(x, k)}", f"    L{j1 + 1}+ {short(y, k)}"]
                i1 += 1
                j1 += 1
        else:
            shown += [f"    L{i + 1}- {short(x)}" for i, x in enumerate(a[i1:i2], i1)]
            shown += [f"    L{j + 1}+ {short(y)}" for j, y in enumerate(b[j1:j2], j1)]
    if not plus and not minus:
        return f"  {name}: unchanged"
    more = len(shown) - limit
    body = "\n".join(shown[:limit]) + (f"\n    ... {more} more line(s)" if more > 0 else "")
    return f"  {name}: +{plus} -{minus} line(s)\n{body}"


def log_problems(s):
    """The updates log as the tool reads it, against the markup: every entry parsed once, ids unique, dates newest
    first, each with a date and a title. A hand edit that breaks the shape shows up here, not as a silent skip."""
    bad = []
    have = entries(s)
    marked = len(ENTRY_ANY_RE.findall(s))
    if marked != len(have) or any(e["nested"] != 1 for e in have):
        bad.append(f'download.html: {marked} <li class="update"> in the markup, {len(have)} read as separate entries. '
                   'Each entry must open with exactly <li class="update" id="..."> and close with </li> on its own '
                   "line at the same indent.")
    ids = [e["id"] for e in have]
    for dup in sorted({i for i in ids if ids.count(i) > 1}):
        bad.append(f"download.html: the entry id {dup!r} is used twice")
    for e in have:
        if not e["date"]:
            bad.append(f'download.html: entry #{e["id"]} has no <time datetime="YYYY-MM-DD">')
        if not e["title"]:
            bad.append(f'download.html: entry #{e["id"]} has no <h3> title')
    dated = [e for e in have if e["date"]]
    for x, y in zip(dated, dated[1:]):
        if y["date"] > x["date"]:
            bad.append(f'download.html: entry #{y["id"]} ({y["date"]}) sits below an older one, #{x["id"]} '
                       f'({x["date"]}); the log is newest first')
    return bad


def slot_problems(pages):
    bad = []
    st = [v for n in PAGES for v in statuses(pages[n])]
    if len(set(st)) > 1:
        bad.append(f"the status slots disagree: {sorted(set(st))} (run status \"<text>\" to set them all)")
    dt = [v for n in PAGES for v in date_slots(pages[n])]
    if len(set(dt)) > 1:
        bad.append(f"the status dates disagree: {sorted(set(dt))} (run status --date YYYY-MM-DD)")
    return bad


def guards(root, pages):
    """Every check on a tree. Returns a list of failures (empty when all pass) and a log of what ran."""
    bad, ran = [], []
    code, out = run_tool([os.path.join(TOOLS, "csp_sync.py"), "--check", "--root", root])
    ran.append("csp_sync --check: " + ("ok" if code == 0 else "FAILED"))
    if code:
        bad.append("csp_sync --check:\n" + out)
    code, out = run_tool([os.path.join(TOOLS, "lint_copy.py")] + [os.path.join(root, n) for n in PAGES])
    ran.append("lint_copy: " + ("ok" if code == 0 else "FAILED"))
    if code:
        bad.append("lint_copy:\n" + out)
    rsbad = [b for n in PAGES for b in rs.problems(n, pages[n])]
    if len({rs.state(pages[n]) for n in PAGES}) > 1:
        rsbad.append("the two pages are in different release states")
    ran.append("release switch check: " + ("ok" if not rsbad else "FAILED"))
    if rsbad:
        bad.append("release switch check:\n" + "\n".join("  " + b for b in rsbad))
    lbad = log_problems(pages["download.html"]) + slot_problems(pages)
    ran.append("log and status slots: " + ("ok" if not lbad else "FAILED"))
    if lbad:
        bad.append("log and status slots:\n" + "\n".join("  " + b for b in lbad))
    return bad, ran


def commit(before, pages, what, dry_run, review=None, gate=None):
    """review: (state, heading) prints that state's fixed copy from the staged pages. gate: a refusal that holds a real
    run back after the diff and the review are shown (a dry run reports it instead)."""
    tmp = tempfile.mkdtemp(prefix="zth-release-")
    try:
        for n in PAGES:
            write(tmp, n, pages[n])
        shutil.copyfile(os.path.join(ROOT, "vercel.json"), os.path.join(tmp, "vercel.json"))
        code, out = run_tool([os.path.join(TOOLS, "csp_sync.py"), "--root", tmp])
        if code:
            raise Refused("csp_sync could not update the staged copy:\n" + out)
        staged = {n: read(tmp, n) for n in FILES}
        bad, ran = guards(tmp, staged)
        print(f"{what}\n\nDiff summary (repo -> staged):")
        for n in FILES:
            print(diff_summary(n, before[n], staged[n]))
        if review:
            print_claims(staged, *review)
        print("\nGuards on the staged copy: " + "; ".join(ran))
        if bad:
            print()
            for b in bad:
                print(b)
            raise Refused("a guard failed on the staged copy, so nothing was written")
        changed = [n for n in FILES if staged[n] != before[n]]
        if not changed:
            print("\nNothing to change: the site already says this.")
            return 0
        if dry_run:
            if gate:
                print(f"\nWithout --dry-run this is refused: {gate}")
            print(f"\nDry run: nothing written. Without --dry-run this writes: {', '.join(changed)}.")
            return 0
        if gate:
            raise Refused(gate)
        for n in FILES:
            if read(ROOT, n) != before[n]:
                raise Refused(f"{n} changed while the tool ran (an editor or another tool). Nothing written; run again.")
        for n in changed:
            write(ROOT, n, staged[n])
        bad, ran = guards(ROOT, {n: staged[n] for n in PAGES})
        print(f"\nWrote: {', '.join(changed)}")
        print("Guards on the repo: " + "; ".join(ran))
        if bad:
            for b in bad:
                print(b)
            return 1
        print("Next: look at both pages locally, then commit and push (docs/RELEASING.md).")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def dating(a, pages, before, d, moves):
    """Applies a date (and a summary) and returns (review, gate) for commit()."""
    prerelease = rs.state(before["index.html"]) != "available"
    if moves:
        set_date(pages, d, move_meta=bool(a.summary_unchanged))
    if a.summary:
        set_summary(pages, clean_copy("--summary", a.summary, SUMMARY_MAX), d if moves else status_date(pages["index.html"]) or d)
    review = ("prerelease", "Still says (the fixed development copy under the status date; read it, it is what a "
                            "visitor takes as true on that date):") if prerelease else None
    gate = None
    if moves and prerelease and not (a.summary or a.summary_unchanged):
        gate = (f"this moves the status date to {d.isoformat()}, and the copy listed above would carry that date. "
                "Read it, then run again with --summary-unchanged (it is all still true) or --summary \"<the new "
                "summary sentence>\". Copy that changed elsewhere (a list item, a paragraph) is edited by hand in "
                "download.html first. --keep-date (log) leaves the date alone.")
    return review, gate


def summary_flags(p):
    p.add_argument("--summary", help=f"new summary under the release page heading (also its search description), "
                                     f"{SUMMARY_MAX} characters at most")
    p.add_argument("--summary-unchanged", action="store_true",
                   help="you read the listed copy and it is still true on the new date")
    p.add_argument("--future", action="store_true", help="allow a --date after tomorrow")


# -- commands --------------------------------------------------------------------------------------------------------
def cmd_show(pages):
    idx, dl = pages["index.html"], pages["download.html"]
    print(f"Release state: {rs.state(idx)} (index.html), {rs.state(dl)} (download.html)")
    d = status_date(idx)
    print(f"Status line:   {' | '.join(dict.fromkeys(statuses(idx) + statuses(dl)))}"
          f"   updated {d.isoformat() if d else '?'}")
    m = SUMMARY_RE.search(dl)
    print(f"Summary:       {html.unescape(m.group(2)) if m else '(no summary slot)'}")
    for n in PAGES:
        v = rs.values(pages[n])
        details = ", ".join(f"{k} {'/'.join(sorted(v[k]))}" for k in rs.PLACEHOLDERS if v[k])
        print(f"Release details ({n}): {details or 'none'}")
    log = entries(dl)
    print(f"Updates log:   {len(log)} entr{'y' if len(log) == 1 else 'ies'}")
    for e in log[:5]:
        print(f"  {e['date']}  {e['title']}  (#{e['id']})")
    return 0


def cmd_check(pages):
    bad, ran = guards(ROOT, pages)
    print("; ".join(ran))
    for b in bad:
        print(b)
    return 1 if bad else 0


def cmd_status(a, before):
    if a.text is None and a.date is None and a.summary is None:
        raise Refused('give the status text, a --date, a --summary, or several: status "internal testing" --date 2026-10-12')
    pages = dict(before)
    lines = []
    if a.text is not None:
        text = status_text(a.text, "the status", lines)
        set_status(pages, text)
        lines.insert(0, f'status "{text}"')
    cur = status_date(before["index.html"])
    d = parse_date(a.date, a.future) if a.date is not None else (cur or datetime.date.today())
    moves = d != cur
    review, gate = dating(a, pages, before, d, moves)
    if moves:
        lines.append(f"dated {d.isoformat()}")
    elif a.text is not None:
        lines.append(f"the date stays {cur.isoformat() if cur else '?'} (pass --date to move it)")
    if a.summary:
        lines.append("summary rewritten")
    if rs.state(before["index.html"]) == "available":
        lines.append("note: the site is available, so the status line shows again only after `prerelease`")
    return commit(before, pages, "status: " + ", ".join(lines), a.dry_run, review, gate)


def cmd_log(a, before):
    title = clean_copy("--title", a.title, TITLE_MAX)
    raw = list(a.body or [])
    if a.body_file:
        raw += re.split(r"\n\s*\n", read_notes(a.body_file).replace("\r\n", "\n").replace("\r", "\n"))
    paras = [clean_copy("a --body paragraph", p) for p in raw if p.strip()]
    if not paras:
        raise Refused("the entry needs at least one --body paragraph (or --body-file)")
    d = parse_date(a.date, a.future)
    pages = dict(before)
    entry_id, newest = add_entry(pages, d, title, paras)
    lines = [f'log entry #{entry_id} "{title}" ({len(paras)} paragraph{"s" if len(paras) > 1 else ""})']
    if a.status:
        notes = []
        text = status_text(a.status, "--status", notes)
        set_status(pages, text)
        lines += [f'status "{text}"'] + notes
    cur = status_date(before["index.html"])
    moves = not a.keep_date and newest and (cur is None or d > cur)
    if a.keep_date and (a.summary or a.summary_unchanged):
        raise Refused("--keep-date leaves the date alone; --summary / --summary-unchanged go with moving it")
    review, gate = dating(a, pages, before, d, moves)
    if moves:
        lines.append(f"status dates moved to {d.isoformat()}")
    elif not newest:
        lines.append("an older date, so it sits below newer entries and the status dates stay")
    return commit(before, pages, "log: " + ", ".join(lines), a.dry_run, review, gate)


def cmd_go_live(a, before):
    url = a.url.strip()
    if re.match(r"^[A-Za-z]:[\\/]", url):
        raise Refused(f"--url {url!r} is a local Windows path. In Git Bash prefix MSYS_NO_PATHCONV=1, or use PowerShell.")
    if url.startswith("//"):
        raise Refused(f"--url {url!r} starts with //, which a browser reads as another host. Use one / for a path on "
                      "this site, or a full https:// address.")
    if not (SITE_PATH_RE.match(url) or HTTPS_RE.match(url)):
        raise Refused("--url must be a site path such as /download/ZOTHEOS_Setup_1.0.0_x64.exe or an https:// address")
    if not re.fullmatch(r"v?\d+(\.\d+){1,3}([-+][0-9A-Za-z.-]+)?", a.version):
        raise Refused(f"--version {a.version!r} is not a version such as 1.0.0")
    version = a.version if a.version.startswith("v") else "v" + a.version
    notes = []
    hosted = None   # the file at a site path, in this repo
    if url.startswith("/"):
        rel = urllib.parse.unquote(url.split("?", 1)[0].split("#", 1)[0]).lstrip("/")
        fp = os.path.normpath(os.path.join(ROOT, rel))
        if not fp.startswith(os.path.normpath(ROOT) + os.sep):
            raise Refused(f"--url {url!r} leaves the site")
        if os.path.isfile(fp):
            hosted = fp
        elif not a.allow_missing:
            raise Refused(f"{url} is not in this repo ({fp} does not exist), so the Download button would lead to a "
                          "missing page. Put the installer at that path first, or use the https:// address where it is "
                          "hosted. If another step deploys the file there, pass --allow-missing and open the link on "
                          "the live site before you announce it.")
        else:
            notes.append(f"note: {url} is not in this repo (--allow-missing): open it on the live site before you "
                         "announce the release")
    else:
        notes.append(f"note: the tool cannot check another host. Open {url} in a browser and confirm it downloads the "
                     "same file before you push.")
    size, sha = a.size, a.sha256.lower() if a.sha256 else None
    if size is not None:
        m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(KB|MB|GB)?\s*", size, re.I)
        if not m:
            raise Refused(f'--size {size!r} is not a size such as "904 MB"')
        size = f"{m.group(1)} {(m.group(2) or 'MB').upper()}"
    if sha is not None and not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise Refused("--sha256 must be the 64 hex digits of the installer's SHA-256")
    source = a.installer or hosted
    if a.installer and not os.path.isfile(a.installer):
        raise Refused(f"--installer {a.installer!r} is not a file")
    if source:
        nbytes = os.path.getsize(source)
        measured_size = f"{nbytes / 1048576:.0f} MB" if nbytes >= 1048576 else f"{-(-nbytes // 1024)} KB"
        if nbytes < 10 * 1048576:
            notes.append(f"note: {source} is only {measured_size}; check that it is the installer")
        measured_sha = rs.sha256_of(source)
        if sha and sha != measured_sha:
            raise Refused(f"--sha256 does not match {source} (the file hashes to {measured_sha})")
        if size:
            given, slack = size_bytes(size)
            if abs(given - nbytes) > max(slack, 0.01 * nbytes):
                raise Refused(f"--size {size} does not match {source}, which is {measured_size} ({nbytes} bytes)")
        if a.installer and hosted and os.path.abspath(a.installer) != os.path.abspath(hosted):
            if os.path.getsize(hosted) != nbytes or rs.sha256_of(hosted) != measured_sha:
                raise Refused(f"the file at {url} in this repo is not the same file as --installer {a.installer}")
        sha, size = measured_sha, size or measured_size
    if not size or not sha:
        raise Refused("go-live needs --size and --sha256 (or --installer to measure both)")
    file_name = urllib.parse.unquote(url.split("?", 1)[0].split("#", 1)[0].rstrip("/").rsplit("/", 1)[-1])
    if not file_name.lower().endswith((".exe", ".msi", ".zip", ".msix")):
        notes.append(f"note: the installer file name {file_name!r} has no .exe/.msi/.zip/.msix ending; check --url")
    for n in notes:
        print(n)
    details = {"version": version, "size": size, "sha256": sha, "href": url, "file": file_name}
    pages = dict(before)
    switch(pages, "available", details)
    return commit(before, pages, f"go-live: {version}, {size}, {file_name}, sha256 {sha[:12]}..., link {url}",
                  a.dry_run, ("available", "Becomes visible (the fixed release copy; read it, every sentence must be "
                                           "true for this installer):"))


def cmd_prerelease(a, before):
    pages = dict(before)
    if a.clear_details:   # a pulled release: no hidden link to that installer stays in the markup
        switch(pages, "prerelease", dict(rs.PLACEHOLDERS))
        what = "prerelease: back to the release list ask, release details cleared to placeholders"
    else:
        switch(pages, "prerelease", None)
        what = "prerelease: back to the release list ask (release details kept for next time)"
    review = None
    if rs.state(before["index.html"]) == "available":
        review = ("prerelease", "Becomes visible again (the development copy from before the release, with its old "
                                "date; post a log entry or a status that says what is true now):")
    return commit(before, pages, what, a.dry_run, review)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(prog="release.py", description=__doc__.split("\n")[0],
                                 epilog="Each command has its own --help. The guide is docs/RELEASING.md.")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("status", help="set the one-line development status, its date, the release page summary")
    p.add_argument("text", nargs="?", help=f'the status after "Windows desktop:", {STATUS_MAX} characters at most')
    p.add_argument("--date", help="YYYY-MM-DD or today (default: the date stays)")
    summary_flags(p)
    p = sub.add_parser("log", help="add a dated entry to the updates log on /download.html")
    p.add_argument("--title", required=True, help=f"one line, {TITLE_MAX} characters at most")
    p.add_argument("--body", action="append", help="one paragraph; repeat --body for more paragraphs")
    p.add_argument("--body-file", help="a UTF-8 text file; blank lines separate paragraphs")
    p.add_argument("--date", help="YYYY-MM-DD (default: today)")
    p.add_argument("--status", help="also set the one-line status")
    p.add_argument("--keep-date", action="store_true", help="leave the status dates where they are")
    summary_flags(p)
    p = sub.add_parser("go-live", help="the installer is public: switch both pages to available")
    p.add_argument("--version", required=True, help="e.g. 1.0.0 (shown as v1.0.0)")
    p.add_argument("--url", required=True, help="the installer link, e.g. /download/ZOTHEOS_Setup_1.0.0_x64.exe")
    p.add_argument("--size", help='e.g. "904 MB"')
    p.add_argument("--sha256", help="the installer's SHA-256, 64 hex digits")
    p.add_argument("--installer", help="the local installer file: measures --size and --sha256, checks given ones")
    p.add_argument("--allow-missing", action="store_true",
                   help="a site path that is not in this repo (another step deploys the file there)")
    p = sub.add_parser("prerelease", help="switch back to the release list ask (rollback)")
    p.add_argument("--clear-details", action="store_true",
                   help="also reset version, size, link and checksum to placeholders (for a pulled installer)")
    sub.add_parser("show", help="print what the site says now")
    sub.add_parser("check", help="run every guard on the repo, write nothing")
    for name, sp in sub.choices.items():
        if name in ("status", "log", "go-live", "prerelease"):
            sp.add_argument("--dry-run", action="store_true", help="stage, check and show the diff; write nothing")
    a = ap.parse_args(argv)
    before = {n: read(ROOT, n) for n in FILES}
    try:
        if a.cmd in (None, "show"):
            return cmd_show(before)
        if a.cmd == "check":
            return cmd_check(before)
        return {"status": cmd_status, "log": cmd_log, "go-live": cmd_go_live,
                "prerelease": cmd_prerelease}[a.cmd](a, before)
    except Refused as e:
        print(f"refused: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
