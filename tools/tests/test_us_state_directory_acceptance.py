"""US directory acceptance: source observations, identity boundaries and publication holds.

Use ZOTHEOS_TEST_REPO for an isolated reviewer run. No network or registry writes.
"""
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import sys

import pytest

ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
import nations_build as B
import nations_directory as D
import nations_fonts as F
import nations_inventories as I
import nations_research as R

CASES = [('us_va_state_directory_2026.json', 'VA', 'us-va-tribal-directory'),
         ('us_nc_state_directory_2026.json', 'NC', 'us-nc-tribal-directory')]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


@pytest.fixture
def isolated(tmp_path):
    folder = tmp_path / 'data/nations/research'
    folder.mkdir(parents=True)
    for name in ['us_federal_directory.json', 'ca_registry_groups_2024.json', 'directory_sources.json',
                 'us_coverage_plan.json', *(c[0] for c in CASES)]:
        shutil.copyfile(ROOT / 'data/nations/research' / name, folder / name)
    optional_al = ROOT / 'data/nations/research/us_al_state_directory_2026.json'
    if optional_al.exists():
        shutil.copyfile(optional_al, folder / optional_al.name)
    shutil.copytree(ROOT / 'data/nations/research/receipts', folder / 'receipts')
    shutil.copyfile(ROOT / 'data/nations/nations.json', tmp_path / 'data/nations/nations.json')
    write(folder / 'coverage_queue.json', {'max_subjects_per_run': 3, 'tasks': []})
    before = (tmp_path / 'data/nations/nations.json').read_bytes()
    yield tmp_path, folder
    assert (tmp_path / 'data/nations/nations.json').read_bytes() == before


def builder(root):
    b = B.Builder(str(ROOT))
    b.root = str(root)
    b.m.root = str(root)
    b.sp = lambda key, body, description: body
    return b


def target(folder, filename):
    path = folder / filename
    doc = read(path)
    return path, doc, doc['entities'][0]


def task(e, sid):
    return {'task_id': 'fixture-profile-' + e['directory_id'], 'task_type': 'entity_profile',
            'subject': 'Fictional acceptance subject', 'entity_id': e['directory_id'],
            'entity_type': e['entity_type'], 'countries': e['countries'], 'region': 'fixture-us',
            'priority': 50, 'status': 'pending', 'allowed_source_ids': [sid],
            'risk': {'status': 'unassessed', 'signals': []}, 'receipts': [], 'next_attempt_after': None}


@pytest.mark.parametrize('filename,state,sid', CASES)
def test_every_state_source_row_is_visible_without_identity_approval(isolated, filename, state, sid):
    root, folder = isolated
    doc = read(folder / filename)
    assert doc['entity_unit'] == 'state_tribal_directory_listing'
    assert doc['snapshot_kind'] == 'source_observation'
    assert doc['as_of'] == dt.datetime.fromisoformat(doc['source']['retrieved_at']).astimezone(dt.timezone.utc).date().isoformat()
    page = D.page(builder(root))
    for e in doc['entities']:
        block = page.split('<li id="' + e['directory_id'] + '"', 1)[1].split('</li>', 1)[0]
        assert B.esc(e['name']) in block
        assert e['registry_crosswalk']['status'] == 'unreviewed'
        assert e['registry_crosswalk']['registry_id'] is None
        assert not re.search(r'href="/nations/[^"#]+"', block)
    assert doc['stated_count'] is None
    assert 'different lists cannot be added together as a count of Indigenous nations' in page
    assert 'not a definition of Indigenous identity' in page


@pytest.mark.parametrize('filename,state,sid', CASES)
@pytest.mark.parametrize('corrupt', ['doc_state', 'row_state', 'country', 'doc_unit', 'row_unit', 'id', 'snapshot_kind'])
def test_state_jurisdiction_and_listing_unit_cannot_be_silently_retyped(isolated, filename, state, sid, corrupt):
    root, folder = isolated
    path, doc, e = target(folder, filename)
    if corrupt == 'doc_state': doc['state'] = 'AK'
    elif corrupt == 'row_state': e['state'] = 'AK'
    elif corrupt == 'country': e['countries'] = ['CA']
    elif corrupt == 'doc_unit': doc['entity_unit'] = 'federally_listed_tribal_entity'
    elif corrupt == 'row_unit': e['entity_type'] = 'federally_listed_tribal_entity'
    elif corrupt == 'id': e['directory_id'] = 'us-fed-123456789abc'
    else: doc['snapshot_kind'] = 'recognition_effective_date'
    write(path, doc)
    with pytest.raises(ValueError): I.documents(root)


