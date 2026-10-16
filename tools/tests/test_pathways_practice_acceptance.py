"""Independent optional-practice acceptance, fixed before renderer changes.

Tests the actual project renderer with fictional public records. This does not
certify source truth, Nation approval, released services or actual outcomes.
"""
import copy
import os
from pathlib import Path
import sys

import pytest

REPO = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(REPO / 'tools' / 'tests'))
from test_indigenous_pathways import guide, tree  # noqa: E402,F401


PRACTICE = {
    'question': 'Planning question sentinel: which public authority should I ask?',
    'steps': ['Planning first sentinel: preserve the exact public page and its date.',
              'Planning second sentinel: write a bounded question for the decision maker.'],
    'boundary': 'Planning boundary sentinel: this is a hypothetical aid, not an application or permission.',
    'reflection': 'Planning reflection sentinel: whose authorization would this require?'
}


def add_practice(data):
    data['chapters'][0]['examples'][0]['practice'] = copy.deepcopy(PRACTICE)
    return data['chapters'][0]['examples'][0]['practice']


def blocks(doc):
    return [n for n in doc.walk() if n.tag in {'article', 'section', 'aside', 'div'}]


def practice_block(doc):
    candidates = [n for n in blocks(doc) if all(value in n.text for value in
                  [PRACTICE['question'], *PRACTICE['steps'], PRACTICE['boundary'], PRACTICE['reflection']])]
    assert candidates, 'The real renderer must display every optional practice field.'
    return min(candidates, key=lambda n: len(n.text))


def test_optional_practice_is_open_labelled_hypothetical_and_separate_from_facts(guide):
    data, _, call = guide
    add_practice(data)
    doc = tree(call())
    practice = practice_block(doc)
    assert 'Try This With The Evidence' in practice.text
    assert 'hypothetical' in practice.text.lower() and 'planning' in practice.text.lower()
    assert 'Exact public fact A sentinel.' not in practice.text
    assert 'Exact public fact B sentinel.' not in practice.text
    assert not any(n.tag == 'details' and PRACTICE['question'] in n.text for n in doc.walk())
    example = min([n for n in blocks(doc) if PRACTICE['question'] in n.text and 'Exact public fact A sentinel.' in n.text], key=lambda n: len(n.text))
    assert example.text.index('Exact public fact B sentinel.') < example.text.index(PRACTICE['question'])
    for value in [PRACTICE['question'], *PRACTICE['steps'], PRACTICE['boundary'], PRACTICE['reflection']]:
        assert example.text.count(value) == 1


def test_legacy_example_without_practice_still_renders(guide):
    _, _, call = guide
    doc = tree(call())
    assert 'Fixture Nation' in doc.text
    assert 'Exact public fact A sentinel.' in doc.text
    assert any(n.tag == 'a' and n.attrs.get('href') == '/nations/fixture-nation' for n in doc.walk())


@pytest.mark.parametrize('hold', ['nation', 'one-fact', 'all-facts', 'chapter-source'])
def test_every_required_hold_suppresses_practice_and_example_links(guide, hold):
    data, model, call = guide
    add_practice(data)
    if hold == 'nation':
        model.by_id.clear()
    elif hold == 'one-fact':
        model.by_id['fixture-nation']['facts'].pop()
    elif hold == 'all-facts':
        model.by_id['fixture-nation']['facts'].clear()
    else:
        data['sources'][0]['nation'] = 'fixture-nation'
        model.by_id.clear()
    html = call()
    for value in [PRACTICE['question'], *PRACTICE['steps'], PRACTICE['boundary'], PRACTICE['reflection'],
                  'Fixture Nation', 'Exact public fact A sentinel.', 'Exact public fact B sentinel.',
                  '/nations/fixture-nation', 'https://nation.example.test/history', 'https://nation.example.test/river']:
        assert value not in html and value not in tree(html).text
    brief = call(brief=True)
    assert 'Fixture Nation' not in brief and PRACTICE['question'] not in brief


def test_only_public_canonical_name_is_used_and_practice_cannot_replace_receipts(guide):
    data, model, call = guide
    add_practice(data)
    model.raw['nations'][0]['name'] = 'RAW NAME MUST STAY PRIVATE'
    model.by_id['fixture-nation']['name'] = 'Public canonical name sentinel'
    doc = tree(call())
    assert 'Public canonical name sentinel' in doc.text
    assert 'RAW NAME MUST STAY PRIVATE' not in doc.text
    for fact in model.by_id['fixture-nation']['facts']:
        node = min([n for n in blocks(doc) if fact['text'] in n.text], key=lambda n: len(n.text))
        assert PRACTICE['question'] not in node.text
        assert any(n.tag == 'a' and n.attrs.get('href') == fact['url'] for n in node.walk())
        assert fact['title'] in node.text and fact['publisher'] in node.text
        assert any(n.tag == 'time' and n.attrs.get('datetime') == fact['date'] for n in node.walk())
        assert not any(n.tag == 'time' and n.attrs.get('datetime') == '2026-10-12' for n in node.walk())
    assert '2017' in doc.text


