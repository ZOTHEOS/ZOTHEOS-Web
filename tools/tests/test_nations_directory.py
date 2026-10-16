"""Directory names remain visible without inventing identity matches or profile facts."""
import json
from pathlib import Path
import re
import shutil

import pytest
import nations_build as B
import nations_directory as D
from conftest import ROOT


def builder():
    b = B.Builder(ROOT)
    b.sp = lambda key, body, description: body
    return b


def editable(tmp_path):
    target = tmp_path / 'data/nations/research'
    shutil.copytree(Path(ROOT) / 'data/nations/research', target)
    p = target / 'us_federal_directory.json'
    return p, json.loads(p.read_text(encoding='utf-8'))


def write(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')


def test_every_dated_source_record_is_visible_and_count_discrepancy_is_disclosed():
    b = builder()
    directory, _ = D.load(ROOT)
    page = D.page(b)
    rendered = re.findall(r'<li id="(us-fed-[a-f0-9]{12})"', page)
    assert len(rendered) == len(set(rendered)) == directory['enumerated_count']
    assert set(rendered) == {e['directory_id'] for e in directory['entities']}
    for e in directory['entities']:
        assert B.esc(e['directory_name']) in page
        assert B.esc(e['name']) in page
    assert B.esc(directory['count_discrepancy']['note']) in page
    assert 'not a researched profile' in page
    assert 'Federal recognition is not a definition of Indigenous identity' in page
    assert 'No worldwide completion percentage is claimed' in page
    assert '577' in page and '575' in page


def test_name_candidates_do_not_invent_profile_links(tmp_path):
    b = builder()
    p, obj = editable(tmp_path)
    e = obj['entities'][0]
    e['registry_crosswalk'] = {'status': 'unreviewed', 'registry_id': None, 'candidates': []}
    e['registry_crosswalk']['candidates'] = [{'registry_id': b.m.nations[0]['id'], 'basis': 'exact_name_or_alias'}]
    write(p, obj)
    b.root = str(tmp_path)
    page = D.page(b)
    block = page.split('<li id="' + e['directory_id'] + '"', 1)[1].split('</li>', 1)[0]
    assert '/nations/' + b.m.nations[0]['id'] not in block
    e['registry_crosswalk']['registry_id'] = b.m.nations[0]['id']
    write(p, obj)
    with pytest.raises(ValueError, match='unreviewed'):
        D.page(b)


def test_confirmed_profile_takedown_is_not_bypassed_by_the_directory(tmp_path):
    b = builder()
    p, obj = editable(tmp_path)
    e = obj['entities'][0]
    nid = b.m.nations[0]['id']
    e['registry_crosswalk'].update(status='confirmed', registry_id=nid,
                                  reviewer='Explicit identity review fixture', evidence_receipt='fixture-receipt')
    write(p, obj)
    b.root = str(tmp_path)
    assert '<li id="' + e['directory_id'] + '"' in D.page(b)
    b.m.overrides['takedown'].append({'nation': nid})
    b.m._apply()
    b.decide()
    page = D.page(b)
    assert '<li id="' + e['directory_id'] + '"' not in page
    assert '/nations/' + nid not in page


@pytest.mark.parametrize('change', ['count', 'groups', 'url', 'resolved'])
def test_a_bad_directory_snapshot_fails_instead_of_claiming_complete_coverage(tmp_path, change):
    p, obj = editable(tmp_path)
    if change == 'count':
        obj['enumerated_count'] -= 1
    elif change == 'groups':
        obj['group_counts']['alaska'] -= 1
    elif change == 'url':
        obj['source']['url'] = 'javascript:alert(1)'
    elif change == 'resolved':
        obj['count_discrepancy']['status'] = 'resolved'
    write(p, obj)
    with pytest.raises(ValueError):
        D.load(tmp_path)


def test_directory_names_render_as_text_even_when_the_source_contains_markup(tmp_path):
    b = builder()
    p, obj = editable(tmp_path)
    obj['entities'][0]['name'] = '<img src=x onerror=alert(1)>'
    obj['entities'][0]['directory_name'] = '<script>bad()</script>'
    write(p, obj)
    b.root = str(tmp_path)
    page = D.page(b)
    assert '<img src=x' not in page and '<script>bad()' not in page
    assert '&lt;img src=x onerror=alert(1)&gt;' in page


def test_directory_route_is_reserved_from_nation_ids(monkeypatch):
    model = B.L.Model(ROOT)
    model.nations[0]['id'] = 'directory'
    monkeypatch.setattr(B.L, 'Model', lambda *args, **kwargs: model)
    with pytest.raises(B.BuildError, match='support pages: directory'):
        B.Builder(ROOT)


def test_canadian_administrative_names_keep_their_dated_scope_and_unique_codes():
    b = builder()
    doc = D.load_canada(ROOT)
    page = D.page(b)
    rendered = re.findall(r'<li id="(ca-register-[0-9]{3})"', page)
    assert len(rendered) == len(set(rendered)) == 634
    assert set(rendered) == {e['directory_id'] for e in doc['entities']}
    for e in doc['entities']:
        assert B.esc(e['directory_name']) in page
        assert not e['name'].lower().startswith('general list')
    assert 'not a count of current governments or all Indigenous peoples' in page
    assert '619 bands from 634 registry groups' in page
    assert 'December 31, 2024' in page
    extra = D.inventories(ROOT)
    total = 1211 + sum(d['enumerated_count'] for d in extra)
    assert str(total) + ' directory records in ' + str(2 + len(extra)) + ' differently scoped lists' in page


def test_all_directory_names_have_whole_glyphs_in_their_selected_face():
    from nations_lint import Faces
    b = builder()
    faces = Faces(ROOT)
    directory, _ = D.load(ROOT)
    for e in directory['entities'] + D.load_canada(ROOT)['entities'] + [e for d in D.inventories(ROOT) for e in d['entities']]:
        if b.brand.serif_ok(e['name']):
            assert not faces.miss(e['name'], 'brand-name'), e['name']
        else:
            assert all(c.isspace() or ord(c) in faces.cov['ZN Serif'] for c in e['name']), e['name']
        assert not faces.miss(e['directory_name'], 'reading'), e['directory_name']


def test_public_source_captures_preserve_measured_bytes_and_hashes():
    import hashlib
    folder = Path(ROOT) / 'data/nations/research/receipts'
    captures = 0
    for rp in folder.glob('*.receipt.json'):
        receipt = json.loads(rp.read_text(encoding='utf-8'))
        stem = rp.name[:-len('.receipt.json')]
        bodies = [folder / (stem + ext) for ext in ('.html', '.xml', '.json')]
        bodies = [p for p in bodies if p.exists()]
        if not bodies:
            assert 'local' in receipt.get('capture_retention', '').lower(), rp.name
            continue
        assert len(bodies) == 1
        body = bodies[0].read_bytes()
        assert len(body) == receipt['bytes'], rp.name
        assert hashlib.sha256(body).hexdigest() == receipt['sha256'], rp.name
        captures += 1
    assert captures >= 6
