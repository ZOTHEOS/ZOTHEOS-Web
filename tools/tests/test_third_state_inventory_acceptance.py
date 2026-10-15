"""Independent pre-build acceptance for a third state directory.

All Alabama names, receipts and URLs below are fictional test inputs. They do
not assert facts about real communities. No network or published registry writes.
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

FILE = 'us_al_state_directory_2026.json'
SID = 'us-al-tribal-directory'
URL = 'https://al-fixture.example.test/directory/'
REC = 'receipts/al-fictional-source.receipt.json'
STAMP = '2026-10-14T21:20:00-06:00'
DAY = '2026-10-15'
IDS = ['us-state-al-fictional-riverlight-council', 'us-state-al-fictional-riverlight-community']


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


@pytest.fixture
def scenario(tmp_path):
    folder = tmp_path / 'data/nations/research'
    folder.mkdir(parents=True)
    for filename in ('us_federal_directory.json', 'ca_registry_groups_2024.json',
                     'directory_sources.json', 'us_coverage_plan.json',
                     'us_va_state_directory_2026.json', 'us_nc_state_directory_2026.json'):
        shutil.copyfile(ROOT / 'data/nations/research' / filename, folder / filename)
    shutil.copytree(ROOT / 'data/nations/research/receipts', folder / 'receipts')
    registry = tmp_path / 'data/nations/nations.json'
    shutil.copyfile(ROOT / 'data/nations/nations.json', registry)
    source = {'publisher': 'Fictional acceptance publisher', 'title': 'Fictional state directory',
              'url': URL, 'retrieved_at': STAMP, 'sha256': 'b' * 64, 'receipt': REC}
    rows = [{'directory_id': key, 'name': name, 'directory_name': name,
             'entity_type': 'state_tribal_directory_listing', 'countries': ['US'],
             'state': 'AL', 'as_of': DAY, 'official_url': None, 'profile_status': 'directory_only',
             'registry_crosswalk': {'status': 'unreviewed', 'registry_id': None, 'candidates': []}}
            for key, name in zip(IDS, ['Fictional Riverlight Council', 'Fictional Riverlight Community'])]
    doc = {'schema_version': 1, 'source': source, 'entity_unit': 'state_tribal_directory_listing',
           'state': 'AL', 'snapshot_kind': 'source_observation', 'as_of': DAY,
           'stated_count': None, 'enumerated_count': len(rows),
           'scope_note': 'Fictional source listing units, not all Indigenous peoples or a unique Nations total.',
           'extraction_note': 'Fictional fixture. No real source was fetched.',
           'scoped_notes': [{'kind': 'note', 'directory_ids': [IDS[0]],
                             'text': 'Fictional bounded explanation for the first source listing only.'}],
           'entities': rows}
    write(folder / FILE, doc)
    write(folder / REC, {'url': URL, 'final_url': URL, 'http_status': 200,
                        'retrieved_at': STAMP, 'sha256': 'b' * 64, 'fixture_only': True})
    sources = read(folder / 'directory_sources.json')
    sources['sources'] = [row for row in sources['sources'] if row['source_id'] != SID]
    sources['sources'].append({'source_id': SID, 'countries': ['US'],
        'entity_unit': 'state_tribal_directory_listing', 'url': URL,
        'allowed_hosts': ['al-fixture.example.test'], 'stated_count': None, 'as_of': DAY,
        'discovery_date': DAY, 'status': 'source_retrieved', 'note': 'Fictional test allowlist only.'})
    write(folder / 'directory_sources.json', sources)
    plan = read(folder / 'us_coverage_plan.json')
    # This fixture intentionally models the original three-state contract.
    nj = next(row for row in plan['state_scopes'] if row['state'] == 'NJ')
    nj['status'] = 'source_discovery_pending'
    nj.pop('inventory_file', None)
    for state in plan['state_scopes']:
        if state['state'] == 'AL':
            state.update(status='source_inventory_preserved', inventory_file=FILE)
    write(folder / 'us_coverage_plan.json', plan)
    write(folder / 'coverage_queue.json', {'max_subjects_per_run': 3, 'tasks': []})
    before = registry.read_bytes()
    yield tmp_path, folder, doc
    assert registry.read_bytes() == before, 'Directory work cannot rewrite published canonical facts'


def loaded(root):
    docs = [doc for doc in I.documents(root) if doc.get('state') == 'AL']
    assert len(docs) == 1, 'The third state inventory must actually be loaded'
    return docs[0]


def builder(root):
    b = B.Builder(str(ROOT))
    b.root = str(root)
    b.m.root = str(root)
    b.sp = lambda key, body, description: body
    return b


def section(page, doc):
    return page.split('id="' + doc['_display']['anchor'] + '"', 1)[1].split('</ul></section>', 1)[0]


def hold(folder, key):
    write(folder / 'publication_holds.json', {'schema_version': 1, 'entries': [{
        'directory_id': key, 'action': 'takedown', 'requested_at': '2026-10-15T04:00:00Z',
        'receipt': 'Fictional isolated acceptance removal receipt only.'}]})


def task(key):
    return {'task_id': 'fictional-profile-' + key, 'task_type': 'entity_profile',
            'subject': 'Fictional state listing', 'entity_id': key,
            'entity_type': 'state_tribal_directory_listing', 'countries': ['US'],
            'region': 'fixture-us-al', 'priority': 50, 'status': 'pending',
            'allowed_source_ids': [SID], 'risk': {'status': 'unassessed', 'signals': []},
            'receipts': [], 'next_attempt_after': None}


def test_third_state_keeps_both_source_rows_without_guessing_identity(scenario):
    root, folder, doc = scenario
    active = loaded(root)
    page = D.page(builder(root))
    for row in doc['entities']:
        block = page.split('<li id="' + row['directory_id'] + '"', 1)[1].split('</li>', 1)[0]
        assert D.esc(row['name']) in block
        assert 'Profile Link Pending' in block
        assert not re.search(r'href="/nations/[^"#]+"', block)
    assert active['enumerated_count'] == 2 and active['stated_count'] is None
    assert 'different lists cannot be added together as a count of Indigenous nations' in page


def test_third_state_navigation_is_named_alabama_not_a_north_carolina_fallback(scenario):
    root, folder, _ = scenario
    doc = loaded(root)
    page = D.page(builder(root))
    link = re.search(r'<a href="#' + re.escape(doc['_display']['anchor']) + r'">(.*?)</a>', page, re.S).group(1)
    option = re.search(r'<option value="' + re.escape(doc['_display']['anchor']) + r'">(.*?)</option>', page, re.S).group(1)
    assert 'Alabama' in link and 'Alabama' in option
    assert 'North Carolina' not in link and 'North Carolina' not in option
    assert '2 records' in link


def test_source_observation_uses_utc_day_and_never_claims_a_legal_effective_date(scenario):
    root, folder, doc = scenario
    active = loaded(root)
    assert dt.datetime.fromisoformat(STAMP).date().isoformat() != DAY
    assert active['as_of'] == DAY
    rendered = section(D.page(builder(root)), active)
    assert 'Read ' + D.display_date(DAY) + ' UTC.' in rendered
    assert 'Read 14 Oct 2026 UTC.' not in rendered
    assert active['snapshot_kind'] == 'source_observation'


@pytest.mark.parametrize('corrupt', ['document_state', 'row_state', 'row_country', 'document_unit',
                                    'row_unit', 'prefix', 'snapshot_kind', 'wrong_utc_day'])
def test_third_state_scope_cannot_be_silently_retyped(scenario, corrupt):
    root, folder, doc = scenario
    loaded(root)
    if corrupt == 'document_state': doc['state'] = 'NC'
    elif corrupt == 'row_state': doc['entities'][0]['state'] = 'NC'
    elif corrupt == 'row_country': doc['entities'][0]['countries'] = ['CA']
    elif corrupt == 'document_unit': doc['entity_unit'] = 'federally_listed_tribal_entity'
    elif corrupt == 'row_unit': doc['entities'][0]['entity_type'] = 'federally_listed_tribal_entity'
    elif corrupt == 'prefix': doc['entities'][0]['directory_id'] = 'us-state-nc-fictional-riverlight'
    elif corrupt == 'snapshot_kind': doc['snapshot_kind'] = 'recognition_effective_date'
    else:
        doc['as_of'] = '2026-10-14'
        for row in doc['entities']: row['as_of'] = doc['as_of']
    write(folder / FILE, doc)
    with pytest.raises(ValueError): I.documents(root)


def test_directory_hold_suppresses_alabama_name_scoped_note_font_and_queue_together(scenario):
    root, folder, doc = scenario
    loaded(root)
    point = 0xE472
    doc['entities'][0]['name'] += chr(point)
    doc['entities'][0]['directory_name'] += chr(point)
    doc['scoped_notes'][0]['text'] += chr(point)
    write(folder / FILE, doc)
    write(folder / 'coverage_queue.json', {'max_subjects_per_run': 3, 'tasks': [task(key) for key in IDS]})
    b = builder(root)
    assert chr(point) in D.page(b)
    assert all(point in role for role in F.role_sets(b.m))
    hold(folder, IDS[0])
    page = D.page(b)
    assert '<li id="' + IDS[0] + '"' not in page
    assert chr(point) not in page
    assert D.esc(doc['scoped_notes'][0]['text']) not in page
    assert '<li id="' + IDS[1] + '"' in page
    assert all(point not in role for role in F.role_sets(b.m))
    assert R.validate(root) == []
    assert [row['entity_id'] for row in R.next_tasks(root, 3, '2026-10-15T05:00:00Z')] == [IDS[1]]
    before_queue = (folder / 'coverage_queue.json').read_bytes()
    with pytest.raises(ValueError, match='publication hold'):
        R.transition(root, task(IDS[0])['task_id'], 'claim', '2026-10-15T05:00:00Z')
    assert (folder / 'coverage_queue.json').read_bytes() == before_queue
    assert len(read(folder / FILE)['entities']) == 2


def test_third_state_remains_optional_but_cannot_be_claimed_preserved_without_data(scenario):
    root, folder, _ = scenario
    loaded(root)
    (folder / FILE).unlink()
    with pytest.raises(ValueError, match='inventory'): D.page(builder(root))
    plan = read(folder / 'us_coverage_plan.json')
    row = next(row for row in plan['state_scopes'] if row['state'] == 'AL')
    row.update(status='source_discovery_pending')
    row.pop('inventory_file')
    write(folder / 'us_coverage_plan.json', plan)
    assert not any(doc.get('state') == 'AL' for doc in I.documents(root))
    assert '48 other state source-discovery scopes remain pending' in D.page(builder(root))


def test_three_state_sources_still_leave_47_state_discovery_scopes_and_all_four_inclusion_lanes(scenario):
    root, folder, _ = scenario
    loaded(root)
    page = D.page(builder(root))
    plan = read(folder / 'us_coverage_plan.json')
    assert plan['complete'] is False and len(plan['state_scopes']) == 50
    assert '47 other state source-discovery scopes remain pending' in page
    for lane in plan['additional_lanes']:
        assert lane['status'] == 'pending'
        assert D.esc(lane['title']) in page
    assert 'not how many nations exist or a percentage of US coverage' in page


def test_third_state_source_needs_its_matching_receipt_and_allowlisted_host(scenario):
    root, folder, doc = scenario
    loaded(root)
    sources = read(folder / 'directory_sources.json')
    next(row for row in sources['sources'] if row['source_id'] == SID)['allowed_hosts'] = ['wrong.example.test']
    write(folder / 'directory_sources.json', sources)
    assert any('exact host allowlist' in error for error in R.validate(root))
    receipt = read(folder / REC)
    receipt['sha256'] = 'c' * 64
    write(folder / REC, receipt)
    with pytest.raises(ValueError, match='measured evidence receipt'): I.documents(root)


def test_third_state_candidate_cannot_become_an_approved_profile_link(scenario):
    root, folder, doc = scenario
    loaded(root)
    nid = next(row['id'] for row in read(ROOT / 'data/nations/nations.json')['nations'] if 'US' in row['countries'])
    row = doc['entities'][0]
    row['registry_crosswalk']['candidates'] = [{'registry_id': nid, 'basis': 'fictional-name-only'}]
    write(folder / FILE, doc)
    page = D.page(builder(root))
    block = page.split('<li id="' + row['directory_id'] + '"', 1)[1].split('</li>', 1)[0]
    assert '/nations/' + nid not in block
    row['registry_crosswalk']['registry_id'] = nid
    write(folder / FILE, doc)
    with pytest.raises(ValueError, match='Unreviewed'): I.documents(root)


def test_unregistered_state_hold_does_not_gain_permission_from_the_third_inventory(scenario):
    root, folder, _ = scenario
    loaded(root)
    hold(folder, 'us-state-zz-fictional-unsupported')
    with pytest.raises(ValueError): I.directory_holds(root)


def test_name_search_is_reachable_before_the_long_coverage_and_inventory_sections():
    page = D.page(builder(ROOT))
    search = page.index('id="directoryTools"')
    assert search < page.index('id="us-inclusion"')
    assert search < page.index('class="directory-inventory-nav"')
    assert re.search(r'<div\b[^>]*\bid="directoryTools"[^>]*\bhidden(?:[ >])', page)
    for key in ('directoryInventory', 'directoryQuery'):
        assert 'for="' + key + '"' in page and 'id="' + key + '"' in page
    assert 'id="directoryClear"' in page
    assert 'id="directoryResult"' in page and 'aria-live="polite"' in page
    assert 'id="directoryNames"' in page and 'aria-controls="directoryNames"' in page
    assert '<noscript>' in page and 'All names remain visible without JavaScript' in page
    expected = D.load(ROOT)[0]['entities'] + D.load_canada(ROOT)['entities']
    expected += [row for doc in I.documents(ROOT) for row in doc['entities']]
    visible = D.visible_entries(builder(ROOT), expected)
    assert all('<li id="' + row['directory_id'] + '"' in page for row in visible)


def test_actual_alabama_named_federal_marker_explanation_follows_its_subject_hold(scenario):
    root, folder, _ = scenario
    actual = read(ROOT / 'data/nations/research' / FILE)
    marked = [row for row in actual['entities'] if row.get('source_federal_marker')]
    assert len(marked) == 1
    subject = marked[0]
    notes = [note for note in actual.get('scoped_notes', [])
             if subject['directory_id'] in note['directory_ids']]
    assert notes, 'The actual named marker explanation must be explicitly bound to its source subject'
    write(folder / FILE, actual)
    doc = loaded(root)
    before = section(D.page(builder(root)), doc)
    assert all(D.esc(note['text']) in before for note in notes)
    hold(folder, subject['directory_id'])
    after = section(D.page(builder(root)), doc)
    assert '<li id="' + subject['directory_id'] + '"' not in after
    assert all(D.esc(note['text']) not in after for note in notes)
    assert subject['name'].split()[0].casefold() not in after.casefold()
    assert all('<li id="' + row['directory_id'] + '"' in after
               for row in actual['entities'] if row['directory_id'] != subject['directory_id'])
