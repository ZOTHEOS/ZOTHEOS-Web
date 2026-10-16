"""Bounded, reviewed nation-page context. Only the canonical public model supplies record names/links."""
import datetime
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import nations_lib as L

MAX_BYTES = 128 * 1024
MAX_FILES = 32
MAX_RECORDS = 256
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
URL = re.compile(r'^https://[^\s"<>]+$')


def text(value, limit=700):
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ValueError("context: invalid or oversized text")
    return value


def date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("context: review date must be YYYY-MM-DD")
    try:
        result = datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("context: invalid review date") from exc
    # A source review has its own clock; old canonical fact checks stay unchanged.
    if result > datetime.datetime.now(datetime.timezone.utc).date():
        raise ValueError("context: future review date")
    return value


def read_json(path):
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("context: file exceeds 128 KiB")
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("context: file must be an object")
    return value


def items(doc, key, limit):
    value = doc.get(key, [])
    if not isinstance(value, list) or len(value) > limit or any(not isinstance(v, dict) for v in value):
        raise ValueError("context: invalid or oversized " + key)
    return value


def esc(value):
    return html.escape(str(value), quote=True)


def stamp(value):
    return f'<time datetime="{esc(value)}">{esc(L.fmt_date(value))}</time>'


class Context:
    def __init__(self, root, model):
        self.model = model
        self.entries = {}
        known = {n["id"] for n in model.raw["nations"]}
        self.known_facts = {n["id"]: {f["id"] for f in n["facts"]} for n in model.raw["nations"]}
        public_facts = {n["id"]: {f["id"] for f in n["facts"]} for n in model.nations}
        folder = Path(root) / "data" / "nations"
        source_folder = folder / "sources"
        files = sorted(source_folder.glob("*.context.json")) if source_folder.exists() else []
        if len(files) > MAX_FILES:
            raise ValueError("context: more than 32 context files")
        if not files:
            return
        allow = read_json(folder / "context_links.json")
        if allow.get("version") != 1:
            raise ValueError("context: unsupported link catalog version")
        links = {}
        for entry in items(allow, "links", MAX_RECORDS):
            nid = self.nation(entry.get("nation"), known)
            address = text(entry.get("url"), 700)
            if not URL.fullmatch(address):
                raise ValueError("context: invalid approved URL")
            key = (nid, address)
            if key in links:
                raise ValueError("context: duplicate approved URL")
            links[key] = {"reviewed": date(entry.get("reviewed")),
                          "publisher": text(entry.get("publisher"), 160)}
        records = 0
        pending_notes = []
        resource_index = {}
        for path in files:
            if path.resolve().parent != source_folder.resolve():
                raise ValueError("context: context path escapes source folder")
            doc = read_json(path)
            reviewed = date(doc.get("reviewed"))
            groups = {"public_notes": items(doc, "public_notes", 64),
                      "official_resources": items(doc, "official_resources", 32),
                      "relationships": items(doc, "relationships", 32)}
            records += sum(len(v) for v in groups.values())
            if records > MAX_RECORDS:
                raise ValueError("context: more than 256 public context records")
            for note in groups["public_notes"]:
                nid = self.nation(note.get("nation"), known)
                body = text(note.get("text"))
                title = text(note["title"], 160) if "title" in note else None
                if title is not None and not title.strip():
                    raise ValueError("context: empty note title")
                refs = None
                if "source_urls" in note:
                    refs = note["source_urls"]
                    if (not isinstance(refs, list) or not 1 <= len(refs) <= 4
                            or any(not isinstance(v, str) for v in refs)):
                        raise ValueError("context: invalid layer sources")
                    if len(set(refs)) != len(refs):
                        raise ValueError("context: duplicate layer sources")
                    for address in refs:
                        self.source_url(address)
                pending_notes.append((nid, body, reviewed, title, refs,
                                      self.visible(nid, note, public_facts)))
            for resource in groups["official_resources"]:
                nid = self.nation(resource.get("nation"), known)
                address = text(resource.get("url"), 700)
                key = (nid, address)
                if key not in links:
                    raise ValueError("context: resource URL not on exact nation/link allowlist")
                label = text(resource.get("label"), 160)
                purpose = text(resource.get("purpose"))
                visible = self.visible(nid, resource, public_facts)
                value = (resource["url"], label, purpose, links[key])
                resource_index.setdefault(key, []).append((value, visible))
                if visible:
                    self.add(nid, "resources", value)
            for relation in groups["relationships"]:
                origin = self.nation(relation.get("from"), known)
                targets = relation.get("to")
                if not isinstance(targets, list) or not 1 <= len(targets) <= 8:
                    raise ValueError("context: invalid relationship targets")
                members = [origin] + [self.nation(nid, known) for nid in targets]
                if len(set(members)) != len(members):
                    raise ValueError("context: duplicate relationship member")
                statement = text(relation.get("relationship"))
                if origin not in model.by_id:
                    continue
                members = [nid for nid in members if nid in model.by_id]
                for nid in members:
                    others = [other for other in members if other != nid]
                    if others:
                        self.add(nid, "relations", (statement, tuple(others), reviewed))

        # Resolve explicit citations after all files, preserving original note order.
        for nid, body, reviewed, title, refs, visible in pending_notes:
            citations = []
            if refs is not None:
                for address in refs:
                    definitions = resource_index.get((nid, address), [])
                    if not definitions:
                        raise ValueError("context: layer source requires an approved same-nation resource")
                    first = definitions[0]
                    if any(value != first for value in definitions[1:]):
                        raise ValueError("context: ambiguous layer source resource")
                    resource, source_visible = first
                    if not source_visible:
                        visible = False
                    citations.append(resource)
            if visible:
                self.add(nid, "notes", (body, reviewed, title, tuple(citations)))

    @staticmethod
    def source_url(address):
        text(address, 700)
        if any(ord(c) < 32 or ord(c) == 127 for c in address):
            raise ValueError("context: invalid layer source URL")
        if not URL.fullmatch(address) or "\\" in address:
            raise ValueError("context: invalid layer source URL")
        try:
            parsed = urlsplit(address)
            port = parsed.port
        except ValueError as exc:
            raise ValueError("context: invalid layer source URL") from exc
        if (not parsed.hostname or parsed.username is not None or parsed.password is not None
                or port == 0 or parsed.netloc.endswith(":")):
            raise ValueError("context: invalid layer source URL")

    @staticmethod
    def nation(nid, known):
        if not isinstance(nid, str) or len(nid) > 64 or not ID.fullmatch(nid) or nid not in known:
            raise ValueError("context: unknown or invalid nation id")
        return nid

    def visible(self, nid, item, public_facts):
        refs = item.get("fact_ids", [])
        if not isinstance(refs, list) or len(refs) > 16 or any(not isinstance(v, str) for v in refs):
            raise ValueError("context: invalid fact references")
        if not set(refs) <= self.known_facts[nid]:
            raise ValueError("context: unknown fact reference")
        return nid in self.model.by_id and set(refs) <= public_facts[nid]

    def add(self, nid, kind, item):
        values = self.entries.setdefault(nid, {}).setdefault(kind, [])
        if item not in values:
            values.append(item)
        if len(values) > 16:
            raise ValueError("context: more than 16 items of one kind on a nation page")

    def page(self, nid):
        entry = self.entries.get(nid)
        if not entry:
            return ""
        out = ['<section class="n-sec" aria-labelledby="nContext">',
               '<h2 class="n-sec-h" id="nContext">Context and resources</h2>']
        for body, reviewed, title, citations in entry.get("notes", []):
            if title is not None:
                out.append(f'<h3 class="n-sec-h">{esc(title)}</h3>')
            out.append(f'<p class="fact-t">{esc(body)}</p><p class="rc">Context reviewed {stamp(reviewed)} by ZOTHEOS.</p>')
            if citations:
                out.append('<p class="rc">Sources For This Layer</p><ul class="src-u">')
                for address, label, purpose, receipt in citations:
                    out.append(f'<li><p><a href="{esc(address)}" rel="noopener noreferrer" target="_blank">{esc(label)}'
                               '<span class="sr-only"> (opens in a new tab)</span></a></p>'
                               f'<p class="rc">{esc(receipt["publisher"])}, source reviewed {stamp(receipt["reviewed"])} by ZOTHEOS.</p></li>')
                out.append('</ul>')
        if entry.get("relations"):
            out.append('<h3 class="n-sec-h">Related records</h3>')
        for statement, others, reviewed in entry.get("relations", []):
            names = ", ".join(f'<a href="/nations/{esc(other)}">{esc(self.model.by_id[other]["name"])}</a>' for other in others)
            out.append(f'<p class="note">{esc(statement)}.</p><p>{names}.</p><p class="rc">Context reviewed {stamp(reviewed)} by ZOTHEOS.</p>')
        if entry.get("resources"):
            out.append('<h3 class="n-sec-h">From the publisher&#39;s own pages</h3><ul class="src-u">')
        for address, label, purpose, receipt in entry.get("resources", []):
            out.append(f'<li><p><a href="{esc(address)}" rel="noopener noreferrer" target="_blank">{esc(label)}'
                       '<span class="sr-only"> (opens in a new tab)</span></a></p>'
                       f'<p class="note">{esc(purpose)}</p><p class="rc">{esc(receipt["publisher"])}, '
                       f'source reviewed {stamp(receipt["reviewed"])} by ZOTHEOS.</p></li>')
        if entry.get("resources"):
            out.append('</ul>')
        out.append('<p class="note">This source review is separate from the fact checks above. External pages open only when you follow a link.</p></section>')
        return "\n".join(out)
