"""Independent chapter-local reader shortcuts, written before implementation.

The actual renderer receives fictional records. Native same-page links must
reach useful public content without JavaScript, collapsed reading or new data
collection. These cases do not certify source truth or community permission.
"""
import copy
import os
from pathlib import Path
import sys

import pytest

REPO = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(REPO / 'tools' / 'tests'))
from test_indigenous_pathways import guide, tree  # noqa: E402,F401


PREPARE = 'Prepare A Brief'
EXAMPLES = 'Sourced Examples'
SOURCES = 'Sources And Further Reading'
LABELS = {PREPARE, EXAMPLES, SOURCES}


def chapter_block(doc, chapter):
    matches = [n for n in doc.walk() if n.tag == 'section'
               and n.attrs.get('aria-labelledby') == 'pw-' + chapter['id']]
    assert len(matches) == 1, 'Each public pathway retains its own named reading section.'
    return matches[0]


def shortcuts(block):
    return [n for n in block.walk() if n.tag == 'a' and n.text.strip() in LABELS]


def target_for(doc, link):
    href = link.attrs.get('href', '')
    assert href.startswith('#') and len(href) > 1, 'Reader shortcuts use native same-document fragments.'
    matches = [n for n in doc.walk() if n.attrs.get('id') == href[1:]]
    assert len(matches) == 1, 'Every shortcut resolves to exactly one real public target.'
    return matches[0]


def find_shortcut(block, label):
    matches = [n for n in shortcuts(block) if n.text.strip() == label]
    assert len(matches) == 1, 'A reader must be able to jump directly to ' + label + '.'
    return matches[0]


def test_every_chapter_offers_direct_routes_to_preparing_and_evidence_before_the_steps(guide):
    data, _, call = guide
    doc = tree(call())
    for chapter in data['chapters']:
        block = chapter_block(doc, chapter)
        prepare, sources = find_shortcut(block, PREPARE), find_shortcut(block, SOURCES)
        order = list(block.walk())
        intro = [n for n in order if n.tag == 'p' and n.text == chapter['intro']]
        first_step = [n for n in order if n.tag == 'h3' and n.text == chapter['steps'][0]['title']]
        assert len(intro) == len(first_step) == 1
        assert order.index(intro[0]) < order.index(prepare) < order.index(first_step[0])
        assert order.index(intro[0]) < order.index(sources) < order.index(first_step[0])


def test_prepare_shortcut_reaches_real_heading_next_to_selected_deliverable_and_native_download(guide):
    data, _, call = guide
    doc = tree(call())
    for chapter in data['chapters']:
        block = chapter_block(doc, chapter)
        target = target_for(doc, find_shortcut(block, PREPARE))
        assert target in list(block.walk()) and target.tag == 'h3'
        assert 'prepare' in target.text.lower()
        assert target.attrs.get('tabindex') == '-1'
        assert chapter['deliverable'] in target.parent.text
        downloads = [n for n in target.parent.walk() if n.tag == 'a'
                     and n.attrs.get('href') == '/static/nations/action-brief-' + chapter['id'] + '.txt']
        assert len(downloads) == 1 and 'download' in downloads[0].attrs


def test_source_shortcut_reaches_focusable_heading_with_this_chapters_exact_sources_and_clocks(guide):
    data, _, call = guide
    doc = tree(call())
    for chapter in data['chapters']:
        block = chapter_block(doc, chapter)
        target = target_for(doc, find_shortcut(block, SOURCES))
        assert target in list(block.walk()) and target.tag == 'h3'
        assert target.text.strip() == SOURCES and target.attrs.get('tabindex') == '-1'
        refs = set(chapter['source_ids']) | {sid for step in chapter['steps'] for sid in step['source_ids']}
        expected = [s for s in data['sources'] if s['id'] in refs]
        for source in expected:
            links = [n for n in target.parent.walk() if n.tag == 'a' and n.attrs.get('href') == source['url']]
            assert len(links) == 1 and source['title'] in links[0].text
            assert source['publisher'] in target.parent.text
            assert any(n.tag == 'time' and n.attrs.get('datetime') == source['reviewed'] for n in target.parent.walk())
        assert 'not endorsements' in target.parent.text


def test_public_example_route_exists_only_for_chapter_with_visible_example_and_preserves_old_anchor(guide):
    data, _, call = guide
    doc = tree(call())
    first = chapter_block(doc, data['chapters'][0])
    example_link = find_shortcut(first, EXAMPLES)
    assert example_link.attrs['href'] == '#pw-cases-land-and-water'
    target = target_for(doc, example_link)
    assert target.tag == 'h3' and target.attrs.get('tabindex') == '-1'
    assert 'Exact public fact A sentinel.' in target.parent.text
    assert not any(n.text.strip() == EXAMPLES for n in shortcuts(chapter_block(doc, data['chapters'][1])))


