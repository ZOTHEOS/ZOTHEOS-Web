"""Doors (Living Gallery, Batch 1, piece 4): the homepage explore section draws only computed truth, in a static,
safe shape. The committed page is read as built and checked against the pages each door opens onto; fictional values
exercise the generator. When a Codex data batch changes a count, test_check_passes_on_the_built_page fails with the
one-line fix: py -3.10 tools/landing_doors.py
"""
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

R = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
INDEX = R / 'index.html'
if str(R / 'tools') not in sys.path:
    sys.path.insert(0, str(R / 'tools'))
sys.dont_write_bytecode = True
import landing_doors as LD  # noqa: E402
import zth_art as A  # noqa: E402

HREFS = ['/nations/paths-to-action', '/theater', '/nations/directory', '/nations/resources', '/game']
DOOR_CLASSES = ('ws-door', 'ws-fig', 'ws-grid', 'ws-ledger', 'ws-bar', 'ws-rail', 'ws-regions', 'ws-climb', 'ws-credit',
                'ws-index', 'ws-action', 'ws-pathways', 'ws-theater', 'ws-nations', 'ws-history', 'ws-game', 'ws-wide',
                'ws-g2')


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent, self.kids, self.data = tag, dict(attrs), parent, [], []

    def walk(self):
        yield self
        for k in self.kids:
            yield from k.walk()

    def text(self):
        return ''.join(d if isinstance(d, str) else d.text() for d in self.data)

    def cls(self):
        return (self.attrs.get('class') or '').split()


class Tree(HTMLParser):
    VOID = {'meta', 'link', 'br', 'img', 'input', 'hr', 'source', 'col', 'area', 'base', 'wbr', 'rect', 'use', 'path'}

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root = Node('#root', {}, None)
        self.cur = self.root
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.kids.append(n)
        self.cur.data.append(n)
        if tag not in self.VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.kids.append(n)
        self.cur.data.append(n)

    def handle_endtag(self, tag):
        n = self.cur
        while n is not self.root and n.tag != tag:
            n = n.parent
        if n is not self.root:
            self.cur = n.parent

    def handle_data(self, d):
        self.cur.data.append(d)


@pytest.fixture(scope='module')
def page():
    return INDEX.read_text(encoding='utf-8')


@pytest.fixture(scope='module')
def hub(page):
    t = Tree(page)
    s = [n for n in t.root.walk() if n.attrs.get('id') == 'explore-zotheos']
    assert len(s) == 1
    return s[0]


@pytest.fixture(scope='module')
def data():
    return LD.gather(str(R))


def doors(hub):
    return [n for n in hub.walk() if n.tag == 'article' and 'ws-door' in n.cls()]


def by_class(node, c):
    return [n for n in node.walk() if c in n.cls()]


def steps_of(hub):
    figs = by_class(hub, 'ws-fig')
    kinds = {('zth-steps' in f.cls(), 'zth-plain' in f.cls()) for f in figs}
    assert kinds in ({(True, False)}, {(False, True)}), 'every door figure carries exactly one variant class'
    return kinds == {(True, False)}


def test_check_passes_on_the_built_page(hub):
    """The page is current: every number on the doors is today's count. A stale count prints the one-line fix."""
    assert steps_of(hub) == A.ART_STEPS, 'the page variant differs from ART_STEPS: run tools/landing_doors.py'
    assert LD.main(['--root', str(R), '--page', str(INDEX), '--check']) == 0


def guide_lanes():
    """Each public chapter's step lanes, read from the built guide itself (class pw-step pw-<scope>)."""
    paths = (R / 'nations' / 'paths-to-action.html').read_text(encoding='utf-8')
    sections = paths.split('<section class="pw-chapter"')[1:]
    return [re.findall(r'<article class="pw-step pw-([a-z-]+)"', s) for s in sections]


