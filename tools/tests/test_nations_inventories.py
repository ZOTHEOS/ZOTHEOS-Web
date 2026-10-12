"""Acceptance boundaries for independently typed Canada/Brazil name catalogues.

Portable in tools/tests; isolated runs may set ZOTHEOS_TEST_REPO and
ZOTHEOS_INVENTORY_FIXTURES. No network or published-registry writes.
"""
import copy
import json
import os
from pathlib import Path
import re
import shutil
import sys

import pytest

ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
CATALOGUES = Path(os.environ.get('ZOTHEOS_INVENTORY_FIXTURES', ROOT / 'data/nations/research'))
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
import nations_build as B
import nations_directory as D
import nations_fonts as F
import nations_inventories as I
import nations_research as R

CA = 'ca_fn_profiles_2026.json'
BR = 'br_census_groups_2022.json'
CASES = [(CA, 'CA', 'ca-profile-', 'ca-first-nation-profiles'),
         (BR, 'BR', 'br-census-', 'br-ibge-census-2022')]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')


@pytest.fixture
def editable(tmp_path):
    """Copy only JSON contracts, never source bodies, headers or session fields."""
    folder = tmp_path / 'data/nations/research'
    folder.mkdir(parents=True)
    for name in ['us_federal_directory.json', 'ca_registry_groups_2024.json', 'directory_sources.json']:
        shutil.copyfile(ROOT / 'data/nations/research' / name, folder / name)
    for name in [CA, BR]:
        shutil.copyfile(CATALOGUES / name, folder / name)
    registry = tmp_path / 'data/nations/nations.json'
    shutil.copyfile(ROOT / 'data/nations/nations.json', registry)
    write(folder / 'coverage_queue.json', {'max_subjects_per_run': 3, 'tasks': []})
    before = registry.read_bytes()
    yield tmp_path, folder
    assert registry.read_bytes() == before, 'Research tests must never change published facts'


def builder(root):
    b = B.Builder(str(ROOT))
    b.root = str(root)
    b.m.root = str(root)
    b.sp = lambda key, body, description: body
    return b


def entry(folder, filename):
    path = folder / filename
    doc = read(path)
    return path, doc, doc['entities'][0]


def known_id(country):
    return next(n['id'] for n in read(ROOT / 'data/nations/nations.json')['nations'] if country in n['countries'])


def task_for(e, source_id):
    return {'task_id': 'fixture-profile-' + e['directory_id'], 'task_type': 'entity_profile',
            'subject': 'Fictional acceptance task', 'entity_id': e['directory_id'],
            'entity_type': e['entity_type'], 'countries': e['countries'], 'region': 'fixture-region',
            'priority': 50, 'status': 'pending', 'allowed_source_ids': [source_id],
            'risk': {'status': 'unassessed', 'signals': []}, 'receipts': [], 'next_attempt_after': None}


def test_exact_source_records_keep_separate_public_units_and_unresolved_counts(editable):
    root, folder = editable
    docs = I.documents(root)
    assert {d['entity_unit']: d['enumerated_count'] for d in docs} == {
        'first_nation_profile': 638, 'census_ethnicity_people_or_group': 391}
    page = D.page(builder(root))
    for doc, (_, country, prefix, _) in zip(docs, CASES):
        ids = re.findall(r'<li id="(' + prefix + r'[a-z0-9-]+)"', page)
        assert len(ids) == len(set(ids)) == doc['enumerated_count']
        assert set(ids) == {e['directory_id'] for e in doc['entities']}
        for e in doc['entities']:
            assert B.esc(e['directory_name']) in page
        assert B.esc(doc['scope_note']) in page
    ca = docs[0]
    assert ca['stated_count'] == 619 and ca['count_discrepancy']['status'] == 'unresolved'
    assert B.esc(ca['count_discrepancy']['note']) in page
    assert '638 source records' in page and '619' in page
    assert '634' in page and 'December 31, 2024' in page
    assert 'different lists cannot be added together as a count of Indigenous nations' in page


@pytest.mark.parametrize('filename,country,prefix,sid', CASES)
@pytest.mark.parametrize('wrong', ['document_unit', 'record_unit', 'country'])
def test_wrong_unit_or_country_fails_before_any_public_render(editable, filename, country, prefix, sid, wrong):
    root, folder = editable
    path, doc, e = entry(folder, filename)
    if wrong == 'document_unit':
        doc['entity_unit'] = 'federally_listed_tribal_entity'
    elif wrong == 'record_unit':
        e['entity_type'] = 'indian_register_group'
    else:
        e['countries'] = ['US']
    write(path, doc)
    with pytest.raises(ValueError):
        D.page(builder(root))


