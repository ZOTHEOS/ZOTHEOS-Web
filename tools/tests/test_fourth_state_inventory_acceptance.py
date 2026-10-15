"""Independent pre-build acceptance for a fourth US source inventory.

Every NJ name, URL, digest and receipt in these fixtures is invented. These
tests check publication boundaries, not facts or legal status of real Nations.
No network, Web checkout mutation, identity approval or human receipt occurs.
"""
import datetime as dt
import hashlib
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

FILE = 'us_nj_state_directory_2026.json'
SID = 'us-nj-tribal-directory'
URL = 'https://nj-fictional.example.test/names/'
REC = 'receipts/nj-fictional-source.receipt.json'
STAMP = '2026-10-14T23:31:12-06:00'
DAY = '2026-10-15'
IDS = ['us-state-nj-fictional-harbor-people', 'us-state-nj-fictional-harbor-council']
NOTE = 'Fictional Harbor People source notation applies only to its bound row.'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


@pytest.fixture
def scenario(tmp_path):
    folder = tmp_path / 'data/nations/research'
    folder.mkdir(parents=True)
    for name in ['us_federal_directory.json', 'ca_registry_groups_2024.json',
                 'directory_sources.json', 'us_coverage_plan.json',
                 'us_al_state_directory_2026.json', 'us_va_state_directory_2026.json',
                 'us_nc_state_directory_2026.json']:
        shutil.copyfile(ROOT / 'data/nations/research' / name, folder / name)
    shutil.copytree(ROOT / 'data/nations/research/receipts', folder / 'receipts')
    registry = tmp_path / 'data/nations/nations.json'
    shutil.copyfile(ROOT / 'data/nations/nations.json', registry)
    before = hashlib.sha256(registry.read_bytes()).hexdigest()
    rows = [{'directory_id': key, 'name': name, 'directory_name': name,
             'entity_type': 'state_tribal_directory_listing', 'countries': ['US'],
             'state': 'NJ', 'as_of': DAY, 'official_url': None,
             'profile_status': 'directory_only',
             'registry_crosswalk': {'status': 'unreviewed', 'registry_id': None, 'candidates': []}}
            for key, name in zip(IDS, ['Fictional Harbor People', 'Fictional Harbor Council'])]
    doc = {'schema_version': 1, 'source': {'publisher': 'Fictional acceptance publisher',
            'title': 'Fictional fourth state name source', 'url': URL,
            'retrieved_at': STAMP, 'sha256': 'a' * 64, 'receipt': REC},
           'state': 'NJ', 'entity_unit': 'state_tribal_directory_listing',
           'snapshot_kind': 'source_observation', 'as_of': DAY,
           'stated_count': None, 'enumerated_count': 2,
           'scope_note': 'Source rows, not all Indigenous peoples or a unique Nations total.',
           'extraction_note': 'Invented isolated fixture. No real source fetched.',
           'scoped_notes': [{'kind': 'note', 'directory_ids': [IDS[0]], 'text': NOTE}],
           'entities': rows}
    write(folder / FILE, doc)
    write(folder / REC, {'url': URL, 'final_url': URL, 'http_status': 200,
                        'retrieved_at': STAMP, 'sha256': 'a' * 64, 'fixture_only': True})
    sources = read(folder / 'directory_sources.json')
    sources['sources'] = [s for s in sources['sources'] if s['source_id'] != SID]
    sources['sources'].append({'source_id': SID, 'countries': ['US'], 'url': URL,
        'entity_unit': 'state_tribal_directory_listing', 'allowed_hosts': ['nj-fictional.example.test'],
        'stated_count': None, 'as_of': DAY, 'discovery_date': DAY,
        'status': 'source_retrieved', 'note': 'Fictional fixture only.'})
    write(folder / 'directory_sources.json', sources)
    plan = read(folder / 'us_coverage_plan.json')
    nj = next(row for row in plan['state_scopes'] if row['state'] == 'NJ')
    nj.update(status='source_inventory_preserved', inventory_file=FILE)
    write(folder / 'us_coverage_plan.json', plan)
    write(folder / 'coverage_queue.json', {'max_subjects_per_run': 3, 'tasks': []})
    yield tmp_path, folder, doc
    assert hashlib.sha256(registry.read_bytes()).hexdigest() == before


def active(root):
    found = [doc for doc in I.documents(root) if doc.get('state') == 'NJ']
    assert len(found) == 1, 'Fourth typed source must load exactly once, not be silently ignored'
    return found[0]


def builder(root):
    b = B.Builder(str(ROOT))
    b.root = str(root)
    b.m.root = str(root)
    b.sp = lambda key, body, description: body
    return b


def hold(folder, key):
    write(folder / 'publication_holds.json', {'schema_version': 1, 'entries': [{
        'directory_id': key, 'action': 'takedown', 'requested_at': '2026-10-15T14:00:18Z',
        'receipt': 'Fictional removal receipt. Not a request from any real Nation.'}]})