def test_counts_agree_with_the_pages_they_open(hub, data):
    lanes = guide_lanes()
    chapters = len(lanes)
    cap = {d.attrs['aria-labelledby']: [n.text() for n in d.walk() if n.tag == 'figcaption'] for d in doors(hub)}
    assert cap['wsd-pathways'] == [f'{chapters} pathways. Each includes something you can prepare offline. '
                                   + LD.lane_line(dict(data, lanes=lanes))]
    # The lane sentence is true of the published guide: one step in each lane, in every chapter.
    if all(sorted(c) == sorted(data['scopes']) for c in lanes):
        assert 'Each also has one step on this website, one you do yourself and one proposed for the app.' in cap['wsd-pathways'][0]
    theater = (R / 'theater.html').read_text(encoding='utf-8')
    records = len(set(re.findall(r'data-theater-film="([^"]+)"', theater)))
    films = json.loads((R / 'data/theater/films.json').read_text(encoding='utf-8'))['films']
    ledger = by_class(hub, 'ws-ledger')[0]
    rows = [(r.kids[0].text(), int(by_class(r, 'n')[0].text())) for r in ledger.kids if r.tag == 'div']
    import theater_build as T
    want = [(T.KINDS[k], sum(f['viewing'] == k for f in films)) for k in LD.WATCH_ORDER]
    assert rows == want and sum(c for _, c in rows) == records == len(films)
    assert cap['wsd-theater'] == [f'{records} records in {LD.word(len(rows))} viewing types.']
    about = (R / 'nations' / 'about.html').read_text(encoding='utf-8')
    n = int(re.search(r'This list holds ([\d,]+) nations', about).group(1).replace(',', ''))
    import nations_lib as L
    regions = L.Model(str(R)).regions
    cells = [int(li.text()) for li in by_class(hub, 'ws-regions')[0].kids if li.tag == 'li']
    assert len(cells) == len(regions) and sum(cells) == n and cells == data['region_counts']
    assert cap['wsd-nations'] == [f'{n:,} profiles in {len(regions)} regions so far, from {min(cells)} in the least '
                                  f'covered region to {max(cells)} in the most.']
    res = (R / 'nations' / 'resources.html').read_text(encoding='utf-8')
    hf, hn = re.search(r'([\d,]+) published historical facts across ([\d,]+) nations', res).groups()
    assert cap['wsd-history'][0].startswith(f'{hf} published historical facts across {hn} Nations. ')
    rail = by_class(hub, 'ws-rail')[0]
    dated = sum(1 for b in by_class(rail, 'ws-rail-dated')[0].kids for i in b.kids if i.tag == 'i')
    undated = sum(1 for i in by_class(rail, 'ws-rail-undated')[0].kids if i.tag == 'i')
    assert dated + undated == int(hf.replace(',', '')) and (dated, undated) == (sum(data['decades'].values()), data['undated'])
    keys = [by_class(k, 'n')[0].text() for k in by_class(rail, 'ws-rail-key')]
    assert keys == [str(dated), str(undated)]


def test_regions_are_equal_unranked_cells_in_directory_order(hub, data):
    cells = [li for li in by_class(hub, 'ws-regions')[0].kids if li.tag == 'li']
    assert by_class(hub, 'ws-regions')[0].attrs.get('aria-hidden') == 'true'
    assert [int(c.text()) for c in cells] == data['region_counts']   # directory order, never sorted
    assert not any(c.attrs for c in cells)                           # every cell identical: no class, no size per region


def test_every_decade_slot_between_the_first_and_last_is_drawn_and_none_is_guessed(hub, data):
    rail = by_class(hub, 'ws-rail')[0]
    cols = [b for b in by_class(rail, 'ws-rail-dated')[0].kids if b.tag == 'b']
    lo, hi = min(data['decades']), max(data['decades'])
    assert len(cols) == (hi - lo) // 10 + 1 and 'style' not in rail.attrs
    assert [sum(1 for i in b.kids if i.tag == 'i') for b in cols] == [data['decades'].get(y, 0) for y in range(lo, hi + 10, 10)]
    axis = [s.text() for s in by_class(rail, 'ws-rail-axis')[0].kids]
    assert axis == [f'{lo}s', f'{hi}s']
    keys = [k.text() for k in by_class(rail, 'ws-rail-key')]
    # Plain parallel keys; screen readers hear the decade range, which the axis shows only to the eye.
    assert keys[0] == f'{sum(data["decades"].values())} Year given, from the {lo}s to the {hi}s'
    assert keys[1] == f'{data["undated"]} No year given'