@pytest.mark.parametrize('change', ['missing_discrepancy', 'claimed_resolved', 'empty_note'])
def test_619_638_difference_cannot_be_silently_resolved(editable, change):
    root, folder = editable
    path, doc, _ = entry(folder, CA)
    if change == 'missing_discrepancy':
        doc.pop('count_discrepancy')
    elif change == 'claimed_resolved':
        doc['count_discrepancy']['status'] = 'resolved'
    else:
        doc['count_discrepancy']['note'] = ''
    write(path, doc)
    with pytest.raises(ValueError, match='discrepancy'):
        I.documents(root)


@pytest.mark.parametrize('filename,country,prefix,sid', CASES)
def test_unknown_confirmed_profile_fails_in_page_and_queue(editable, filename, country, prefix, sid):
    root, folder = editable
    path, doc, e = entry(folder, filename)
    e['registry_crosswalk'].update(status='confirmed', registry_id='fixture-absent-profile',
                                  reviewer='Fictional AI-assisted source review', evidence_receipt='fixture-only')
    write(path, doc)
    with pytest.raises(ValueError, match='unknown profile'):
        D.page(builder(root))
    assert any('existing registry id' in error for error in R.validate(root))


@pytest.mark.parametrize('filename,country,prefix,sid', CASES)
def test_candidates_and_source_profile_urls_do_not_create_approved_links(editable, filename, country, prefix, sid):
    root, folder = editable
    path, doc, e = entry(folder, filename)
    nid = known_id(country)
    e['registry_crosswalk']['candidates'] = [{'registry_id': nid, 'basis': 'fixture-name-only'}]
    e['source_profile_url'] = 'https://source.example.test/profile'
    write(path, doc)
    page = D.page(builder(root))
    block = page.split('<li id="' + e['directory_id'] + '"', 1)[1].split('</li>', 1)[0]
    assert '/nations/' + nid not in block and e['source_profile_url'] not in block
    e['registry_crosswalk']['registry_id'] = nid
    write(path, doc)
    with pytest.raises(ValueError, match='Unreviewed'):
        I.documents(root)


@pytest.mark.parametrize('filename,country,prefix,sid', CASES)
def test_unreviewed_official_website_is_rejected(editable, filename, country, prefix, sid):
    root, folder = editable
    path, doc, e = entry(folder, filename)
    e['official_url'] = 'https://nation.example.test/'
    write(path, doc)
    with pytest.raises(ValueError, match='separate source review'):
        I.documents(root)


@pytest.mark.parametrize('filename,country,prefix,sid', CASES)
@pytest.mark.parametrize('hold', ['hide_nation', 'takedown'])
def test_confirmed_removal_holds_filter_page_and_all_font_roles(editable, filename, country, prefix, sid, hold):
    root, folder = editable
    path, doc, e = entry(folder, filename)
    nid = known_id(country)
    # Fictional, exclusive codepoints make a leaked directory string observable.
    e['name'], e['directory_name'] = 'Fixture \ue111', 'Fixture source \ue112'
    e['registry_crosswalk'].update(status='confirmed', registry_id=nid,
                                  reviewer='Fictional AI-assisted source review', evidence_receipt='fixture-only')
    write(path, doc)
    b = builder(root)
    assert '<li id="' + e['directory_id'] + '"' in D.page(b)
    roles = F.role_sets(b.m)
    assert all({0xE111, 0xE112} <= role for role in roles)
    b.m.overrides[hold].append({'nation': nid})
    b.m._apply()
    b.decide()
    page = D.page(b)
    assert '<li id="' + e['directory_id'] + '"' not in page
    assert '/nations/' + nid not in page
    assert all(not {0xE111, 0xE112}.intersection(role) for role in F.role_sets(b.m))


@pytest.mark.parametrize('filename,country,prefix,sid', CASES)
def test_typed_task_claim_and_identity_reconciliation_preserve_unit(editable, filename, country, prefix, sid):
    root, folder = editable
    path, doc, e = entry(folder, filename)
    task = task_for(e, sid)
    write(folder / 'coverage_queue.json', {'max_subjects_per_run': 3, 'tasks': [task]})
    assert R.validate(root) == []
    claimed = R.transition(root, task['task_id'], 'claim', '2026-10-12T10:00:00Z')
    assert claimed['status'] == 'researching' and claimed['entity_type'] == e['entity_type']
    # Reset only the fictional queue so reconciliation can examine a name candidate.
    nid = known_id(country)
    e['registry_crosswalk']['candidates'] = [{'registry_id': nid, 'basis': 'fixture-name-only'}]
    write(path, doc)
    write(folder / 'coverage_queue.json', {'max_subjects_per_run': 3, 'tasks': [task]})
    result = R.reconcile(root, '2026-10-12T10:00:00Z')
    assert result['new_identity_tasks'] == ['identity-' + e['directory_id']]
    queued = read(folder / 'coverage_queue.json')['tasks']
    assert queued[0]['status'] == 'needs_review' and queued[0]['profile_disposition'] == 'identity_crosswalk_first'
    assert queued[1]['entity_type'] == e['entity_type'] and queued[1]['countries'] == [country]
    identity = R.transition(root, queued[1]['task_id'], 'claim', '2026-10-12T10:00:00Z')
    assert identity['status'] == 'researching'
    assert read(path)['entities'][0]['registry_crosswalk']['status'] == 'unreviewed'


