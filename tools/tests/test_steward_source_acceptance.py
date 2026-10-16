"""Independent pre-build acceptance for bounded supporting source evidence.

Run against the proposed repo with ZOTHEOS_TEST_REPO. Fixtures are fictional,
use local temporary data, and never create published facts or human receipts.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
import nations_build as B
import nations_directory as D
import nations_inventories as I

NC = 'us_nc_state_directory_2026.json'
SUBJECT = 'us-state-nc-catawba-nation'
URL = 'https://www.doa.nc.gov/fictional-source-acceptance.pdf'
REC = 'receipts/fictional-supporting-source.receipt.json'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


@pytest.fixture
def scenario(tmp_path):
    folder = tmp_path / 'data/nations/research'
    folder.mkdir(parents=True)
    for filename in ('us_federal_directory.json', 'ca_registry_groups_2024.json',
                     'directory_sources.json', 'us_coverage_plan.json', NC,
                     'us_va_state_directory_2026.json'):
        shutil.copyfile(ROOT / 'data/nations/research' / filename, folder / filename)
    for filename, _, unit, *_ in I.INVENTORIES:
        optional = ROOT / 'data/nations/research' / filename
        if unit == 'state_tribal_directory_listing' and optional.exists():
            shutil.copyfile(optional, folder / optional.name)
    shutil.copytree(ROOT / 'data/nations/research/receipts', folder / 'receipts')
    doc = read(folder / NC)
    source = {'label': 'Fictional supporting source', 'url': URL, 'receipt': REC, 'pages': [1, 5, 7, 19]}
    doc['source_discrepancies'][0]['supporting_sources'] = [source]
    receipt = {'url': URL, 'final_url': URL, 'http_status': 200,
               'retrieved_at': '2026-10-15T07:00:00Z', 'sha256': 'a' * 64,
               'fixture_only': True}
    write(folder / REC, receipt)
    write(folder / NC, doc)
    return tmp_path, folder, doc, source, receipt


def page(root):
    b = B.Builder(str(ROOT))
    b.root = str(root)
    b.m.root = str(root)
    b.sp = lambda key, body, description: body
    return D.page(b)


def test_supporting_evidence_is_rendered_and_bound_to_the_subject(scenario):
    root, folder, doc, source, receipt = scenario
    before = page(root)
    assert URL in before and source['label'] in before
    write(folder / 'publication_holds.json', {'schema_version': 1, 'entries': [{
        'directory_id': SUBJECT, 'action': 'takedown',
        'requested_at': '2026-10-15T07:00:00Z',
        'receipt': 'Fictional removal for acceptance only'}]})
    after = page(root)
    assert URL not in after
    assert source['label'] not in after
    assert '<li id="' + SUBJECT + '"' not in after
    assert 'us-state-nc-coharie-tribe' in after
    assert doc['enumerated_count'] == 9


@pytest.mark.parametrize('corrupt', ['missing_receipt', 'traversal', 'bad_hash', 'failed_http',
                                    'missing_timezone', 'wrong_receipt_url', 'wrong_final_url',
                                    'unsafe_url', 'empty_label', 'too_many_sources'])
def test_invalid_supporting_evidence_cannot_enter_public_directory(scenario, corrupt):
    root, folder, doc, source, receipt = scenario
    if corrupt == 'missing_receipt': source['receipt'] = 'receipts/absent-acceptance.json'
    elif corrupt == 'traversal': source['receipt'] = 'receipts/../' + NC
    elif corrupt == 'bad_hash': receipt['sha256'] = 'not-a-measured-hash'
    elif corrupt == 'failed_http': receipt['http_status'] = 404
    elif corrupt == 'missing_timezone': receipt['retrieved_at'] = '2026-10-15T07:00:00'
    elif corrupt == 'wrong_receipt_url': receipt['url'] = 'https://different.example.test/source.pdf'
    elif corrupt == 'wrong_final_url': receipt['final_url'] = 'https://different.example.test/source.pdf'
    elif corrupt == 'unsafe_url': source['url'] = 'javascript:alert(1)'
    elif corrupt == 'empty_label': source['label'] = ' '
    else: doc['source_discrepancies'][0]['supporting_sources'] = [copy.deepcopy(source) for _ in range(9)]
    write(folder / REC, receipt)
    write(folder / NC, doc)
    with pytest.raises(ValueError):
        I.documents(root)


@pytest.mark.parametrize('bad_pages', [[0], [-1], [True], ['seven'], list(range(1, 34))])
def test_evidence_page_references_are_bounded_positive_integers(scenario, bad_pages):
    root, folder, doc, source, receipt = scenario
    source['pages'] = bad_pages
    write(folder / NC, doc)
    with pytest.raises(ValueError):
        I.documents(root)


def test_source_labels_cannot_become_executable_markup(scenario):
    root, folder, doc, source, receipt = scenario
    source['label'] = '<script>fictionalBad()</script> & source'
    write(folder / NC, doc)
    rendered = page(root)
    assert '<script>fictionalBad()' not in rendered
    assert '&lt;script&gt;fictionalBad()&lt;/script&gt;' in rendered
    assert URL in rendered


def test_new_evidence_does_not_rewrite_the_old_observation_or_invent_legal_day():
    doc = read(ROOT / 'data/nations/research' / NC)
    discrepancy = next(d for d in doc['source_discrepancies'] if d['subject_directory_id'] == SUBJECT)
    assert doc['as_of'] == '2026-10-14'
    assert all(e['as_of'] == '2026-10-14' for e in doc['entities'])
    assert doc['source']['retrieved_at'].startswith('2026-10-14T')
    assert doc['enumerated_count'] == 9 and doc['stated_count'] is None
    assert discrepancy['status'] == 'unresolved' and discrepancy['event_date'] is None
    assert discrepancy['event_month'] == '2026-06'
    assert discrepancy['minutes_meeting_date'] == '2026-06-05'
    assert discrepancy['displayed_month_day'] == 'June 6'
    # The source dispute must not approve Catawba identity; other identities may pass separate review.
    subjects = [e for e in doc['entities'] if e['directory_id'] == SUBJECT]
    assert len(subjects) == 1
    assert subjects[0]['registry_crosswalk']['status'] == 'unreviewed'
    assert subjects[0]['registry_crosswalk']['registry_id'] is None
