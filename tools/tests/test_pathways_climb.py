"""The Climb And The Three Lanes (Living Gallery, Batch 1, piece 1) on /nations/paths-to-action.

Fictional data exercises the real renderer in both art variants, and the committed page is read as built. These cases
check structure, counts and the art rules; they do not certify any source, outcome or Nation approval.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

import pytest

REPO = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(REPO / 'tools/tests'))
sys.path.insert(0, str(REPO / 'tools'))
from test_indigenous_pathways import fixture_catalogue, fixture_model, tree  # noqa: E402
import zth_art  # noqa: E402

CSS = (REPO / 'tools/nations/partials/nations.css').read_text(encoding='utf-8')
ART = re.compile(r'\b(pw-climb|pw-route|pw-lanes?|pw-here|zth-[\w-]+)\b')
FORBIDDEN = re.compile(r'gradient|filter|shadow|animation|transition|opacity|blur|mask|mix-blend|color-mix', re.I)


def load_module():
    spec = importlib.util.spec_from_file_location('climb_contract', REPO / 'tools/nations_pathways.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(params=[False, True], ids=['plain', 'stepped'])
def climb(request, tmp_path, monkeypatch):
    # The module nations_pathways imports, whichever copy another test file left in sys.modules.
    monkeypatch.setattr(importlib.import_module('zth_art'), 'ART_STEPS', request.param)
    data, model = fixture_catalogue(), fixture_model()
    path = tmp_path / 'data/nations/pathways.json'
    path.parent.mkdir(parents=True)

    def call(kind='render'):
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf8')
        mod = load_module()
        return mod, getattr(mod, kind)(str(tmp_path), model)

    return data, model, call, request.param


def classes(node):
    return node.attrs.get('class', '').split()


def find(doc, cls, tag=None):
    return [n for n in doc.walk() if cls in classes(n) and (tag is None or n.tag == tag)]


def test_one_climb_whose_four_steps_are_the_method(climb):
    _, _, call, steps = climb
    mod, html = call()
    doc = tree(html)
    figures = find(doc, 'pw-climb', 'figure')
    assert len(figures) == 1
    lists = [n for n in figures[0].walk() if n.tag == 'ol']
    assert len(lists) == 1 and lists[0].attrs.get('aria-label') == mod.METHOD_LABEL
    assert [n.text for n in lists[0].children if getattr(n, 'tag', '') == 'li'] == list(mod.METHOD)
    caption = [n for n in figures[0].walk() if n.tag == 'figcaption']
    assert len(caption) == 1 and caption[0].text == mod.CLIMB_CAPTIONS[steps] + (' ' + zth_art.CREDIT if steps else '')
    # Only the stepped variant draws a riser, so only it may say the step is drawn open.
    assert ('drawn open' in caption[0].text) == steps and ('left open' in caption[0].text) == (not steps)
    assert ('zth-steps' if steps else 'zth-plain') in classes(figures[0])
    # The Climb and its key stay in the hero, before the capabilities section.
    assert html.index('class="pw-climb') < html.index('class="pw-lanes"') < html.index('</header>') < html.index('pw-capabilities')


def test_each_step_carries_one_empty_lane_mark_matching_its_scope(climb):
    data, _, call, _ = climb
    mod, html = call()
    doc = tree(html)
    steps = [n for n in doc.walk() if n.tag == 'article' and 'pw-step' in classes(n)]
    assert len(steps) == sum(len(c['steps']) for c in data['chapters'])
    for step in steps:
        scope = next(c[3:] for c in classes(step) if c[3:] in mod.SCOPES)
        marks = find(step, 'pw-lane')
        assert len(marks) == 1 and marks[0].tag == 'span' and not marks[0].text
        labels = find(step, 'pw-scope', 'p')
        assert len(labels) == 1 and marks[0].parent is labels[0] and labels[0].text == mod.SCOPES[scope]
        # Only the four-corner mark (a proposed app workflow) carries its one empty inner element.
        inner = [n for n in marks[0].children if getattr(n, 'tag', None)]
        assert [n.tag for n in inner] == (['i'] if scope == 'future-app' else []) and not any(n.children for n in inner)


def test_lane_key_lists_exactly_the_scopes_with_defining_notes(climb):
    data, _, call, _ = climb
    mod, html = call()
    doc = tree(html)
    keys = find(doc, 'pw-lanes')
    assert len(keys) == 1
    key = keys[0]
    title = [n for n in key.walk() if n.attrs.get('id') == 'pw-lanes-title']
    assert key.attrs.get('role') == 'group' and key.attrs.get('aria-labelledby') == 'pw-lanes-title'
    assert len(title) == 1 and title[0].text == mod.LANES_TITLE
    rows = [n for n in key.walk() if n.tag == 'div' and n.parent.tag == 'dl']
    assert [classes(r)[0] for r in rows] == ['pw-' + k for k in mod.SCOPES]
    for row, (k, name) in zip(rows, mod.SCOPES.items()):
        dt = [n for n in row.walk() if n.tag == 'dt']
        dd = [n for n in row.walk() if n.tag == 'dd']
        assert dt[0].text == name and dd[0].text == mod.LANE_NOTES[k] and len(find(row, 'pw-lane')) == 1
        # A note defines its lane; it never repeats the lane's name or the capabilities section below the key.
        assert name.lower() not in dd[0].text.lower()
        assert dd[0].text not in ('Available On This Website', 'Clear Boundaries', 'App Workflows Are Proposed')
        assert all(dd[0].text.rstrip('.') not in p for ps in data['capabilities'].values() for p in ps)


def test_practice_label_carries_the_mark_of_the_lane_it_names(climb):
    _, _, call, _ = climb
    mod, html = call()
    doc = tree(html)
    blocks = [n for n in doc.walk() if n.tag == 'section' and 'pw-practice' in classes(n)]
    for block in blocks:
        label = find(block, 'pw-scope', 'p')[0]
        assert 'pw-reader-controlled' in classes(label) and label.text.endswith(mod.SCOPES['reader-controlled'])
        assert len(find(label, 'pw-lane')) == 1


def test_chapter_marker_rows_count_public_chapters_and_fill_the_current_one(climb):
    data, model, call, _ = climb
    _, html = call()
    doc = tree(html)
    total = len(data['chapters'])
    rows = find(doc, 'pw-here')
    assert len(rows) == total
    for position, row in enumerate(rows, 1):
        squares = [n for n in row.children if getattr(n, 'tag', '') == 'i']
        assert len(squares) == total and not row.text
        assert [i for i, s in enumerate(squares, 1) if 'on' in classes(s)] == [position]
        eyebrow = row.parent
        assert 'pw-eyebrow' in classes(eyebrow)
        assert eyebrow.text == 'Pathway ' + str(position).zfill(2) + ' of ' + str(total)
    # A named-source hold removes a chapter: every row and every " of N" follows the public count.
    data['sources'][0]['nation'] = 'fixture-nation'
    model.by_id.clear()
    _, held = call()
    rows = find(tree(held), 'pw-here')
    assert len(rows) == total - 1
    assert all(len([n for n in r.children if getattr(n, 'tag', '') == 'i']) == total - 1 for r in rows)
    assert ' of ' + str(total - 1) in tree(held).text and ' of ' + str(total) not in tree(held).text


def test_existing_guards_hold_with_the_art(climb):
    _, _, call, _ = climb
    _, html = call()
    doc = tree(html)
    assert not [n for n in doc.walk() if n.tag in {'svg', 'img', 'form', 'input', 'button', 'script', 'canvas'}]
    assert len([n for n in doc.walk() if n.tag == 'nav']) == 1
    ids = [n.attrs['id'] for n in doc.walk() if 'id' in n.attrs]
    assert len(ids) == len(set(ids))
    assert not re.search(r'\bon\w+\s*=|\bstyle\s*=|tabindex="0"', html, re.I)


def test_every_art_element_is_marked_original_and_carries_its_variant(climb):
    _, _, call, steps = climb
    _, html = call()
    doc = tree(html)
    origin = [n for n in doc.walk() if n.attrs.get('data-origin') == 'zotheos-original']
    variant = [n for n in doc.walk() if {'zth-plain', 'zth-steps'} & set(classes(n))]
    assert origin and origin == variant
    want = 'zth-steps' if steps else 'zth-plain'
    assert all(want in classes(n) for n in origin)
    assert ('zth-plain' if steps else 'zth-steps') not in html


def test_credit_line_appears_once_only_where_stepped_geometry_is_drawn(climb):
    _, _, call, steps = climb
    _, html = call()
    assert html.count(zth_art.CREDIT) == (1 if steps else 0)


def test_plain_text_briefs_carry_no_art(climb):
    _, _, call, _ = climb
    mod, brief = call('action_brief')
    _, briefs = call('chapter_briefs')
    for text in [brief, *briefs.values()]:
        assert 'zotheos-original' not in text and mod.LANES_TITLE not in text
        assert not any(c in text for c in mod.CLIMB_CAPTIONS.values())
        assert not any(n in text for n in mod.LANE_NOTES.values())


def test_art_helpers_fail_closed():
    for method in (['A', 'B', 'C'], ['A', 'A', 'B', 'C'], ['A', 'B', 'C', ' ']):
        with pytest.raises(ValueError):
            zth_art.climb(method, 'Label', 'Caption')
    for position, total in [(0, 3), (4, 3), (1, 0), ('1', 3), (True, 3)]:
        with pytest.raises(ValueError):
            zth_art.here(position, total)


def test_the_committed_guide_draws_the_climb_and_a_mark_on_every_step():
    """The page as built from the real catalogue: one Climb of the method, the key, one mark per step and one row per
    chapter, all counted from the same catalogue the page is built from."""
    mod = load_module()
    page = (REPO / 'nations/paths-to-action.html').read_text(encoding='utf-8')
    doc = tree(page)
    route = find(doc, 'pw-route', 'ol')
    assert len(route) == 1 and [n.text for n in route[0].children if getattr(n, 'tag', '') == 'li'] == list(mod.METHOD)
    steps = [n for n in doc.walk() if n.tag == 'article' and 'pw-step' in classes(n)]
    assert steps and all(len(find(s, 'pw-lane')) == 1 for s in steps)
    chapters = [n for n in doc.walk() if n.tag == 'section' and 'pw-chapter' in classes(n)]
    rows = find(doc, 'pw-here')
    assert len(rows) == len(chapters) and all(len(find(r, 'on')) == 1 for r in rows)
    assert all(len([i for i in r.children if getattr(i, 'tag', '') == 'i']) == len(chapters) for r in rows)
    guide = find(doc, 'pathways', 'div')
    assert len(guide) == 1 and not [n for n in guide[0].walk() if n.tag in {'svg', 'img'}]


# ---------------------------------------------------------------------------------------------- static art lint
def _rules(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    depth, start, out = 0, 0, []
    for i, ch in enumerate(css):
        if ch == '{':
            if depth == 0:
                sel, open_at = css[start:i].strip(), i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                body = css[open_at + 1:i]
                out.extend(_rules(body) if sel.startswith('@') else [(sel, body)])
                start = i + 1
    return out


def test_art_css_is_flat_and_static():
    """Static half of the art lint (the evidence pack checks computed styles in Chrome): rules that draw the art use no
    gradient, filter, shadow, opacity, mix, animation or transition, and no broad rule animates the art."""
    rules = _rules(CSS)
    art = [(s, b) for s, b in rules if ART.search(s) or re.search(r'\.pw-(website-now|reader-controlled|future-app|lane)\b', s)]
    assert len(art) >= 20, 'The art rules are expected in the Nations stylesheet.'
    for sel, body in art:
        assert not FORBIDDEN.search(body), sel
    for sel, body in rules:
        if not re.search(r'(animation|transition)[\w-]*\s*:\s*(?!\s*none\b)', body):
            continue
        for part in sel.split(','):
            assert not ART.search(part), part
            last = re.split(r'[\s>+~]+', part.strip())[-1]
            last = re.sub(r'::?[\w-]+(\([^)]*\))?|\[[^\]]*\]', '', last)
            assert not re.fullmatch(r'\*|figure|figcaption|ol|li|span|i|dl|dt|dd|div|p', last), 'A broad rule would animate the art: ' + part


def test_meaning_carrying_lines_are_two_pixels_or_more():
    """At 125% and 150% display scales a 1px line antialiases; every line that carries a lane's meaning is 2px or more,
    and the double rule keeps a 2px gap so it stays double."""
    rules = dict(_rules(CSS))
    lanes = {k: v for k, v in rules.items() if k.startswith('.pw-step.pw-')}
    styles = sorted(re.search(r'border-left:(\d+)px (\w+)', v).groups() for v in lanes.values())
    assert styles == [('2', 'dotted'), ('2', 'solid'), ('6', 'double')]


def test_the_plain_variant_ships_until_the_roots_decision():
    """The owner ships the plain variant; no stepped CSS ships until his Roots decision. Flipping ART_STEPS without the
    stepped rules (or shipping the rules without the decision) fails here."""
    stepped_rules = [s for s, _ in _rules(CSS) if 'zth-steps' in s]
    assert zth_art.ART_STEPS is False
    assert stepped_rules == [], 'stepped CSS waits for the Roots decision'
    assert 'zth-steps' not in (REPO / 'nations/paths-to-action.html').read_text(encoding='utf-8')
