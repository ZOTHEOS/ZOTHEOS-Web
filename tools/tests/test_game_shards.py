"""Growth boundaries, exact public coverage, and removal of obsolete public copies."""
import collections
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import game_nations as G
import nations_lib as L
from conftest import ROOT


def unpack(outputs, name):
    doc = json.loads(outputs['game/' + name + '.json'])
    if 'shards' not in doc:
        return doc['nations']
    rows = [] if name == 'nations' else {}
    for entry in doc['shards']:
        text = outputs['game/data/' + entry[0]]
        assert hashlib.sha256(text.encode()).hexdigest()[:32] in entry[0]
        child = json.loads(text)
        assert child['count'] == len(child['nations']) == entry[1]
        assert 'shards' not in child
        if isinstance(rows, list):
            rows.extend(child['nations'])
        else:
            assert not set(rows).intersection(child['nations'])
            rows.update(child['nations'])
    assert len(rows) == doc['count']
    return rows


def test_legacy_bytes_preserved_until_the_exact_utf8_boundary():
    rows = [dict(id='nation-%02d' % i, region='a', text='\u00e9' * 100) for i in range(20)]
    doc = dict(updated='2026-10-12', count=len(rows), source='fixture', nations=rows)
    expected = json.dumps(doc, ensure_ascii=False, separators=(',', ':'))
    size = len(expected.encode())
    text, shards = G.partition(doc, size + 1, 'n')
    assert text == expected and not shards
    text, shards = G.partition(doc, size, 'n')
    outputs = dict(shards, **{'game/nations.json': text})
    assert {n['id']: n for n in unpack(outputs, 'nations')} == {n['id']: n for n in rows}
    assert all(len(s.encode()) < size for s in outputs.values())


def test_count_cap_shards_even_when_bytes_fit_and_regions_are_balanced():
    rows = [dict(id='nation-%04d' % i, region='small' if i < 7 else 'medium' if i < 22 else 'large')
            for i in range(1201)]
    doc = dict(updated='2026-10-12', count=len(rows), source='fixture', nations=rows)
    text, shards = G.partition(doc, G.LIMIT, 'n')
    manifest = json.loads(text)
    assert len(manifest['shards']) == 3
    counts = [p[1] for p in manifest['shards']]
    assert max(counts) - min(counts) <= 1 and max(counts) <= 600
    regions = [collections.Counter(n['region'] for n in json.loads(s)['nations']) for s in shards.values()]
    for region in ('small', 'medium', 'large'):
        assert max(r[region] for r in regions) - min(r[region] for r in regions) <= 1
    actual = unpack(dict(shards, **{'game/nations.json': text}), 'nations')
    assert len({n['id'] for n in actual}) == 1201
    assert G.partition(doc, G.LIMIT, 'n') == (text, shards)


def test_forced_shards_are_lossless_including_sources_receipts_and_holds(monkeypatch):
    model = L.Model(ROOT)
    expected_outputs, expected, skipped = G.build(ROOT, model=model)
    expected_history = unpack(expected_outputs, 'history')
    assert not skipped
    # Force independent quick/history boundaries using real public data.
    monkeypatch.setattr(G, 'LIMIT', 50000)
    monkeypatch.setattr(G, 'HISTORY_LIMIT', 12000)
    outputs, _, skipped = G.build(ROOT, model=model)
    assert not skipped
    assert {n['id']: n for n in unpack(outputs, 'nations')} == {n['id']: n for n in expected}
    assert unpack(outputs, 'history') == expected_history
    for rel, text in outputs.items():
        assert len(text.encode()) < (12000 if '/h-' in rel or rel.endswith('/history.json') else 50000)
    assert 'Bhuri Bai' not in ''.join(outputs.values())
    # History ranges must route every exact ID to the one shard containing it.
    manifest = json.loads(outputs['game/history.json'])
    for nid in expected_history:
        target = next(p for p in manifest['shards'] if nid <= p[2])
        assert nid in json.loads(outputs['game/data/' + target[0]])['nations']


def test_holds_remove_old_public_shards_and_check_detects_stale_copies(tmp_path, monkeypatch):
    shutil.copytree(Path(ROOT)/'data/nations', tmp_path/'data/nations',
                    ignore=shutil.ignore_patterns('sources', 'tools', '*.md', 'nations.min.json'))
    monkeypatch.setattr(G, 'LIMIT', 50000)
    monkeypatch.setattr(G, 'HISTORY_LIMIT', 12000)
    assert G.main(['--root', str(tmp_path)]) == 0
    old = set((tmp_path/'game/data').glob('*.json'))
    unrelated = tmp_path/'game/data/keep-this.json'
    unrelated.write_text('{}', encoding='utf-8')
    raw = json.loads((tmp_path/'data/nations/nations.json').read_text(encoding='utf-8'))
    held = next(f for n in raw['nations'] for f in n['facts'] if f['kind'] == 'history')
    overrides_path = tmp_path/'data/nations/overrides.json'
    overrides = json.loads(overrides_path.read_text(encoding='utf-8'))
    overrides['hide_fact'].append({'fact': held['id']})
    overrides_path.write_text(json.dumps(overrides), encoding='utf-8')
    assert G.main(['--root', str(tmp_path), '--check']) == 1
    assert G.main(['--root', str(tmp_path)]) == 0
    assert old - set((tmp_path/'game/data').glob('*.json'))
    assert unrelated.read_text(encoding='utf-8') == '{}'
    assert all(held['text'] not in p.read_text(encoding='utf-8') for p in (tmp_path/'game').rglob('*.json'))
    assert G.main(['--root', str(tmp_path), '--check']) == 0
    # An obsolete but correctly named copy is itself a failed check, even when
    # every current output matches. --check must not remove it.
    orphan = tmp_path/'game/data'/('h-' + '0'*32 + '.json')
    orphan.write_text('{}', encoding='utf-8')
    assert G.main(['--root', str(tmp_path), '--check']) == 1
    assert orphan.exists()


def test_loader_acceptance():
    node = shutil.which('node')
    assert node, 'Node is required for the game loader acceptance check'
    result = subprocess.run([node, str(Path(__file__).with_name('game-shards-acceptance.js')),
                             str(Path(G.ROOT)/'game/index.src.html')],
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
