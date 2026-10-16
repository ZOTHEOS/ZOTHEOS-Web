"""Supplemental adversarial controls, kept separate from the immutable43-case proof.

Written while implementation was in progress; not relabeled as the original
prebuild evidence. Uses only fictional fixtures and the actual renderer.
"""
import copy

import pytest

from test_indigenous_pathways import guide, tree


def test_step_reference_cannot_silently_name_an_unreviewed_source(guide):
    data, _, call = guide
    data['chapters'][0]['steps'][0]['source_ids'] = ['unreviewed-source']
    with pytest.raises(ValueError):
        call()


def test_step_only_named_source_hold_propagates_to_whole_chapter_and_brief(guide):
    data, model, call = guide
    data['sources'][1]['nation'] = 'fixture-nation'
    data['chapters'][0]['steps'][0]['source_ids'] = ['culture-source']
    data['chapters'][0]['intro'] = 'Step-linked held chapter sentinel'
    model.by_id.clear()
    html = call()
    brief = call(brief=True)
    assert 'Step-linked held chapter sentinel' not in html and 'Land And Water' not in html
    assert 'Land And Water' not in brief
    assert 'Community Language' not in html and 'Community Language' not in brief


def test_hidden_chapters_do_not_bypass_validation_of_other_references(guide):
    data, model, call = guide
    data['sources'][0]['nation'] = 'fixture-nation'
    data['chapters'][0]['steps'][0]['source_ids'] = ['unreviewed-source']
    model.by_id.clear()
    with pytest.raises(ValueError):
        call()


@pytest.mark.parametrize('url', [
    'https:///missing-host', 'https://publisher.example.test:65536/',
    'https://publisher.example.test/\x00hidden', 'https://publisher.example.test/\tstripped'
])
def test_additional_url_parser_ambiguities_fail_closed(guide, url):
    data, _, call = guide
    data['sources'][0]['url'] = url
    with pytest.raises(ValueError):
        call()


def test_public_example_never_substitutes_raw_name_or_raw_fact_text(guide):
    _, model, call = guide
    model.raw['nations'][0]['name'] = 'PRIVATE RAW NAME SENTINEL'
    model.raw['nations'][0]['facts'][0]['text'] = 'PRIVATE RAW FACT SENTINEL'
    html = call()
    assert 'Fixture Nation' in tree(html).text and 'Exact public fact A sentinel.' in tree(html).text
    assert 'PRIVATE RAW' not in html


def test_retained_fact_grace_discloses_failed_attempt_without_resetting_check(guide):
    _, model, call = guide
    fact = model.by_id['fixture-nation']['facts'][0]
    fact.update(date='2026-10-08', grace=True, note='2026-10-15')
    doc = tree(call())
    blocks = [n for n in doc.walk() if n.tag == 'article' and fact['text'] in n.text]
    block = min(blocks, key=lambda n: len(n.text))
    dates = [n.attrs.get('datetime') for n in block.walk() if n.tag == 'time']
    assert '2026-10-08' in dates and '2026-10-15' in dates
    assert any(term in block.text.lower() for term in ['could not reach', 'failed', 'unreachable'])


def test_genuine_person_check_is_attributed_only_to_its_selected_fact(guide):
    _, model, call = guide
    model.by_id['fixture-nation']['facts'][0]['human'] = True
    reading = tree(call()).text
    first_receipt = reading.split('Exact public fact A sentinel.', 1)[1].split('Exact public fact B sentinel.', 1)[0]
    second_receipt = reading.split('Exact public fact B sentinel.', 1)[1]
    assert 'checked by a person' in first_receipt.lower()
    assert 'checked by a person' not in second_receipt.lower()


@pytest.mark.parametrize('case', ['chapter-ref', 'step-ref', 'step-scope', 'source-nation', 'example-nation'])
def test_unhashable_json_values_are_rejected_as_catalogue_errors(guide, case):
    data, _, call = guide
    if case == 'chapter-ref':
        data['chapters'][0]['source_ids'] = [['river-source']]
    elif case == 'step-ref':
        data['chapters'][0]['steps'][0]['source_ids'] = [{}]
    elif case == 'step-scope':
        data['chapters'][0]['steps'][0]['scope'] = []
    elif case == 'source-nation':
        data['sources'][0]['nation'] = []
    else:
        data['chapters'][0]['examples'][0]['nation'] = []
    with pytest.raises(ValueError):
        call()


def test_render_and_download_do_not_mutate_canonical_data_or_catalogue(guide):
    data, model, call = guide
    original_data = copy.deepcopy(data)
    original_model = copy.deepcopy(vars(model))
    call()
    call(brief=True)
    assert data == original_data
    assert vars(model) == original_model