@pytest.mark.parametrize('hold', ['nation', 'one-fact', 'all-facts'])
def test_held_example_has_no_example_shortcut_or_identity_leak_but_retains_public_brief_and_sources(guide, hold):
    data, model, call = guide
    if hold == 'nation':
        model.by_id.clear()
    elif hold == 'one-fact':
        model.by_id['fixture-nation']['facts'].pop()
    else:
        model.by_id['fixture-nation']['facts'].clear()
    doc = tree(call())
    first = chapter_block(doc, data['chapters'][0])
    assert {n.text.strip() for n in shortcuts(first)} == {PREPARE, SOURCES}
    assert 'pw-cases-land-and-water' not in [n.attrs.get('id') for n in doc.walk()]
    for private in ['Fixture Nation', 'Exact public fact A sentinel.', '/nations/fixture-nation']:
        assert private not in call()
    for label in [PREPARE, SOURCES]:
        assert target_for(doc, find_shortcut(first, label)) in list(first.walk())


def test_held_framework_chapter_leaves_no_dangling_shortcut_or_hidden_deliverable(guide):
    data, model, call = guide
    data['sources'][0]['nation'] = 'fixture-nation'
    model.by_id.clear()
    doc = tree(call())
    assert not [n for n in doc.walk() if n.tag == 'a' and 'land-and-water' in n.attrs.get('href', '')]
    for held in ['Land And Water', 'Deliverable sentinel', 'River Programme']:
        assert held not in doc.text
    remaining = chapter_block(doc, data['chapters'][1])
    assert {n.text.strip() for n in shortcuts(remaining)} == {PREPARE, SOURCES}
    for link in shortcuts(remaining):
        target_for(doc, link)


def test_all_fragments_resolve_and_keyboard_targets_remain_unique_after_reordering_and_renaming(guide):
    data, _, call = guide
    def mapping():
        doc = tree(call())
        ids = [n.attrs['id'] for n in doc.walk() if 'id' in n.attrs]
        assert len(ids) == len(set(ids))
        result = {}
        for chapter in data['chapters']:
            block = chapter_block(doc, chapter)
            result[chapter['id']] = {n.text.strip(): n.attrs['href'] for n in shortcuts(block)}
            assert {PREPARE, SOURCES} <= result[chapter['id']].keys()
            for n in shortcuts(block):
                target = target_for(doc, n)
                assert target.attrs.get('tabindex') == '-1'
        for n in doc.walk():
            if n.tag == 'a' and n.attrs.get('href', '').startswith('#'):
                target_for(doc, n)
        return result
    before = mapping()
    data['chapters'].reverse()
    data['chapters'][0]['title'] = 'A Renamed Pathway & Its Readers'
    assert mapping() == before


def test_native_routes_keep_one_chapter_navigation_and_open_reading_without_new_browser_capabilities(guide):
    data, _, call = guide
    html, doc = call(), tree(call())
    assert len([n for n in doc.walk() if n.tag == 'nav']) == 1
    forbidden = {'script', 'iframe', 'form', 'input', 'textarea', 'select', 'button', 'audio', 'video', 'img'}
    assert not [n for n in doc.walk() if n.tag in forbidden or any(k.startswith('on') for k in n.attrs)]
    for chapter in data['chapters']:
        block = chapter_block(doc, chapter)
        assert len(shortcuts(block)) >= 2
        assert not [n for n in block.walk() if n.tag == 'details' and chapter['deliverable'] in n.text]
        for value in [chapter['intro'], chapter['deliverable'], chapter['reflection'], *chapter['verify']]:
            assert value in block.text
        for step in chapter['steps']:
            assert step['text'] in block.text
    assert 'this page has no form or upload' in doc.text.lower()
    assert 'localStorage' not in html and 'fetch(' not in html


def test_chapter_titles_in_accessible_shortcuts_remain_text_and_catalogue_is_not_mutated(guide):
    data, model, call = guide
    attack = '<svg onload="alert(1)"> & "reader"'
    data['chapters'][0]['title'] = attack
    before_data, before_model = copy.deepcopy(data), copy.deepcopy(vars(model))
    html, doc = call(), tree(call())
    block = chapter_block(doc, data['chapters'][0])
    assert {PREPARE, EXAMPLES, SOURCES} == {n.text.strip() for n in shortcuts(block)}
    assert not [n for n in doc.walk() if n.tag == 'svg' or any(k.startswith('on') for k in n.attrs)]
    assert attack in doc.text and '&lt;svg' in html
    assert data == before_data and vars(model) == before_model