@pytest.mark.parametrize('filename,state,sid', CASES)
def test_observation_day_cannot_be_backdated_as_if_it_were_a_legal_date(isolated, filename, state, sid):
    root, folder = isolated
    path, doc, _ = target(folder, filename)
    doc['as_of'] = (dt.date.fromisoformat(doc['as_of']) - dt.timedelta(days=1)).isoformat()
    for e in doc['entities']: e['as_of'] = doc['as_of']
    write(path, doc)
    with pytest.raises(ValueError): I.documents(root)


@pytest.mark.parametrize('filename,state,sid', CASES)
def test_observation_day_uses_utc_instead_of_the_timestamp_local_calendar_day(isolated, filename, state, sid):
    root, folder = isolated
    path, doc, _ = target(folder, filename)
    moment = dt.datetime.fromisoformat(doc['source']['retrieved_at'])
    local = moment.astimezone(dt.timezone(dt.timedelta(hours=-6)))
    assert local.date().isoformat() != doc['as_of'], 'Fixture must span UTC midnight'
    doc['source']['retrieved_at'] = local.isoformat()
    recpath = folder / doc['source']['receipt']
    receipt = read(recpath)
    receipt['retrieved_at'] = local.isoformat()
    write(recpath, receipt)
    write(path, doc)
    assert next(d for d in I.documents(root) if d['state'] == state)['as_of'] == moment.astimezone(dt.timezone.utc).date().isoformat()
    page = D.page(builder(root))
    anchor = 'us-virginia' if state == 'VA' else 'us-north-carolina'
    section = page.split('id="' + anchor + '"', 1)[1].split('</ul></section>', 1)[0]
    assert 'Read ' + D.display_date(doc['as_of']) + ' UTC.' in section
    assert 'Read ' + D.display_date(local.date().isoformat()) + ' UTC.' not in section


@pytest.mark.parametrize('corrupt', ['missing', 'traversal', 'wrong_hash', 'wrong_url', 'undated', 'failed_http'])
def test_state_source_receipt_must_exist_and_support_the_published_observation(isolated, corrupt):
    root, folder = isolated
    path, doc, _ = target(folder, CASES[1][0])
    recpath = folder / doc['source']['receipt']
    rec = read(recpath)
    if corrupt == 'missing': doc['source']['receipt'] = 'receipts/fixture-absent.json'
    elif corrupt == 'traversal': doc['source']['receipt'] = 'receipts/../us_nc_state_directory_2026.json'
    elif corrupt == 'wrong_hash': rec['sha256'] = '0' * 64
    elif corrupt == 'wrong_url': rec['url'] = 'https://different.example.test/'
    elif corrupt == 'undated': rec['retrieved_at'] = rec['retrieved_at'].split('+')[0]
    else: rec['http_status'] = 503
    write(recpath, rec)
    write(path, doc)
    with pytest.raises(ValueError): I.documents(root)


@pytest.mark.parametrize('corrupt', ['unreviewed', 'no_receipt', 'wrong_destination', 'empty_identity_evidence'])
def test_published_own_website_link_requires_matching_reviewed_identity_evidence(isolated, corrupt):
    root, folder = isolated
    path, doc, _ = target(folder, CASES[1][0])
    e = next(e for e in doc['entities'] if e['official_url'])
    if corrupt == 'unreviewed': e['official_url_review']['status'] = 'unreviewed'
    elif corrupt == 'no_receipt': e['official_url_review']['evidence_receipt'] = 'receipts/fixture-absent.json'
    elif corrupt == 'wrong_destination': e['official_url'] = 'https://different.example.test/'
    else:
        e['official_url_review'].pop('evidence', None)
        recpath = folder / e['official_url_review']['evidence_receipt']
        rec = read(recpath)
        rec.pop('evidence_phrase', None)
        write(recpath, rec)
    write(path, doc)
    with pytest.raises(ValueError): I.documents(root)