def test_paths_number_word_and_method_follow_the_guide(hub, data):
    door = [d for d in doors(hub) if d.attrs['aria-labelledby'] == 'wsd-pathways'][0]
    para = [n for n in door.kids if n.tag == 'p'][0].text()
    assert para.startswith(LD.word(data['chapters']).capitalize() + ' practical pathways ')
    paths = (R / 'nations' / 'paths-to-action.html').read_text(encoding='utf-8')
    route = re.search(r'<ol class="pw-route"[^>]*>(.*?)</ol>', paths).group(1)
    assert tuple(re.findall(r'<li>(.*?)</li>', route)) == data['method']
    climb = by_class(door, 'ws-climb')[0]
    assert climb.tag == 'ol' and climb.attrs.get('aria-label') == 'From Reading To A Decision'
    assert [li.text() for li in climb.kids if li.tag == 'li'] == list(data['method'])
    # No lane legend on the homepage: no step here carries a mark, so a key would key nothing.
    assert not by_class(hub, 'ws-lanes') and not by_class(hub, 'ws-lane')


def test_heading_comes_before_the_figure_and_the_link_comes_last(hub):
    for d in doors(hub):
        kids = [k for k in d.kids]
        tags = [('fig' if 'ws-fig' in k.cls() else k.tag) for k in kids]
        assert tags[:3] == ['span', 'h3', 'p'] and tags[-1] == 'a'
        assert tags.index('h3') < (tags.index('fig') if 'fig' in tags else len(tags))


def test_the_game_door_draws_nothing_and_no_figure_descends(hub):
    game = [d for d in doors(hub) if d.attrs['aria-labelledby'] == 'wsd-game'][0]
    assert not by_class(game, 'ws-fig') and not [n for n in game.walk() if n.tag == 'svg']
    assert not by_class(hub, 'ws-drop')


def test_theater_rows_come_in_two_groups_never_sorted_by_count(hub):
    ledger = by_class(hub, 'ws-ledger')[0]
    rows = [r for r in ledger.kids if r.tag == 'div']
    marked = [i for i, r in enumerate(rows) if 'ws-g2' in r.cls()]
    assert marked == [len(LD.WATCH_GROUPS[0])]
    assert set(LD.WATCH_ORDER) == {k for g in LD.WATCH_GROUPS for k in g} and len(LD.WATCH_ORDER) == 6


def test_hub_keeps_every_destination_and_each_door_has_exactly_one_link(hub):
    ds = doors(hub)
    assert [d.attrs['aria-labelledby'] for d in ds] == ['wsd-pathways', 'wsd-theater', 'wsd-nations', 'wsd-history', 'wsd-game']
    for d, href in zip(ds, HREFS):
        links = [n for n in d.walk() if n.tag == 'a']
        assert len(links) == 1 and links[0].attrs['href'] == href and 'ws-action' in links[0].cls()
        assert [n for n in d.walk() if n.tag == 'h3' and n.attrs.get('id') == d.attrs['aria-labelledby']]
    assert set(HREFS) <= {n.attrs.get('href') for n in hub.walk() if n.tag == 'a'}


def test_art_is_static_original_and_wordless(hub, page):
    for f in by_class(hub, 'ws-fig'):
        assert f.attrs.get('data-origin') == 'zotheos-original'
    for svg in [n for n in hub.walk() if n.tag == 'svg']:
        assert svg.attrs.get('aria-hidden') == 'true' and svg.attrs.get('focusable') == 'false'
        assert svg.attrs.get('shape-rendering') == 'crispEdges'
        assert not [n for n in svg.walk() if n.tag in ('text', 'image', 'foreignobject', 'use', 'path', 'circle')]
        for r in [n for n in svg.walk() if n.tag == 'rect']:
            assert set(r.attrs) == {'width', 'height'} and all(re.fullmatch(r'\d+', r.attrs[k]) for k in r.attrs)
    for bad in ('script', 'img', 'form', 'input', 'button', 'iframe', 'video', 'audio', 'picture'):
        assert not [n for n in hub.walk() if n.tag == bad]
    # No inline style attribute: the figures survive a future hash-only style policy.
    i, j = page.find(LD.START), page.find(LD.END)
    assert not re.search(r'\sstyle\s*=', page[i:j])


def test_credit_line_appears_only_with_the_stepped_variant(hub):
    credits = by_class(hub, 'ws-credit')
    if steps_of(hub):
        assert [c.text() for c in credits] == [A.CREDIT]
    else:
        assert not credits


