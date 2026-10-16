"""Independent reading-navigation acceptance using fictional, isolated records.

Exercise the real public Model, Context and nation_page renderer.  These inputs
are acceptance fixtures, not Nations research, source receipts or browser proof.
Run with ZOTHEOS_TEST_REPO pointing at the repository under review.
"""
import copy
import datetime as dt
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import sys

import pytest

ROOT = Path(os.environ.get("ZOTHEOS_TEST_REPO", Path(__file__).resolve().parents[2]))
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "tools"))
import nations_build as B
import nations_lib as L
from nations_context import Context

DAY = (dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)).isoformat()
OWN = "https://fictional-alpha.example.test/"
HISTORY = OWN + "history/"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class Element:
    def __init__(self, tag, attrs=None, parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs or []), parent
        self.children = []
        self.parts = []

    @property
    def text(self):
        return " ".join(" ".join(part.text if isinstance(part, Element) else part for part in self.parts).split())

    def descendants(self):
        for child in self.children:
            yield child
            yield from child.descendants()


class DOM(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]
        self.feed(html)
        self.elements = list(self.root.descendants())

    def handle_starttag(self, tag, attrs):
        el = Element(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(el)
        self.stack[-1].parts.append(el)
        if tag not in VOID:
            self.stack.append(el)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                return

    def handle_data(self, data):
        self.stack[-1].parts.append(data)

    def by_id(self, value):
        return [el for el in self.elements if el.attrs.get("id") == value]

    def accessible_name(self, el):
        if el.attrs.get("aria-labelledby"):
            return " ".join(target.text for key in el.attrs["aria-labelledby"].split()
                            for target in self.by_id(key))
        return el.attrs.get("aria-label", "")

    def reading_nav(self):
        navs = [el for el in self.elements if el.tag == "nav"
                and self.accessible_name(el).casefold() == "explore this record"]
        assert len(navs) == 1, "One accessible Explore This Record navigation must be emitted"
        return navs[0]


@pytest.fixture
def scenario(tmp_path):
    folder = tmp_path / "data" / "nations"
    (folder / "sources").mkdir(parents=True)

    def fact(key, text):
        return {"id": key, "text": text, "kind": "history", "as_of": "2001",
                "status": "verified", "checked": DAY, "last_verified": DAY,
                "source": {"title": "Fictional source title", "publisher": "Fictional Alpha",
                           "url": HISTORY}}

    alpha = {"id": "fictional-alpha", "name": "Fictional Alpha <&\"",
             "region": "fictional-region", "also": [], "lands": "Fictional river lands.",
             "countries": ["US"], "official_url": OWN, "name_source_url": OWN,
             "facts": [fact("fictional-public-fact", "FICTIONAL PUBLIC FACT"),
                       fact("fictional-held-fact", "FICTIONAL HELD FACT")]}
    beta = dict(copy.deepcopy(alpha), id="fictional-beta", name="Fictional Beta", facts=[])
    docs = {
        "nations.json": {"version": 1, "generated": DAY, "nations": [alpha, beta]},
        "regions.json": {"order": ["fictional-region"], "regions": {
            "fictional-region": {"display": "Fictional Region"}}},
        "countries.json": {"US": "United States"},
        "overrides.json": {"hide_fact": [{"fact": "fictional-held-fact"}],
                           "hide_nation": [], "takedown": []},
        "pronounce_publishers.json": {},
        "site.json": {"contact": "corrections@example.test"},
        "source_priority.json": {"domains": {}, "suffixes": {}},
        "context_links.json": {"version": 1, "links": [
            {"nation": "fictional-alpha", "url": HISTORY, "publisher": "Fictional Alpha", "reviewed": DAY}]},
    }
    context = {
        "reviewed": DAY,
        "public_notes": [{"nation": "fictional-alpha", "title": "Fictional History",
                          "text": "FICTIONAL PUBLIC CONTEXT", "fact_ids": ["fictional-public-fact"]}],
        "official_resources": [{"nation": "fictional-alpha", "label": "Fictional Own History",
                                "url": HISTORY, "purpose": "Fictional publisher reading.",
                                "fact_ids": ["fictional-public-fact"]}],
        "relationships": [],
    }
    return {"root": tmp_path, "folder": folder, "docs": docs, "context": context}


def render(scenario, nation="fictional-alpha", context=True):
    folder = scenario["folder"]
    for filename, doc in scenario["docs"].items():
        (folder / filename).write_text(json.dumps(doc), encoding="utf-8")
    path = folder / "sources" / "fixture.context.json"
    if context:
        path.write_text(json.dumps(scenario["context"]), encoding="utf-8")
    elif path.exists():
        path.unlink()
    model = L.Model(str(scenario["root"]), DAY)
    assert model.errors == [], model.errors
    before = copy.deepcopy(model.raw)
    b = B.Builder.__new__(B.Builder)
    b.root, b.m, b.model = str(scenario["root"]), model, model
    b.contact = model.site["contact"]
    # Isolate the real article/template renderer without loading unrelated fonts
    # or global navigation. The public model and source-context loader are real.
    b.tpl = lambda key: (ROOT / "tools" / "nations" / "templates" / (key + ".html")).read_text(encoding="utf-8")
    b.page = lambda *args: args[-1]
    for n in model.nations:
        n.update(sz="md", fc="brand", sc="latn", lf="brand", af_all="brand")
        for f in n["facts"]:
            f["fc"] = "brand"
    pages = {n["id"]: b.nation_page(n) for n in model.nations}
    assert model.raw == before, "Reading navigation may not rewrite canonical fact/source clocks"
    return pages.get(nation, ""), model, pages


def links(nav):
    return [(el.attrs.get("href"), el.text) for el in nav.descendants() if el.tag == "a"]


def test_reading_navigation_is_visible_static_and_between_own_site_and_lands(scenario):
    html, model, pages = render(scenario)
    dom = DOM(html)
    nav = dom.reading_nav()
    assert "Explore This Record" in nav.text, "The navigation label must be visible as well as accessible"
    assert "hidden" not in nav.attrs and nav.attrs.get("aria-hidden") != "true"
    assert "Explore This Record" in dom.root.text
    own = next(el for el in dom.elements if el.tag == "a" and el.attrs.get("href") == OWN)
    assert dom.elements.index(own) < dom.elements.index(nav) < dom.elements.index(dom.by_id("nLands")[0])
    assert not any(el.tag == "script" or any(k.startswith("on") for k in el.attrs)
                   for el in [nav, *nav.descendants()]), "Reading navigation must work without JavaScript"


def test_links_are_plain_language_native_in_page_anchors_in_reading_order(scenario):
    html, model, pages = render(scenario)
    dom = DOM(html)
    assert links(dom.reading_nav()) == [
        ("#nLands", "Lands"), ("#nFacts", "Facts And Sources"), ("#nContext", "Context And Resources")]


@pytest.mark.parametrize("kind", ["notes", "resources", "relationships"])
def test_any_real_public_context_kind_gets_one_history_link(scenario, kind):
    doc = scenario["context"]
    if kind != "notes": doc["public_notes"] = []
    if kind != "resources": doc["official_resources"] = []
    if kind == "relationships":
        doc["relationships"] = [{"from": "fictional-alpha", "to": ["fictional-beta"],
                                 "relationship": "Distinct fictional records"}]
    html, model, pages = render(scenario)
    dom = DOM(html)
    assert len(dom.by_id("nContext")) == 1
    assert links(dom.reading_nav()).count(("#nContext", "Context And Resources")) == 1


def test_profile_without_context_never_advertises_history(scenario):
    html, model, pages = render(scenario, context=False)
    dom = DOM(html)
    assert not dom.by_id("nContext")
    assert links(dom.reading_nav()) == [("#nLands", "Lands"), ("#nFacts", "Facts And Sources")]
    assert "Context And Resources" not in dom.root.text


@pytest.mark.parametrize("kind", ["notes", "resources", "both"])
def test_fact_holds_remove_dependent_context_and_its_navigation(scenario, kind):
    doc = scenario["context"]
    if kind == "notes": doc["official_resources"] = []
    if kind == "resources": doc["public_notes"] = []
    for field in ("public_notes", "official_resources"):
        for item in doc[field]: item["fact_ids"] = ["fictional-held-fact"]
    html, model, pages = render(scenario)
    dom = DOM(html)
    assert Context(scenario["root"], model).page("fictional-alpha") == ""
    assert "FICTIONAL HELD FACT" not in html and "FICTIONAL PUBLIC CONTEXT" not in html
    assert not dom.by_id("nContext")
    assert not any(href == "#nContext" for href, text in links(dom.reading_nav()))


@pytest.mark.parametrize("control", ["hide_nation", "takedown"])
def test_removed_records_cannot_be_resurrected_by_navigation(scenario, control):
    scenario["docs"]["overrides.json"][control] = [{"nation": "fictional-alpha"}]
    html, model, pages = render(scenario)
    assert "fictional-alpha" not in model.by_id and "fictional-alpha" not in pages
    assert html == ""
    assert Context(scenario["root"], model).page("fictional-alpha") == ""
    assert all("FICTIONAL PUBLIC CONTEXT" not in page for page in pages.values())


def test_native_anchor_targets_are_unique_focusable_section_headings(scenario):
    html, model, pages = render(scenario)
    dom = DOM(html)
    nav = dom.reading_nav()
    for href, label in links(nav):
        targets = dom.by_id(href[1:])
        assert len(targets) == 1
        target = targets[0]
        assert target.tag == "h2", "Native jumps must land on the section heading"
        assert target.attrs.get("tabindex") == "-1", "Programmatic target focus must not add a Tab stop"
        assert target.parent.tag == "section"
        assert target.parent.attrs.get("aria-labelledby") == href[1:]


def test_sources_dates_counts_corrections_and_escaped_name_survive(scenario):
    html, model, pages = render(scenario)
    dom = DOM(html)
    assert dom.by_id("nName")[0].text == 'Fictional Alpha <&"'
    assert 'Fictional Alpha &lt;&amp;&quot;' in html
    assert not any(el.tag in {"script", "img"} for el in dom.elements)
    assert "FICTIONAL PUBLIC FACT" in html and "FICTIONAL HELD FACT" not in html
    assert "Fictional source title" in html and "As of 2001" in dom.root.text
    assert 'class="fcount">1</span>' in html
    assert any(el.tag == "time" and el.attrs.get("datetime") == DAY for el in dom.elements)
    assert "by ZOTHEOS" in dom.root.text and "separate from the fact checks" in dom.root.text
    source_links = [el for el in dom.elements if el.tag == "a" and el.attrs.get("href") == HISTORY]
    assert source_links and all("noopener" in el.attrs.get("rel", "") and "noreferrer" in el.attrs.get("rel", "") for el in source_links)
    assert any(el.tag == "a" and el.text == "Suggest a correction" and el.attrs.get("href", "").startswith("mailto:") for el in dom.elements)
    assert any(el.tag == "a" and el.attrs.get("href") == "/nations/for-nations" for el in dom.elements)


def test_reading_navigation_does_not_require_an_own_site_link(scenario):
    scenario["docs"]["nations.json"]["nations"][0]["official_url"] = None
    html, model, pages = render(scenario, context=False)
    dom = DOM(html)
    nav = dom.reading_nav()
    assert dom.elements.index(dom.by_id("nName")[0]) < dom.elements.index(nav) < dom.elements.index(dom.by_id("nLands")[0])
    assert links(nav) == [("#nLands", "Lands"), ("#nFacts", "Facts And Sources")]