def test_catawba_source_conflict_stays_visible_without_an_invented_effective_date(isolated):
    root, folder = isolated
    doc = read(folder / CASES[1][0])
    conflict = doc['source_discrepancies'][0]
    assert conflict['status'] == 'unresolved' and conflict['event_date'] is None
    page = D.page(builder(root))
    assert doc['scoped_notes'] and all(B.esc(t['text']) in page for t in doc['scoped_notes'])
    assert 'June 6' in page and 'without giving the year' in page
    assert 'certified nine-tribe state-recognition total' not in page


@pytest.mark.parametrize('filename,state,sid', CASES)
def test_unreviewed_candidates_cannot_gain_a_canonical_link_without_identity_review(isolated, filename, state, sid):
    root, folder = isolated
    path, doc, e = target(folder, filename)
    nid = next(n['id'] for n in read(ROOT / 'data/nations/nations.json')['nations'] if 'US' in n['countries'])
    e['registry_crosswalk']['candidates'] = [{'registry_id': nid, 'basis': 'fixture-name-only'}]
    e['registry_crosswalk']['registry_id'] = nid
    write(path, doc)
    with pytest.raises(ValueError): I.documents(root)


def test_state_directory_holds_remove_names_from_html_fonts_and_research_selection(isolated):
    root, folder = isolated
    tasks, holds, ids, points = [], [], [], set()
    for index, (filename, state, sid) in enumerate(CASES):
        path, doc, e = target(folder, filename)
        chars = [chr(0xE321 + 2 * index), chr(0xE322 + 2 * index)]
        e['name'], e['directory_name'] = 'Fictional ' + chars[0], 'Fictional source ' + chars[1]
        write(path, doc)
        tasks.append(task(e, sid)); ids.append(e['directory_id']); points.update(map(ord, chars))
        holds.append({'directory_id': e['directory_id'], 'action': 'takedown',
                      'requested_at': '2026-10-14T05:00:00Z', 'receipt': 'Fictional removal receipt for acceptance only'})
    b = builder(root)
    assert all('<li id="' + key + '"' in D.page(b) for key in ids)
    assert all(points <= role for role in F.role_sets(b.m))
    write(folder / 'publication_holds.json', {'schema_version': 1, 'entries': holds})
    write(folder / 'coverage_queue.json', {'max_subjects_per_run': 3, 'tasks': tasks})
    before = (folder / 'coverage_queue.json').read_bytes()
    assert all('<li id="' + key + '"' not in D.page(b) for key in ids)
    assert all(not points.intersection(role) for role in F.role_sets(b.m))
    assert R.next_tasks(root, 3, '2026-10-15T05:00:00Z') == []
    for row in tasks:
        with pytest.raises(ValueError, match='publication hold'):
            R.transition(root, row['task_id'], 'claim', '2026-10-15T05:00:00Z')
    assert (folder / 'coverage_queue.json').read_bytes() == before
    assert len(read(folder / CASES[0][0])['entities']) == 11
    assert len(read(folder / CASES[1][0])['entities']) == 9


@pytest.mark.parametrize('corrupt', ['complete', 'missing_state', 'duplicate_state', 'pretend_inventory', 'missing_inclusion_lane'])
def test_us_gap_plan_cannot_claim_complete_or_discard_unresearched_scopes(isolated, corrupt):
    root, folder = isolated
    path = folder / 'us_coverage_plan.json'; plan = read(path)
    if corrupt == 'complete': plan['complete'] = True
    elif corrupt == 'missing_state': plan['state_scopes'].pop()
    elif corrupt == 'duplicate_state': plan['state_scopes'][-1] = dict(plan['state_scopes'][0])
    elif corrupt == 'pretend_inventory':
        next(row for row in plan['state_scopes'] if row['state'] == 'CO').update(status='source_inventory_preserved', inventory_file='us_co_state_directory_2026.json')
    else: plan['additional_lanes'] = [r for r in plan['additional_lanes'] if r['id'] != 'native-hawaiian']
    write(path, plan)
    with pytest.raises(ValueError): D.page(builder(root))