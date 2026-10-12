"""Bounded, reviewed nation-page context. Only the canonical public model supplies record names/links."""
import datetime
import html
import json
from pathlib import Path
import re

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


def date(value, build_date):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("context: review date must be YYYY-MM-DD")
    try:
        result = datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("context: invalid review date") from exc
    if result > datetime.date.fromisoformat(build_date):
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
            links[key] = {"reviewed": date(entry.get("reviewed"), model.build_date),
                          "publisher": text(entry.get("publisher"), 160)}
        records = 0
        for path in files:
            if path.resolve().parent != source_folder.resolve():
                raise ValueError("context: context path escapes source folder")
            doc = read_json(path)
            reviewed = date(doc.get("reviewed"), model.build_date)
            groups = {"public_notes": items(doc, "public_notes", 64),
                      "official_resources": items(doc, "official_resources", 32),
                      "relationships": items(doc, "relationships", 32)}
            records += sum(len(v) for v in groups.values())
            if records > MAX_RECORDS:
                raise ValueError("context: more than 256 public context records")
            for note in groups["public_notes"]:
                nid = self.nation(note.get("nation"), known)
                body = text(note.get("text"))
                if self.visible(nid, note, public_facts):
                    self.add(nid, "notes", (body, reviewed))
            for resource in groups["official_resources"]:
                nid = self.nation(resource.get("nation"), known)
                address = text(resource.get("url"), 700)
                key = (nid, address)
                if key not in links:
                    raise ValueError("context: resource URL not on exact nation/link allowlist")
                label = text(resource.get("label"), 160)
                purpose = text(resource.get("purpose"))
                if self.visible(nid, resource, public_facts):
                    self.add(nid, "resources", (resource["url"], label, purpose, links[key]))
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
        for body, reviewed in entry.get("notes", []):
            out.append(f'<p class="fact-t">{esc(body)}</p><p class="rc">Context reviewed {stamp(reviewed)} with AI assistance.</p>')
        if entry.get("relations"):
            out.append('<h3 class="n-sec-h">Related records</h3>')
        for statement, others, reviewed in entry.get("relations", []):
            names = ", ".join(f'<a href="/nations/{esc(other)}">{esc(self.model.by_id[other]["name"])}</a>' for other in others)
            out.append(f'<p class="note">{esc(statement)}.</p><p>{names}.</p><p class="rc">Context reviewed {stamp(reviewed)} with AI assistance.</p>')
        if entry.get("resources"):
            out.append('<h3 class="n-sec-h">From the publisher&#39;s own pages</h3><ul class="src-u">')
        for address, label, purpose, receipt in entry.get("resources", []):
            out.append(f'<li><p><a href="{esc(address)}" rel="noopener noreferrer" target="_blank">{esc(label)}'
                       '<span class="sr-only"> (opens in a new tab)</span></a></p>'
                       f'<p class="note">{esc(purpose)}</p><p class="rc">{esc(receipt["publisher"])}, '
                       f'source reviewed {stamp(receipt["reviewed"])} with AI assistance.</p></li>')
        if entry.get("resources"):
            out.append('</ul>')
        out.append('<p class="note">This source review is separate from the fact checks above. External pages open only when you follow a link.</p></section>')
        return "\n".join(out)
