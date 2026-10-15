"""Acceptance for directory-bound source notes and their publication holds.

Actual source notes are reviewed separately; all removal requests here are fictional fixtures.
"""
import json
import os
from pathlib import Path
import sys

import pytest

sys.dont_write_bytecode = True
ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT / 'tools/tests'))
from test_us_state_directory_acceptance import isolated, unreviewed_source_rows, builder, read, write, CASES
import nations_directory as D
import nations_fonts as F
import nations_inventories as I


def scoped(doc):
    notes = doc.get('scoped_notes', [])
    assert notes, 'The actual named source note must use explicit directory bindings'
    return notes[0]


def inventory_section(page, anchor):
    return page.split('id="' + anchor + '"', 1)[1].split('</ul></section>', 1)[0]


@pytest.mark.parametrize('filename,state,sid', CASES)
def test_each_bound_directory_hold_suppresses_actual_named_source_note(unreviewed_source_rows, filename, state, sid):
    root, folder = unreviewed_source_rows
    doc = read(folder / filename)
    note = scoped(doc)
    anchor = 'us-virginia' if state == 'VA' else 'us-north-carolina'
    b = builder(root)
    unheld = inventory_section(D.page(b), anchor)
    assert D.esc(note['text']) in unheld
    assert set(note['directory_ids']) <= {e['directory_id'] for e in doc['entities']}
    assert all(e['registry_crosswalk']['status'] == 'unreviewed' for e in doc['entities'])
    for key in note['directory_ids']:
        write(folder / 'publication_holds.json', {'schema_version': 1, 'entries': [{
            'directory_id': key, 'action': 'takedown',
            'requested_at': '2026-10-14T06:00:00Z',
            'receipt': 'Fictional isolated acceptance removal request.'
        }]})
        held = inventory_section(D.page(b), anchor)
        assert '<li id="' + key + '"' not in held
        assert D.esc(note['text']) not in held
        if state == 'NC':
            assert 'Read the other published account' not in held
        for other in doc['entities']:
            if other['directory_id'] != key:
                assert '<li id="' + other['directory_id'] + '"' in held
        assert len(read(folder / filename)['entities']) == doc['enumerated_count']


@pytest.mark.parametrize('filename,state,sid', CASES)
def test_holding_unrelated_row_keeps_scoped_source_note_visible(isolated, filename, state, sid):
    root, folder = isolated
    doc = read(folder / filename)
    note = scoped(doc)
    other = next(e['directory_id'] for e in doc['entities'] if e['directory_id'] not in note['directory_ids'])
    write(folder / 'publication_holds.json', {'schema_version': 1, 'entries': [{
        'directory_id': other, 'action': 'hold', 'requested_at': '2026-10-14T06:00:00Z',
        'receipt': 'Fictional unrelated removal request for acceptance.'
    }]})
    page = D.page(builder(root))
    assert D.esc(note['text']) in page
    assert '<li id="' + other + '"' not in page


@pytest.mark.parametrize('filename,state,sid', CASES)
def test_bound_hold_removes_name_font_input_and_note_together(isolated, filename, state, sid):
    root, folder = isolated
    path = folder / filename
    doc = read(path)
    note = scoped(doc)
    key = note['directory_ids'][0]
    row = next(e for e in doc['entities'] if e['directory_id'] == key)
    glyph = chr(0xE449 if state == 'VA' else 0xE44A)
    row['name'] = 'Fictional ' + glyph
    row['directory_name'] = 'Fictional published ' + glyph
    note['text'] = 'Fictional bounded source explanation for ' + row['name'] + '.'
    write(path, doc)
    b = builder(root)
    assert D.esc(note['text']) in D.page(b)
    assert all(ord(glyph) in role for role in F.role_sets(b.m))
    write(folder / 'publication_holds.json', {'schema_version': 1, 'entries': [{
        'directory_id': key, 'action': 'hold', 'requested_at': '2026-10-14T06:00:00Z',
        'receipt': 'Fictional held name and source note for font acceptance.'
    }]})
    page = D.page(b)
    assert glyph not in page
    assert D.esc(note['text']) not in page
    assert all(ord(glyph) not in role for role in F.role_sets(b.m))


@pytest.mark.parametrize('corrupt', ['no_ids', 'unknown_id', 'duplicate_id', 'too_many_ids',
                                    'bad_kind', 'too_long_text', 'too_many_notes'])
def test_scoped_note_contract_rejects_unbounded_or_unknown_subjects(isolated, corrupt):
    root, folder = isolated
    path = folder / CASES[0][0]
    doc = read(path)
    note = scoped(doc)
    if corrupt == 'no_ids': note['directory_ids'] = []
    elif corrupt == 'unknown_id': note['directory_ids'] = ['us-state-va-fictional-absent']
    elif corrupt == 'duplicate_id': note['directory_ids'] = [note['directory_ids'][0]] * 2
    elif corrupt == 'too_many_ids': note['directory_ids'] = [note['directory_ids'][0]] * 17
    elif corrupt == 'bad_kind': note['kind'] = 'verified_fact'
    elif corrupt == 'too_long_text': note['text'] = 'x' * 2001
    else: doc['scoped_notes'] = [dict(note) for _ in range(33)]
    write(path, doc)
    with pytest.raises(ValueError): I.documents(root)


@pytest.mark.parametrize('corrupt', ['unknown_subject', 'non_https_url'])
def test_conflict_source_link_cannot_escape_its_directory_subject_or_https_scope(isolated, corrupt):
    root, folder = isolated
    path = folder / CASES[1][0]
    doc = read(path)
    conflict = doc['source_discrepancies'][0]
    if corrupt == 'unknown_subject': conflict['subject_directory_id'] = 'us-state-nc-fictional-absent'
    else: conflict['announcement_url'] = 'http://example.invalid/unreviewed'
    write(path, doc)
    with pytest.raises(ValueError): I.documents(root)
