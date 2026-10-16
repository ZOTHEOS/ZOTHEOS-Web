"""Independent practical-guide contract, authored before its renderer exists.

Fictional data exercises the real renderer. These cases do not certify law,
source truth, external services, Nation approval or real-world outcomes.
"""
import copy
import importlib.util
import json
import os
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
import re
import sys

import pytest


ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
TOOLS = ROOT / 'tools'
sys.path.insert(0, str(TOOLS))


class Node:
    def __init__(self, tag='', attrs=None, parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs or []), parent
        self.children = []

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    @property
    def text(self):
        return ''.join(child.text if isinstance(child, Node) else child for child in self.children)


class Document(HTMLParser):
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.current = self.root
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.current)
        self.current.children.append(node)
        if tag not in self.VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        item = self.current
        while item.parent is not None:
            if item.tag == tag:
                self.current = item.parent
                return
            item = item.parent

    def handle_data(self, data):
        self.current.children.append(data)


def fixture_catalogue():
    return {
        'version': 1,
        'title': 'Paths To Action',
        'intro': ['A fictional practical guide for reader-controlled work.'],
        'capabilities': {
            'now': ['Read public records and follow their own published sources.'],
            'limits': ['This website does not file applications, act as a lawyer or receive private evidence.'],
            'future': ['Possible desktop evidence organization is proposed, not a service available here.']
        },
        'sources': [
            {'id': 'river-source', 'url': 'https://publisher.example.test/river', 'publisher': 'Fictional Publisher',
             'title': 'River Programme', 'reviewed': '2026-10-12', 'as_of': '2018-02-01'},
            {'id': 'culture-source', 'url': 'https://publisher.example.test/culture', 'publisher': 'Fictional Publisher',
             'title': 'Community Language', 'reviewed': '2026-10-13'}
        ],
        'chapters': [
            {'id': 'land-and-water', 'title': 'Land And Water',
             'intro': 'Start with a bounded public question, not an assumed outcome.',
             'steps': [
                 {'title': 'Find The Original', 'text': 'Website-step sentinel: follow the public publisher.',
                  'scope': 'website-now', 'source_ids': ['river-source']},
                 {'title': 'Ask Before Acting', 'text': 'Reader-step sentinel: decide what to ask the authorized institution.',
                  'scope': 'reader-controlled', 'source_ids': ['river-source']},
                 {'title': 'Possible Draft Support', 'text': 'Future-step sentinel: a proposed app could help organize a draft.',
                  'scope': 'future-app', 'source_ids': ['river-source']}
             ],
             'verify': ['Verify the responsible institution and the date of the source.'],
             'deliverable': 'Deliverable sentinel: a one-page question and source list.',
             'reflection': 'Reflection sentinel: whose decision is this?',
             'source_ids': ['river-source'],
             'examples': [{'nation': 'fixture-nation', 'fact_ids': ['fixture-fact-a', 'fixture-fact-b']}]},
            {'id': 'language-and-culture', 'title': 'Language And Culture',
             'intro': 'Community authority decides what may be shared.',
             'steps': [{'title': 'Read The Programme', 'text': 'Culture-step sentinel: read the publisher first.',
                        'scope': 'website-now', 'source_ids': ['culture-source']}],
             'verify': ['A public page is not permission to reuse restricted material.'],
             'deliverable': 'Culture deliverable sentinel: a permission question, not a copied archive.',
             'reflection': 'Culture reflection sentinel: who controls reuse?',
             'source_ids': ['culture-source'], 'examples': []}
        ]
    }


def fixture_model():
    facts = [
        {'id': 'fixture-fact-a', 'text': 'Exact public fact A sentinel.', 'date': '2026-10-08', 'as_of': '2017',
         'url': 'https://nation.example.test/history', 'publisher': 'Fixture Nation', 'title': 'Own History',
         'human': False, 'grace': False, 'note': None, 'kind': 'history'},
        {'id': 'fixture-fact-b', 'text': 'Exact public fact B sentinel.', 'date': '2026-10-09', 'as_of': None,
         'url': 'https://nation.example.test/river', 'publisher': 'Fixture Nation', 'title': 'Own River Work',
         'human': False, 'grace': False, 'note': None, 'kind': 'land'}
    ]
    raw = {'nations': [{'id': 'fixture-nation', 'name': 'Fixture Nation', 'facts': copy.deepcopy(facts)},
                       {'id': 'other-nation', 'name': 'Other Nation', 'facts': [{'id': 'other-fact'}]}]}
    public = {'fixture-nation': {'id': 'fixture-nation', 'name': 'Fixture Nation', 'facts': copy.deepcopy(facts)}}
    return SimpleNamespace(raw=raw, by_id=public, nations=list(public.values()))