@pytest.mark.parametrize('filename,country,prefix,sid', CASES)
def test_wrong_typed_task_cannot_claim_or_reconcile(editable, filename, country, prefix, sid):
    root, folder = editable
    _, _, e = entry(folder, filename)
    task = task_for(e, sid)
    task['entity_type'] = 'indian_register_group'
    write(folder / 'coverage_queue.json', {'max_subjects_per_run': 3, 'tasks': [task]})
    before = (folder / 'coverage_queue.json').read_bytes()
    assert any('typed directory scope' in error for error in R.validate(root))
    with pytest.raises(ValueError, match='typed directory scope'):
        R.transition(root, task['task_id'], 'claim', '2026-10-12T10:00:00Z')
    with pytest.raises(ValueError, match='typed directory scope'):
        R.reconcile(root, '2026-10-12T10:00:00Z')
    assert (folder / 'coverage_queue.json').read_bytes() == before


def test_optional_catalogues_preserve_existing_directory_and_queue_fixtures(editable):
    root, folder = editable
    for filename in [CA, BR]:
        (folder / filename).unlink()
    assert I.documents(root) == []
    assert R.validate(root) == []
    page = D.page(builder(root))
    assert '1211 directory records in 2 differently scoped lists' in page
    assert 'ca-profile-' not in page and 'br-census-' not in page



def test_directory_only_id_hold_filters_canada_brazil_page_and_font_roles(editable):
    root, folder = editable
    holds, target_ids, codepoints = [], [], set()
    for index, filename in enumerate([CA, BR]):
        path, doc, e = entry(folder, filename)
        first, second = 0xE121 + 2 * index, 0xE122 + 2 * index
        e['name'], e['directory_name'] = 'Fixture ' + chr(first), 'Fixture source ' + chr(second)
        assert e['registry_crosswalk']['status'] == 'unreviewed'
        assert e['registry_crosswalk']['registry_id'] is None
        write(path, doc)
        target_ids.append(e['directory_id'])
        codepoints.update([first, second])
        holds.append({'directory_id': e['directory_id'], 'action': 'hold' if index == 0 else 'takedown',
                      'requested_at': '2026-10-12T10:00:00Z', 'receipt': 'Fictional removal receipt for acceptance test'})
    b = builder(root)
    page = D.page(b)
    assert all('<li id="' + key + '"' in page for key in target_ids)
    assert all(codepoints <= role for role in F.role_sets(b.m))
    write(folder / 'publication_holds.json', {'schema_version': 1, 'entries': holds})
    page = D.page(b)
    assert all('<li id="' + key + '"' not in page for key in target_ids)
    assert all(not codepoints.intersection(role) for role in F.role_sets(b.m))
    # Catalogues retain their full sourced records; this is a publication hold,
    # not a manufactured identity match, legal finding or source deletion.
    assert len(read(folder / CA)['entities']) == 638
    assert len(read(folder / BR)['entities']) == 391


def test_bad_directory_id_hold_fails_closed_before_page_or_fonts(editable):
    root, folder = editable
    _, _, e = entry(folder, CA)
    good = {'directory_id': e['directory_id'], 'action': 'hold',
            'requested_at': '2026-10-12T10:00:00Z', 'receipt': 'Fictional removal receipt'}
    invalid = []
    undated = dict(good)
    undated.pop('requested_at')
    invalid.append([undated])
    for fields in [{'directory_id': '../unsafe'}, {'action': 'restore'}, {'receipt': ''},
                   {'requested_at': '2026-10-12T10:00:00'}, {'requested_at': 'not-a-date'}]:
        invalid.append([dict(good, **fields)])
    invalid.append([dict(good), dict(good)])
    for entries in invalid:
        write(folder / 'publication_holds.json', {'schema_version': 1, 'entries': entries})
        with pytest.raises((ValueError, KeyError)):
            D.page(builder(root))
        with pytest.raises((ValueError, KeyError)):
            F.role_sets(builder(root).m)