def task(key):
    return {'task_id': 'fictional-review-' + key, 'task_type': 'entity_profile',
            'subject': 'Fictional source listing', 'entity_id': key,
            'entity_type': 'state_tribal_directory_listing', 'countries': ['US'],
            'region': 'fixture-us-nj', 'priority': 50, 'status': 'pending',
            'allowed_source_ids': [SID], 'risk': {'status': 'unassessed', 'signals': []},
            'receipts': [], 'next_attempt_after': None}


def test_fourth_source_is_named_new_jersey_in_navigation_picker_and_heading(scenario):
    root, folder, _ = scenario
    doc = active(root)
    page = D.page(builder(root))
    anchor = doc['_display']['anchor']
    assert anchor == 'us-new-jersey'
    navigation = re.search(r'<a href="#' + re.escape(anchor) + r'">(.*?)</a>', page, re.S).group(1)
    option = re.search(r'<option value="' + re.escape(anchor) + r'">(.*?)</option>', page, re.S).group(1)
    assert 'New Jersey' in navigation and 'New Jersey' in option
    assert '2 records' in navigation
    section = page.split('id="' + anchor + '"', 1)[1].split('</ul></section>', 1)[0]
    assert 'New Jersey' in section and 'North Carolina' not in navigation


def test_source_rows_remain_separate_unlinked_and_unreviewed(scenario):
    root, folder, doc = scenario
    active(root)
    page = D.page(builder(root))
    for row in doc['entities']:
        block = page.split('<li id="' + row['directory_id'] + '"', 1)[1].split('</li>', 1)[0]
        assert D.esc(row['name']) in block and 'Profile Link Pending' in block
        assert not re.search(r'href="/nations/[^"#]+"', block)
        assert row['registry_crosswalk'] == {'status': 'unreviewed', 'registry_id': None, 'candidates': []}
    assert 'different lists cannot be added together as a count of Indigenous nations' in page


def test_four_state_sources_leave_46_pending_scopes_and_every_extra_inclusion_lane(scenario):
    root, folder, _ = scenario
    active(root)
    page = D.page(builder(root))
    plan = read(folder / 'us_coverage_plan.json')
    assert plan['complete'] is False and len(plan['state_scopes']) == 50
    assert '46 other state source-discovery scopes remain pending' in page
    assert {lane['id'] for lane in plan['additional_lanes']} == {
        'outside-recognition', 'native-hawaiian', 'alaska-communities', 'borders-and-territories'}
    for lane in plan['additional_lanes']:
        assert lane['status'] == 'pending' and D.esc(lane['title']) in page
    assert 'not how many nations exist or a percentage of US coverage' in page


def test_observation_uses_actual_utc_day_without_becoming_a_recognition_date(scenario):
    root, folder, doc = scenario
    active(root)
    assert dt.datetime.fromisoformat(STAMP).date().isoformat() != DAY
    assert dt.datetime.fromisoformat(STAMP).astimezone(dt.timezone.utc).date().isoformat() == DAY
    page = D.page(builder(root))
    section = page.split('id="us-new-jersey"', 1)[1].split('</ul></section>', 1)[0]
    assert 'Read 15 Oct 2026 UTC.' in section and 'Read 14 Oct 2026 UTC.' not in section
    assert doc['snapshot_kind'] == 'source_observation' and doc['stated_count'] is None


@pytest.mark.parametrize('bad', ['document_state', 'row_state', 'country', 'document_unit',
    'row_unit', 'id_prefix', 'legal_date', 'local_day'])
def test_jurisdiction_unit_and_observation_scope_cannot_be_retyped(scenario, bad):
    root, folder, doc = scenario
    active(root)
    if bad == 'document_state': doc['state'] = 'NY'
    elif bad == 'row_state': doc['entities'][0]['state'] = 'NY'
    elif bad == 'country': doc['entities'][0]['countries'] = ['CA']
    elif bad == 'document_unit': doc['entity_unit'] = 'federally_listed_tribal_entity'
    elif bad == 'row_unit': doc['entities'][0]['entity_type'] = 'federally_listed_tribal_entity'
    elif bad == 'id_prefix': doc['entities'][0]['directory_id'] = 'us-state-ny-fictional-other'
    elif bad == 'legal_date': doc['snapshot_kind'] = 'recognition_effective_date'
    else:
        doc['as_of'] = '2026-10-14'
        for row in doc['entities']: row['as_of'] = doc['as_of']
    write(folder / FILE, doc)
    with pytest.raises(ValueError): I.documents(root)