@pytest.fixture
def guide(tmp_path):
    path = tmp_path / 'data' / 'nations' / 'pathways.json'
    path.parent.mkdir(parents=True)
    data, model = fixture_catalogue(), fixture_model()

    def call(data_override=None, model_override=None, brief=False):
        source = TOOLS / 'nations_pathways.py'
        if not source.is_file():
            pytest.fail('Practical-guide renderer not implemented yet; expected prebuild RED.')
        path.write_text(json.dumps(data if data_override is None else data_override, ensure_ascii=False), encoding='utf8')
        spec = importlib.util.spec_from_file_location('pathways_under_contract', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        function = getattr(module, 'action_brief' if brief else 'render', None)
        assert callable(function), 'The agreed real renderer / plain-text brief callable is required.'
        return function(str(tmp_path), model if model_override is None else model_override)

    return data, model, call


def tree(text):
    return Document(text).root


def test_substantive_reading_is_open_static_and_has_no_submission_ui(guide):
    data, _, call = guide
    html = call()
    doc = tree(html)
    for chapter in data['chapters']:
        for text in [chapter['intro'], chapter['deliverable'], chapter['reflection'], *chapter['verify']]:
            assert text in doc.text
        for step in chapter['steps']:
            assert step['text'] in doc.text
    assert not [n for n in doc.walk() if n.tag in {'script', 'iframe', 'form', 'input', 'textarea', 'select', 'button', 'video', 'audio'}]
    assert not [n for n in doc.walk() if n.tag == 'details' and any(c['intro'] in n.text for c in data['chapters'])]
    assert not re.search(r'\bon\w+\s*=', html, re.I)


def test_native_chapter_index_has_unique_focusable_heading_targets(guide):
    data, _, call = guide
    doc = tree(call())
    navs = [n for n in doc.walk() if n.tag == 'nav' and any(c['title'] in n.text for c in data['chapters'])]
    assert len(navs) == 1
    ids = [n.attrs['id'] for n in doc.walk() if 'id' in n.attrs]
    assert len(ids) == len(set(ids))
    links = [n for n in navs[0].walk() if n.tag == 'a' and n.attrs.get('href', '').startswith('#')]
    assert len(links) == len(data['chapters'])
    for chapter, link in zip(data['chapters'], links):
        target = [n for n in doc.walk() if n.attrs.get('id') == link.attrs['href'][1:]]
        assert len(target) == 1 and target[0].tag == 'h2'
        assert target[0].attrs.get('tabindex') == '-1'
        assert chapter['title'] in target[0].text


def test_anchors_remain_stable_when_chapter_order_changes(guide):
    data, _, call = guide
    before = tree(call())
    data['chapters'].reverse()
    after = tree(call())
    def anchors(doc):
        return {n.text.strip(): n.attrs['id'] for n in doc.walk() if n.tag == 'h2' and n.attrs.get('tabindex') == '-1'}
    assert anchors(before) == anchors(after)


def test_capability_scopes_are_visible_on_each_step_and_future_is_not_live(guide):
    _, _, call = guide
    doc = tree(call())
    labels = {'Website-step sentinel': ('website', 'now'),
              'Reader-step sentinel': ('you',),
              'Future-step sentinel': ('proposed',)}
    for sentinel, expected in labels.items():
        blocks = [n for n in doc.walk() if n.tag == 'article' and sentinel in n.text]
        assert blocks, 'Each step needs its own scope-bearing reading block.'
        text = min(blocks, key=lambda n: len(n.text)).text.lower()
        assert all(word in text for word in expected)
    assert 'not a service available here' in doc.text
    assert 'does not file applications' in doc.text


def test_source_clocks_are_not_promoted_to_fact_or_event_clocks(guide):
    _, _, call = guide
    doc = tree(call())
    assert any(n.tag == 'time' and n.attrs.get('datetime') == '2026-10-12' for n in doc.walk())
    assert '2018-02-01' in doc.text or any(n.attrs.get('datetime') == '2018-02-01' for n in doc.walk())
    facts = [n for n in doc.walk() if n.tag == 'article' and 'Exact public fact A sentinel.' in n.text]
    assert facts
    smallest = min(facts, key=lambda n: len(n.text))
    assert any(n.tag == 'time' and n.attrs.get('datetime') == '2026-10-08' for n in smallest.walk())
    assert not any(n.tag == 'time' and n.attrs.get('datetime') == '2026-10-12' for n in smallest.walk())
    assert 'checked by a person' not in doc.text.lower()
    assert 'approved by' not in doc.text.lower()


def test_official_source_links_are_explicit_native_and_have_real_receipts(guide):
    data, _, call = guide
    doc = tree(call())
    for source in data['sources']:
        links = [n for n in doc.walk() if n.tag == 'a' and n.attrs.get('href') == source['url']]
        assert links and any(source['title'] in n.text for n in links)
        assert source['publisher'] in doc.text
        assert any(n.tag == 'time' and n.attrs.get('datetime') == source['reviewed'] for n in doc.walk())
        for link in links:
            if link.attrs.get('target') == '_blank':
                assert {'noopener', 'noreferrer'} <= set(link.attrs.get('rel', '').split())


def test_public_example_uses_exact_canonical_name_facts_sources_and_link(guide):
    _, _, call = guide
    doc = tree(call())
    assert 'Fixture Nation' in doc.text
    assert 'Exact public fact A sentinel.' in doc.text and 'Exact public fact B sentinel.' in doc.text
    assert any(n.tag == 'a' and n.attrs.get('href') == '/nations/fixture-nation' for n in doc.walk())
    assert any(n.tag == 'a' and n.attrs.get('href') == 'https://nation.example.test/history' for n in doc.walk())


@pytest.mark.parametrize('hold', ['nation', 'one-fact', 'all-facts'])
def test_any_required_canonical_hold_suppresses_whole_example(guide, hold):
    _, model, call = guide
    if hold == 'nation':
        model.by_id.clear()
    elif hold == 'one-fact':
        model.by_id['fixture-nation']['facts'].pop()
    else:
        model.by_id['fixture-nation']['facts'].clear()
    doc = tree(call())
    assert 'Fixture Nation' not in doc.text
    assert 'Exact public fact A sentinel.' not in doc.text and 'Exact public fact B sentinel.' not in doc.text
    assert '/nations/fixture-nation' not in call()
    assert 'Deliverable sentinel' in doc.text


def test_named_source_hold_suppresses_dependent_chapter_and_navigation(guide):
    data, model, call = guide
    data['sources'][0]['nation'] = 'fixture-nation'
    data['sources'][0]['publisher'] = 'Held publisher sentinel'
    data['chapters'][0]['intro'] = 'Held chapter body sentinel'
    model.by_id.clear()
    html = call()
    for held in ['Held publisher sentinel', 'Held chapter body sentinel', 'River Programme', 'https://publisher.example.test/river', 'Land And Water']:
        assert held not in tree(html).text and held not in html
    assert 'Language And Culture' in tree(html).text


def test_catalogue_prose_and_canonical_names_are_escaped_as_text(guide):
    data, model, call = guide
    attack = '<img src=x onerror=alert(1)> " & <svg/onload=alert(2)>'
    data['title'] = attack
    data['chapters'][0]['title'] = attack
    data['chapters'][0]['deliverable'] = attack
    data['sources'][0]['title'] = attack
    model.by_id['fixture-nation']['name'] = attack
    html = call()
    doc = tree(html)
    assert attack in doc.text
    assert not [n for n in doc.walk() if n.tag in {'img', 'svg'} or any(k.startswith('on') for k in n.attrs)]
    assert '&lt;img' in html


def test_action_brief_is_native_plain_text_and_comes_from_visible_chapters(guide):
    data, _, call = guide
    doc = tree(call())
    links = [n for n in doc.walk() if n.tag == 'a' and n.attrs.get('href') == '/static/nations/action-brief.txt']
    assert len(links) == 1 and 'download' in links[0].attrs
    brief = call(brief=True)
    assert isinstance(brief, str) and '<html' not in brief.lower() and '<script' not in brief.lower()
    for chapter in data['chapters']:
        assert chapter['title'] in brief and chapter['deliverable'] in brief and chapter['reflection'] in brief
    assert re.search(r'_{3,}|\[ \]', brief), 'An offline brief needs blank reader-controlled fields.'


def test_plain_text_brief_cannot_bypass_held_source_or_example(guide):
    data, model, call = guide
    data['sources'][0]['nation'] = 'fixture-nation'
    model.by_id.clear()
    brief = call(brief=True)
    assert 'Land And Water' not in brief and 'River Programme' not in brief
    assert 'Fixture Nation' not in brief and 'Exact public fact' not in brief
    assert 'Language And Culture' in brief


@pytest.mark.parametrize('url', [
    'javascript:alert(1)', 'http://publisher.example.test/', '//publisher.example.test/',
    'data:text/html,unsafe', 'https://user@publisher.example.test/',
    'https://publisher.example.test:0/', 'https://publisher.example.test:/',
    'https://publisher.example.test\\@evil.example.test/', 'https://publisher.example.test/\nsecond',
    'https://publisher.example.test/\x7f', 'https://[broken/'
])
def test_source_urls_fail_closed_before_page_or_brief(guide, url):
    data, _, call = guide
    data['sources'][0]['url'] = url
    with pytest.raises(ValueError):
        call()
    with pytest.raises(ValueError):
        call(brief=True)


@pytest.mark.parametrize('case', [
    'duplicate-chapter', 'unsafe-chapter-id', 'too-many-chapters', 'missing-deliverable',
    'blank-reflection', 'invalid-step-scope', 'duplicate-source', 'unknown-source',
    'future-source-review', 'invalid-calendar-date', 'unknown-source-nation',
    'unknown-example-nation', 'unknown-example-fact', 'wrong-nation-fact', 'empty-example-facts', 'duplicate-example-facts'
])
def test_malformed_catalogue_fails_closed(guide, case):
    data, _, call = guide
    if case == 'duplicate-chapter':
        data['chapters'].append(copy.deepcopy(data['chapters'][0]))
    elif case == 'unsafe-chapter-id':
        data['chapters'][0]['id'] = 'unsafe" onclick="run()'
    elif case == 'too-many-chapters':
        data['chapters'] = [dict(copy.deepcopy(data['chapters'][0]), id='chapter-'+str(i)) for i in range(13)]
    elif case == 'missing-deliverable':
        del data['chapters'][0]['deliverable']
    elif case == 'blank-reflection':
        data['chapters'][0]['reflection'] = '   '
    elif case == 'invalid-step-scope':
        data['chapters'][0]['steps'][0]['scope'] = 'already-completed'
    elif case == 'duplicate-source':
        data['sources'].append(copy.deepcopy(data['sources'][0]))
    elif case == 'unknown-source':
        data['chapters'][0]['source_ids'] = ['unreviewed-source']
    elif case == 'future-source-review':
        data['sources'][0]['reviewed'] = '9999-01-01'
    elif case == 'invalid-calendar-date':
        data['sources'][0]['reviewed'] = '2026-02-30'
    elif case == 'unknown-source-nation':
        data['sources'][0]['nation'] = 'not-canonical'
    elif case == 'unknown-example-nation':
        data['chapters'][0]['examples'][0]['nation'] = 'not-canonical'
    elif case == 'unknown-example-fact':
        data['chapters'][0]['examples'][0]['fact_ids'] = ['not-a-fact']
    elif case == 'wrong-nation-fact':
        data['chapters'][0]['examples'][0]['fact_ids'] = ['other-fact']
    elif case == 'empty-example-facts':
        data['chapters'][0]['examples'][0]['fact_ids'] = []
    elif case == 'duplicate-example-facts':
        data['chapters'][0]['examples'][0]['fact_ids'] = ['fixture-fact-a', 'fixture-fact-a']
    with pytest.raises(ValueError):
        call()


def test_new_support_route_has_native_builder_registration():
    import nations_build as builder
    assert 'paths-to-action' in dict(builder.SUPPORT)
    assert callable(getattr(builder.Builder, 'pathways', None))


def test_existing_public_claim_and_context_boundaries_remain_explicit():
    release = (ROOT/'download.html').read_text(encoding='utf8')
    nations = (ROOT/'tools/nations/templates/for-nations.html').read_text(encoding='utf8')
    assert 'No replacement installer is available from this page yet.' in release
    assert 'not yet advised by an Indigenous advisory circle' in nations