def test_directory_id_removal_preserves_canonical_registry_and_never_reconciles_it_away(editable):
    root, folder = editable
    registry = root / 'data/nations/nations.json'
    registry_before = registry.read_bytes()
    catalogue_before = {name: (folder / name).read_bytes() for name in [CA, BR]}
    holds = [{'directory_id': read(folder / name)['entities'][0]['directory_id'], 'action': 'takedown',
              'requested_at': '2026-10-12T10:00:00Z', 'receipt': 'Fictional removal receipt'} for name in [CA, BR]]
    hold_path = folder / 'publication_holds.json'
    write(hold_path, {'schema_version': 1, 'entries': holds})
    before_hold = hold_path.read_bytes()
    b = builder(root)
    D.page(b)
    F.role_sets(b.m)
    R.reconcile(root, '2026-12-12T10:00:00Z')
    assert registry.read_bytes() == registry_before
    assert b.m.raw == json.loads(registry_before)
    assert all((folder / name).read_bytes() == content for name, content in catalogue_before.items())
    assert hold_path.read_bytes() == before_hold
    assert I.directory_holds(root) == {h['directory_id'] for h in holds}



@pytest.mark.parametrize('hold', ['hide_nation', 'takedown'])
def test_any_bound_chiricahua_profile_hold_removes_composite_resource(editable, hold):
    root, folder = editable
    catalog = read(ROOT / 'data/nations/resources.json')
    card = next(item for item in catalog['resources'] if item.get('nation_ids'))
    assert set(card['nation_ids']) == {'fort-sill-apache-us-ok-nm', 'mescalero-apache-us-nm',
                                     'chiricahua-apache-nation-us-nm'}
    write(root / 'data/nations/resources.json', catalog)
    # Every named participant can require removal; holding only one must remove
    # the whole composite card instead of leaving that nation's name as a route.
    for nid in card['nation_ids']:
        b = builder(root)
        assert 'id="resource-item-' + card['id'] + '"' in b.resources()
        b.m.overrides[hold].append({'nation': nid})
        b.m._apply()
        b.decide()
        page = b.resources()
        assert 'id="resource-item-' + card['id'] + '"' not in page
        assert B.esc(card['summary']) not in page
        assert 'id="history-' + nid + '"' not in page


def test_resource_unknown_canonical_binding_fails_instead_of_rendering(editable):
    root, folder = editable
    catalog = read(ROOT / 'data/nations/resources.json')
    card = next(item for item in catalog['resources'] if item.get('nation_ids'))
    card['nation_ids'].append('fixture-absent-profile')
    write(root / 'data/nations/resources.json', catalog)
    with pytest.raises(B.BuildError, match='invalid canonical nation references'):
        builder(root).resources()



def test_held_typed_subjects_cannot_be_planned_or_claimed_without_changing_receipts(editable):
    root, folder = editable
    tasks, holds, held_ids, unheld_ids = [], [], set(), set()
    for filename, country, prefix, sid in CASES:
        entries = read(folder / filename)['entities'][:2]
        for index, e in enumerate(entries):
            task = task_for(e, sid)
            task['region'] = country
            task['priority'] = 100 if index == 0 else 10
            tasks.append(task)
            (held_ids if index == 0 else unheld_ids).add(task['task_id'])
        holds.append({'directory_id': entries[0]['directory_id'], 'action': 'hold',
                      'requested_at': '2026-10-12T10:00:00Z', 'receipt': 'Fictional directory-only removal receipt'})
    queue_path, hold_path = folder / 'coverage_queue.json', folder / 'publication_holds.json'
    write(queue_path, {'max_subjects_per_run': 3, 'tasks': tasks})
    write(hold_path, {'schema_version': 1, 'entries': holds})
    assert R.validate(root) == []
    before_queue, before_receipts = queue_path.read_bytes(), hold_path.read_bytes()
    # High-priority held entries must remain excluded even well after the receipt
    # date; both unheld typed lanes are available to the bounded planner.
    selected = R.next_tasks(root, 3, '2026-12-12T10:00:00Z')
    assert {t['task_id'] for t in selected} == unheld_ids
    assert not held_ids.intersection(t['task_id'] for t in selected)
    for task_id in held_ids:
        with pytest.raises(ValueError, match='publication hold'):
            R.transition(root, task_id, 'claim', '2026-12-12T10:00:00Z')
        assert queue_path.read_bytes() == before_queue
        assert hold_path.read_bytes() == before_receipts
    assert all(t['status'] == 'pending' and t['receipts'] == [] for t in read(queue_path)['tasks'])
