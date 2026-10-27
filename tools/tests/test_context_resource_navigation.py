"""Preimplementation contract for the conditional publisher-resource shortcut.

Reuses the original fictional history-navigation fixtures. Saved prechange output
proves that ineligible records stay byte-exact and that body/source copy survives.
No browser geometry or historical meaning is certified by these parser tests.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

import pytest

sys.dont_write_bytecode = True
R = Path(os.environ.get('ZOTHEOS_TEST_REPO', str(Path(__file__).resolve().parents[2])))
_spec = importlib.util.spec_from_file_location(
    'original_history_resource_fixture_helpers', R / 'tools/tests/test_history_reading_navigation.py')
H = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(H)

HISTORY_LABEL = 'In This History'
CONTEXT_LABEL = 'In This Context'
RESOURCE_LABEL = 'Publisher Resources'
RESOURCE_HEADING = "From the publisher's own pages"
RESOURCE_ID = 'nResources'
THIRD_TITLE = 'FICTIONAL: A Third Guided Layer'


def case_data(name):
    doc, allow = H.data()
    if name == 'legacy':
        for note in doc['public_notes']:
            del note['reading_id']
    elif name == 'one-explicit':
        del doc['public_notes'][1]['reading_id']
    elif name == 'one-note-held':
        doc['public_notes'][0]['fact_ids'] = ['alpha-held']
    elif name == 'one-resource-held':
        doc['official_resources'][0]['fact_ids'] = ['alpha-held']
    elif name == 'all-notes-held':
        for note in doc['public_notes']:
            note['fact_ids'] = ['alpha-held']
    elif name in {'all-resources-held', 'no-resources'}:
        # Keep the two layers independently visible; their list has no resources.
        for note in doc['public_notes']:
            del note['source_urls']
        if name == 'all-resources-held':
            for resource in doc['official_resources']:
                resource['fact_ids'] = ['alpha-held']
        else:
            doc['official_resources'] = []
    elif name == 'all-cited-resources-held':
        for resource in doc['official_resources']:
            resource['fact_ids'] = ['alpha-held']
    elif name in {'three-guided', 'third-survives-first-resource-hold'}:
        doc['public_notes'].append({
            'nation': 'test-alpha', 'reading_id': 'third-layer', 'title': THIRD_TITLE,
            'text': 'A third fictional layer, preserving the same public source.',
            'source_urls': [H.URL2]})
        if name == 'third-survives-first-resource-hold':
            doc['official_resources'][0]['fact_ids'] = ['alpha-held']
    else:
        assert name == 'base-guided'
    return doc, allow


def render_case(tmp_path, name):
    doc, allow = case_data(name)
    return H.render(tmp_path, doc, allow)


def saved_outputs():
    return json.loads(Path(__file__).with_name(
        'resource-navigation-prechange-goldens.json').read_text(encoding='utf8'))['outputs']


def reading_navs(dom):
    return [n for n in dom.nodes() if n.tag == 'nav' and
            n.attrs.get('aria-label') in {HISTORY_LABEL, CONTEXT_LABEL}]


def nodes_with_id(dom, ident):
    return [n for n in dom.nodes() if n.attrs.get('id') == ident]


def resource_links(dom):
    return [n for n in dom.nodes() if n.tag == 'a' and
            n.attrs.get('href') == '#' + RESOURCE_ID]


def assert_no_resource_jump(markup):
    dom = H.DOM(markup)
    assert not resource_links(dom), 'No resource link may survive an ineligible guide/list.'
    assert not nodes_with_id(dom, RESOURCE_ID), 'Do not mint an orphan resource target.'
    assert not [n for n in reading_navs(dom) if n.attrs['aria-label'] == CONTEXT_LABEL]
    return dom


@pytest.mark.parametrize('case,history_links', [
    ('base-guided', [(H.SCHOOL, '#nHistory-schools'), (H.RIVER, '#nHistory-river-work')]),
    ('three-guided', [(H.SCHOOL, '#nHistory-schools'), (H.RIVER, '#nHistory-river-work'),
                      (THIRD_TITLE, '#nHistory-third-layer')]),
    ('third-survives-first-resource-hold', [(H.RIVER, '#nHistory-river-work'),
                                           (THIRD_TITLE, '#nHistory-third-layer')]),
])
def test_two_or_more_visible_layers_append_one_resolvable_focusable_resource_jump(
        tmp_path, case, history_links):
    page = render_case(tmp_path, case)
    dom = H.DOM(page)
    navs = reading_navs(dom)
    assert len(navs) == 1
    nav = navs[0]
    assert nav.attrs['aria-label'] == CONTEXT_LABEL
    assert 'nation-reading' in nav.attrs.get('class', '').split()
    assert 'hidden' not in nav.attrs and nav.attrs.get('aria-hidden') != 'true'
    labels = [n.text() for n in nav.nodes() if n.tag == 'p' and
              'lbl' in n.attrs.get('class', '').split()]
    assert labels == [CONTEXT_LABEL]
    links = [n for n in nav.nodes() if n.tag == 'a']
    assert [(n.text(), n.attrs.get('href')) for n in links] == history_links + [
        (RESOURCE_LABEL, '#' + RESOURCE_ID)]
    assert len(resource_links(dom)) == 1
    all_ids = [n.attrs['id'] for n in dom.nodes() if 'id' in n.attrs]
    assert len(all_ids) == len(set(all_ids))
    for link in links:
        assert link.attrs['href'].startswith('#')
        assert not any(key.startswith('on') for key in link.attrs)
        assert 'hidden' not in link.attrs and link.attrs.get('aria-hidden') != 'true'
        assert 'target' not in link.attrs and 'download' not in link.attrs
        targets = nodes_with_id(dom, link.attrs['href'][1:])
        assert len(targets) == 1
        target = targets[0]
        assert target.tag == 'h3' and target.attrs.get('tabindex') == '-1'
        assert target.text() == (RESOURCE_HEADING if link.attrs['href'] == '#' + RESOURCE_ID
                                 else link.text())
    assert dom.nodes().index(nav) < dom.nodes().index(nodes_with_id(dom, RESOURCE_ID)[0])


@pytest.mark.parametrize('case', [
    'legacy', 'one-explicit', 'one-note-held', 'one-resource-held',
    'all-notes-held', 'all-resources-held', 'no-resources', 'all-cited-resources-held',
])
def test_ineligible_records_keep_prechange_markup_byte_for_byte(tmp_path, case):
    page = render_case(tmp_path, case)
    assert page == saved_outputs()[case]
    assert_no_resource_jump(page)


@pytest.mark.parametrize('case', ['all-resources-held', 'no-resources'])
def test_two_independent_layers_without_visible_resources_keep_history_only_guide(tmp_path, case):
    page = render_case(tmp_path, case)
    dom = assert_no_resource_jump(page)
    navs = reading_navs(dom)
    assert len(navs) == 1 and navs[0].attrs['aria-label'] == HISTORY_LABEL
    assert [(n.text(), n.attrs.get('href')) for n in navs[0].nodes() if n.tag == 'a'] == [
        (H.SCHOOL, '#nHistory-schools'), (H.RIVER, '#nHistory-river-work')]
    assert not [n for n in dom.nodes() if n.tag == 'h3' and n.text() == RESOURCE_HEADING]


@pytest.mark.parametrize('case', ['one-note-held', 'one-resource-held'])
def test_one_surviving_layer_and_resource_do_not_leave_a_redundant_or_orphan_jump(tmp_path, case):
    page = render_case(tmp_path, case)
    dom = assert_no_resource_jump(page)
    assert not reading_navs(dom)
    assert nodes_with_id(dom, 'nHistory-river-work')[0].attrs.get('tabindex') == '-1'
    assert H.BODY1 not in page and H.BODY2 in page


def test_all_cited_resource_holds_suppress_their_layers_and_empty_context(tmp_path):
    page = render_case(tmp_path, 'all-cited-resources-held')
    assert page == ''
    assert_no_resource_jump(page)


def content_after_navigation(markup):
    content = markup[markup.index('</nav>') + len('</nav>'):]

    def remove_only_resource_target(match):
        tag = match.group(0)
        if re.search(r'\bid=["\']nResources["\']', tag):
            tag = re.sub(r'\s+id=["\']nResources["\']', '', tag)
            tag = re.sub(r'\s+tabindex=["\']-1["\']', '', tag)
        return tag

    return re.sub(r'<h3\b[^>]*>', remove_only_resource_target, content)


def test_shortcut_preserves_entire_existing_reading_body_urls_and_review_dates(tmp_path):
    page = render_case(tmp_path, 'base-guided')
    before = saved_outputs()['base-guided']
    assert content_after_navigation(page) == content_after_navigation(before)
    dom = H.DOM(page)
    external = [n.attrs['href'] for n in dom.nodes() if n.tag == 'a' and
                not n.attrs.get('href', '').startswith('#')]
    assert external == [H.URL1, H.URL2, H.URL1, H.URL2]
    dates = [n.attrs.get('datetime') for n in dom.nodes() if n.tag == 'time']
    assert dates == [H.DAY, '2026-10-08', H.DAY, '2026-10-09', '2026-10-08', '2026-10-09']
    assert page.count(H.BODY1) == page.count(H.BODY2) == 1
    assert page.count('Sources For This Layer') == 2
    assert all(n.tag not in {'script', 'iframe', 'img', 'video', 'audio', 'form', 'button', 'input'}
               for n in dom.nodes())
    assert not re.search(r'localStorage|sessionStorage|fetch\(|XMLHttpRequest|history\.', page)


def test_resource_target_does_not_reuse_a_layer_identity_named_resources(tmp_path):
    doc, allow = H.data()
    doc['public_notes'][0]['reading_id'] = 'resources'
    page = H.render(tmp_path, doc, allow)
    dom = H.DOM(page)
    assert len(nodes_with_id(dom, 'nHistory-resources')) == 1
    assert nodes_with_id(dom, 'nHistory-resources')[0].text() == H.SCHOOL
    targets = nodes_with_id(dom, RESOURCE_ID)
    assert len(targets) == 1 and targets[0].text() == RESOURCE_HEADING
    assert len(resource_links(dom)) == 1