@pytest.mark.parametrize('bad', ['missing', 'traversal', 'wrong_hash', 'wrong_url', 'undated', 'http_failure'])
def test_fourth_source_needs_measured_matching_bounded_receipt(scenario, bad):
    root, folder, doc = scenario
    active(root)
    receipt = read(folder / REC)
    if bad == 'missing': doc['source']['receipt'] = 'receipts/missing.json'
    elif bad == 'traversal': doc['source']['receipt'] = 'receipts/../' + FILE
    elif bad == 'wrong_hash': receipt['sha256'] = 'b' * 64
    elif bad == 'wrong_url': receipt['url'] = 'https://wrong.example.test/'
    elif bad == 'undated': receipt['retrieved_at'] = '2026-10-15T05:31:12'
    else: receipt['http_status'] = 503
    write(folder / REC, receipt)
    write(folder / FILE, doc)
    with pytest.raises(ValueError): I.documents(root)


def test_source_host_allowlist_does_not_expand_implicitly(scenario):
    root, folder, _ = scenario
    active(root)
    sources = read(folder / 'directory_sources.json')
    next(s for s in sources['sources'] if s['source_id'] == SID)['allowed_hosts'] = ['other.example.test']
    write(folder / 'directory_sources.json', sources)
    assert any('exact host allowlist' in error for error in R.validate(root))


def test_name_similarity_never_approves_profile_identity(scenario):
    root, folder, doc = scenario
    active(root)
    nid = next(n['id'] for n in read(ROOT / 'data/nations/nations.json')['nations'] if 'US' in n['countries'])
    row = doc['entities'][0]
    row['registry_crosswalk']['candidates'] = [{'registry_id': nid, 'basis': 'fictional name similarity'}]
    write(folder / FILE, doc)
    page = D.page(builder(root))
    block = page.split('<li id="' + IDS[0] + '"', 1)[1].split('</li>', 1)[0]
    assert '/nations/' + nid not in block
    row['registry_crosswalk']['registry_id'] = nid
    write(folder / FILE, doc)
    with pytest.raises(ValueError, match='Unreviewed'): I.documents(root)


def test_takedown_removes_bound_name_note_font_and_queue_claim_without_deleting_source(scenario):
    root, folder, doc = scenario
    active(root)
    point = 0xE47B
    doc['entities'][0]['name'] += chr(point)
    doc['entities'][0]['directory_name'] += chr(point)
    doc['scoped_notes'][0]['text'] += chr(point)
    write(folder / FILE, doc)
    write(folder / 'coverage_queue.json', {'max_subjects_per_run': 3, 'tasks': [task(key) for key in IDS]})
    b = builder(root)
    assert chr(point) in D.page(b) and all(point in role for role in F.role_sets(b.m))
    hold(folder, IDS[0])
    page = D.page(b)
    assert '<li id="' + IDS[0] + '"' not in page
    assert '<li id="' + IDS[1] + '"' in page
    assert NOTE not in page and chr(point) not in page
    assert all(point not in role for role in F.role_sets(b.m))
    assert R.validate(root) == []
    assert [t['entity_id'] for t in R.next_tasks(root, 3, '2026-10-15T15:00:00Z')] == [IDS[1]]
    before = (folder / 'coverage_queue.json').read_bytes()
    with pytest.raises(ValueError, match='publication hold'):
        R.transition(root, task(IDS[0])['task_id'], 'claim', '2026-10-15T15:00:00Z')
    assert (folder / 'coverage_queue.json').read_bytes() == before
    assert len(read(folder / FILE)['entities']) == 2


def test_scoped_named_note_cannot_bind_an_absent_or_duplicate_subject(scenario):
    root, folder, doc = scenario
    active(root)
    for keys in ([IDS[0], IDS[0]], ['us-state-nj-fictional-absent']):
        doc['scoped_notes'][0]['directory_ids'] = keys
        write(folder / FILE, doc)
        with pytest.raises(ValueError, match='bindings'): I.documents(root)


def test_fourth_inventory_is_optional_but_plan_cannot_pretend_missing_data_exists(scenario):
    root, folder, _ = scenario
    active(root)
    (folder / FILE).unlink()
    with pytest.raises(ValueError, match='inventory'): D.page(builder(root))
    plan = read(folder / 'us_coverage_plan.json')
    row = next(row for row in plan['state_scopes'] if row['state'] == 'NJ')
    row.update(status='source_discovery_pending')
    row.pop('inventory_file')
    write(folder / 'us_coverage_plan.json', plan)
    assert not any(doc.get('state') == 'NJ' for doc in I.documents(root))
    assert '47 other state source-discovery scopes remain pending' in D.page(builder(root))


def test_fourth_inventory_does_not_authorize_a_fifth_state_hold_namespace(scenario):
    root, folder, _ = scenario
    active(root)
    hold(folder, 'us-state-zz-fictional-unsupported')
    with pytest.raises(ValueError): I.directory_holds(root)