@pytest.mark.parametrize('human,grace,note', [(False, False, None), (True, False, None), (True, True, '2026-10-10')])
def test_receipt_clocks_and_person_or_grace_status_are_preserved(guide, human, grace, note):
    data, model, call = guide
    add_practice(data)
    fact = model.by_id['fixture-nation']['facts'][0]
    fact.update(human=human, grace=grace, note=note)
    doc = tree(call())
    node = min([n for n in blocks(doc) if fact['text'] in n.text], key=lambda n: len(n.text))
    dates = [n.attrs.get('datetime') for n in node.walk() if n.tag == 'time']
    assert '2026-10-08' in dates
    assert ('checked by a person on' in node.text.lower()) is human
    assert ('could not reach the page on' in node.text.lower()) is grace
    assert ('2026-10-10' in dates) is grace
    assert '2026-10-12' not in dates


def test_all_practice_strings_are_escaped_and_do_not_add_browser_capabilities(guide):
    data, _, call = guide
    practice = add_practice(data)
    attack = '<img src=x onerror=alert(1)> " & <svg/onload=alert(2)>'
    for key in ('question', 'boundary', 'reflection'):
        practice[key] = attack + key
    practice['steps'] = [attack + 'step']
    html = call()
    doc = tree(html)
    for key in ('question', 'boundary', 'reflection'):
        assert attack + key in doc.text
    assert attack + 'step' in doc.text
    assert '&lt;img' in html
    assert not [n for n in doc.walk() if n.tag in {'img', 'svg', 'script', 'iframe', 'form', 'input', 'textarea', 'select', 'button', 'video', 'audio'}
                or any(key.lower().startswith('on') for key in n.attrs)]
    assert not [n for n in doc.walk() if n.tag == 'a' and n.attrs.get('href') == 'x']


INVALID = [
    ('container-null', None), ('container-list', []), ('container-bool', True), ('container-str', 'practice'),
    ('missing-question', 'missing'), ('missing-steps', 'missing'), ('missing-boundary', 'missing'), ('missing-reflection', 'missing'),
    ('extra-field', 'extra'),
    *[(key + '-' + name, value) for key in ('question', 'boundary', 'reflection') for name, value in
      [('null', None), ('bool', True), ('integer', 3), ('array', ['text']), ('mapping', {'text': 'x'}),
       ('blank', '  '), ('oversized', 'x' * 2001), ('control', 'text\x00bad')]],
    ('steps-null', None), ('steps-str', 'one'), ('steps-mapping', {'one': 'two'}), ('steps-empty', []),
    ('steps-oversized', ['step'] * 9), ('steps-bad-item', [True]), ('steps-blank-item', [' ']),
    ('steps-long-item', ['x' * 2001]), ('steps-control-item', ['text\x00bad'])
]


@pytest.mark.parametrize('case,value', INVALID, ids=[case for case, _ in INVALID])
@pytest.mark.parametrize('held', [False, True], ids=['visible', 'held'])
def test_strict_bounded_validation_happens_before_holds_and_for_plain_brief(guide, case, value, held):
    data, model, call = guide
    practice = add_practice(data)
    if case.startswith('container-'):
        data['chapters'][0]['examples'][0]['practice'] = value
    elif case.startswith('missing-'):
        del practice[case.removeprefix('missing-')]
    elif case == 'extra-field':
        practice['unexpected'] = 'Do not silently accept unvalidated metadata.'
    else:
        practice[case.split('-', 1)[0]] = value
    if held:
        data['sources'][0]['nation'] = 'fixture-nation'
        model.by_id.clear()
    for brief in (False, True):
        with pytest.raises(ValueError):
            call(brief=brief)


def test_blank_native_action_brief_remains_shared_and_reader_controlled(guide):
    data, _, call = guide
    add_practice(data)
    doc = tree(call())
    links = [n for n in doc.walk() if n.tag == 'a' and n.attrs.get('href') == '/static/nations/action-brief.txt']
    assert links and all('download' in n.attrs for n in links)
    brief = call(brief=True)
    assert 'Question or need: ____________________' in brief
    assert 'Next step I choose: ____________________' in brief
    assert '<html' not in brief.lower() and '<script' not in brief.lower()
