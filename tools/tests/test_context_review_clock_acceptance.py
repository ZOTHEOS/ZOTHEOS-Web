"""Independent acceptance for context and canonical fact clocks.

Names, statements and links are fictional isolated inputs, never research
receipts. The UTC validation day is measured at test execution, not invented.
"""
import copy
import datetime as dt
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
from nations_context import Context

TODAY = dt.datetime.now(dt.timezone.utc).date()
OLD = (TODAY - dt.timedelta(days=3)).isoformat()
URL = 'https://fictional-own-source.example.test/history/'


@pytest.fixture
def scenario(tmp_path):
    folder = tmp_path / 'data/nations'
    sources = folder / 'sources'
    sources.mkdir(parents=True)
    fact = {'id': 'fictional-source-fact', 'text': 'Fictional existing canonical fact',
            'checked': OLD, 'last_verified': OLD}
    alpha = {'id': 'fictional-alpha', 'name': 'Fictional Alpha', 'facts': [fact]}
    beta = {'id': 'fictional-beta', 'name': 'Fictional Beta', 'facts': []}
    raw_alpha = copy.deepcopy(alpha)
    raw_alpha['facts'].append({'id': 'fictional-held-fact', 'checked': OLD, 'last_verified': OLD})
    m = SimpleNamespace(build_date=OLD, nations=[alpha, beta],
        by_id={alpha['id']: alpha, beta['id']: beta},
        raw={'generated': OLD, 'nations': [raw_alpha, copy.deepcopy(beta),
             {'id': 'fictional-removed', 'name': 'Fictional Removed', 'facts': []}]})
    doc = {'reviewed': TODAY.isoformat(),
        'public_notes': [{'nation': 'fictional-alpha', 'text': 'Fictional reviewed source context.'}],
        'official_resources': [{'nation': 'fictional-alpha', 'label': 'Fictional own history',
            'url': URL, 'purpose': 'An invented bounded source link for acceptance only.'}],
        'relationships': [{'from': 'fictional-alpha', 'to': ['fictional-beta', 'fictional-removed'],
            'relationship': 'Distinct fictional records, not aliases'}]}
    catalog = {'version': 1, 'links': [{'nation': 'fictional-alpha', 'url': URL,
        'publisher': 'Fictional Alpha', 'reviewed': TODAY.isoformat()}]}
    return tmp_path, sources, m, doc, catalog


def save(scenario):
    root, sources, m, doc, catalog = scenario
    (sources / 'fixture.context.json').write_text(json.dumps(doc), encoding='utf-8')
    (sources.parent / 'context_links.json').write_text(json.dumps(catalog), encoding='utf-8')
    return Context(root, m)


def test_context_can_be_reviewed_today_without_rewriting_canonical_fact_or_generated_dates(scenario):
    root, sources, m, doc, catalog = scenario
    before = copy.deepcopy(m.__dict__)
    page = save(scenario).page('fictional-alpha')
    assert 'Fictional reviewed source context.' in page
    assert 'datetime="' + TODAY.isoformat() + '"' in page
    assert 'with AI assistance' in page and 'separate from the fact checks' in page
    assert 'human verified' not in page.lower()
    assert m.__dict__ == before
    assert m.build_date == OLD and m.raw['generated'] == OLD
    assert m.by_id['fictional-alpha']['facts'][0]['checked'] == OLD
    assert m.by_id['fictional-alpha']['facts'][0]['last_verified'] == OLD


@pytest.mark.parametrize('where', ['document', 'link'])
@pytest.mark.parametrize('bad', ['future_utc_day', 'invalid_calendar', 'non_iso', 'timestamp_not_day'])
def test_actual_future_or_invalid_context_review_dates_still_fail(scenario, where, bad):
    root, sources, m, doc, catalog = scenario
    # Keep the other independent context clock old so the failing assertion
    # cannot be satisfied accidentally by the legacy canonical clock ceiling.
    doc['reviewed'] = OLD
    catalog['links'][0]['reviewed'] = OLD
    value = {'future_utc_day': (TODAY + dt.timedelta(days=1)).isoformat(),
             'invalid_calendar': '2026-02-30', 'non_iso': 'today',
             'timestamp_not_day': TODAY.isoformat() + 'T00:00:00Z'}[bad]
    if where == 'document': doc['reviewed'] = value
    else: catalog['links'][0]['reviewed'] = value
    with pytest.raises(ValueError): save(scenario)


@pytest.mark.parametrize('change', ['path', 'nation'])
def test_new_review_day_does_not_relax_exact_nation_and_url_allowlist(scenario, change):
    root, sources, m, doc, catalog = scenario
    if change == 'path': doc['official_resources'][0]['url'] = URL + '?other=1'
    else: doc['official_resources'][0]['nation'] = 'fictional-beta'
    with pytest.raises(ValueError, match='exact nation/link allowlist'): save(scenario)


def test_new_review_day_does_not_resurrect_removed_nation_or_held_fact_context(scenario):
    root, sources, m, doc, catalog = scenario
    doc['public_notes'][0]['fact_ids'] = ['fictional-held-fact']
    doc['official_resources'][0]['fact_ids'] = ['fictional-held-fact']
    doc['public_notes'].append({'nation': 'fictional-removed', 'text': 'FICTIONAL REMOVED TEXT'})
    c = save(scenario)
    page = c.page('fictional-alpha')
    assert 'Fictional reviewed source context.' not in page and URL not in page
    assert 'FICTIONAL REMOVED TEXT' not in page and 'fictional-removed' not in page
    assert c.page('fictional-removed') == ''
    assert 'Fictional Beta' in page


def test_new_review_day_does_not_accept_unknown_fact_references(scenario):
    root, sources, m, doc, catalog = scenario
    doc['public_notes'][0]['fact_ids'] = ['fictional-not-in-registry']
    with pytest.raises(ValueError, match='unknown fact reference'): save(scenario)