def test_door_css_has_no_gradient_glow_motion_or_fade(page):
    styles = re.findall(r'<style[^>]*>(.*?)</style>', page, re.S)
    css = re.sub(r'/\*.*?\*/', '', '\n'.join(styles), flags=re.S)
    rules = re.findall(r'([^{}]+)\{([^{}]*)\}', css)
    hit = [(sel.strip(), body) for sel, body in rules if re.search(r'\.(%s)(?![\w-])' % '|'.join(DOOR_CLASSES), sel)]
    assert hit, 'door rules not found'
    for sel, body in hit:
        b = body.lower()
        assert 'gradient' not in b and 'shadow' not in b and 'blur' not in b and 'filter' not in b, sel
        assert not re.search(r'(^|;)\s*opacity\s*:', b), sel
        for prop in ('animation', 'transition'):
            for m in re.finditer(r'(?:^|;)\s*%s(?:-[a-z-]+)?\s*:\s*([^;]+)' % prop, b):
                assert m.group(1).strip() == 'none', (sel, prop)
    # The Climb is drawn by the guide's rule set: the fourth slot left open between two ticks. No stepped CSS ships
    # until the owner's Roots decision.
    assert '.zth-plain .ws-climb li:last-child::after {height:8px;border:solid var(--ink-2);border-width:0 2px;}' in '\n'.join(styles)
    assert A.ART_STEPS is False and not [sel for sel, _ in rules if 'zth-steps' in sel]


def test_no_dash_and_unique_ids(page, hub):
    i, j = page.find(LD.START), page.find(LD.END)
    assert '—' not in page[i:j] and '–' not in page[i:j]
    ids = re.findall(r'\sid="([^"]+)"', page)
    assert len(ids) == len(set(ids))


def test_render_follows_the_data_not_a_typed_number(data):
    d = dict(data, chapters=9, profiles=1, region_counts=[1], undated=0, history_facts=sum(data['decades'].values()))
    out = LD.render(d, False)
    assert 'Nine practical pathways' in out and '9 pathways. Each includes' in out
    assert '1 profile in 1 region so far.' in out
    assert 'ws-rail-undated' not in out and 'No year given' not in out
    out = LD.render(dict(data, chapters=1, lanes=data['lanes'][:1]), True)
    assert 'One practical pathway through' in out and '1 pathway. It includes' in out and 'It also has one' in out
    assert A.CREDIT in out
    uneven = dict(data, lanes=[['website-now', 'website-now', 'future-app']] + data['lanes'][1:])
    assert 'Together they hold' in LD.lane_line(uneven) and 'Each also has' not in LD.lane_line(uneven)
    with pytest.raises(LD.DoorsError):
        LD.render(dict(data, region_counts=data['region_counts'][:-1]), False)


def test_unknown_viewing_type_fails_closed(monkeypatch):
    import theater_build as T
    monkeypatch.setattr(T, 'KINDS', dict(T.KINDS, **{'newkind': 'New Kind'}))
    with pytest.raises(LD.DoorsError):
        LD.gather(str(R))


def test_climb_and_bars_fail_closed():
    with pytest.raises(ValueError):
        A.door_climb(['A', 'B', 'C'], 'Label')
    with pytest.raises(ValueError):
        A.door_climb(['A', 'A', 'B', 'C'], 'Label')
    for value, top in [(-1, 5), (6, 5), (1, 0), (1.5, 5), (True, 5)]:
        with pytest.raises(ValueError):
            A.bar(value, top)
    svg = A.bar(18, 67)
    assert 'viewBox="0 0 67 1"' in svg and 'width="18"' in svg and 'crispEdges' in svg and 'style' not in svg


def test_the_theater_door_keeps_the_theater_chapter_pictogram(hub, page):
    """The live Theater chapter draws its pictogram on the gateway's Theater door (.ws-theater::after) and sizes it
    from --wpad; the door keeps that class, and the door padding is that same --wpad on every width."""
    theater = [d for d in doors(hub) if d.attrs['aria-labelledby'] == 'wsd-theater'][0]
    assert 'ws-theater' in theater.cls()
    assert '.ws-door {--wpad:30px;' in page and 'padding:var(--wpad);' in page and '.ws-door{--wpad:22px;}' in page
    assert '.ws-theater::after {' in page and '.ws-theater { position: relative; --wsb: var(--cochineal); --wpad: 30px; }' in page


def test_the_section_reserves_its_measured_height_in_each_band(page):
    """content-visibility skips the section until it nears; --cis holds the measured content height per band, so
    anchor jumps land where they should. Each value must be at least the doors' own height there."""
    values = [int(v) for v in re.findall(r'#explore-zotheos \{ --cis: (\d+)px; \}', page)]
    assert len(values) == 3 and values[0] < values[1] < values[2] and values[0] > 1300
