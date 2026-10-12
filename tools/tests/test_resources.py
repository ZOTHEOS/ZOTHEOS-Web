"""Resources preserve the registry's publication boundaries, sources and checking receipts."""
import json
import re
from pathlib import Path

import pytest

import nations_build as B
from conftest import ROOT


def resource_builder():
    b = B.Builder(ROOT)
    # Inspect page content independently of the common frame already covered by the page build gates.
    b.sp = lambda key, body, description: body
    return b


def test_resources_include_every_published_history_with_source_and_full_nation_link():
    b = resource_builder()
    page = b.resources()
    members = [n for n in b.m.nations if any(f['kind'] == 'history' for f in n['facts'])]
    expected = {f['id'] for n in members for f in n['facts']}
    assert set(re.findall(r'id="history-fact-([^"]+)"', page)) == expected
    for n in members:
        assert b.name_el(n, 'span', 'nm row-name') in page
        assert f'href="/nations/{n["id"]}"' in page
        for f in n['facts']:
            assert B.esc(f['text']) in page
            assert B.url(f['url']) in page
            assert B.esc(f['publisher']) in page
    assert str(len(members)) + ' nations are collected below' in page
    assert str(len(b.m.nations)) + ' nations.' in page
    assert 'not complete histories' in page
    assert '<script' not in page and '<iframe' not in page
    assert 'Bhuri Bai' not in page


def test_resources_recompute_coverage_after_history_withdrawal_and_nation_takedown():
    b = resource_builder()
    before = b.resources()
    nation = b.m.raw['nations'][0]
    fact = next(f for f in nation['facts'] if f['kind'] == 'history')
    fact['status'] = 'stale'
    b.m.overrides['takedown'].append({'nation': 'benet-uganda'})
    b.m._apply()
    b.decide()
    after = b.resources()
    assert 'id="history-' + nation['id'] + '"' in before
    assert 'id="history-' + nation['id'] + '"' not in after
    assert 'id="history-benet-uganda"' not in after
    assert B.esc(fact['text']) not in after
    count = sum(any(f['kind'] == 'history' for f in n['facts']) for n in b.m.nations)
    assert f'{count} nations are collected below' in after
    assert f'{len(b.m.nations)} nations.' in after


def test_history_receipt_uses_last_verified_date_and_discloses_failed_attempt():
    b = resource_builder()
    b.m.build_date = '2026-10-20'
    fact = next(f for f in b.m.raw['nations'][0]['facts'] if f['kind'] == 'history')
    fact.update(status='unreachable', checked='2026-10-20', last_verified='2026-10-08')
    b.m._apply()
    b.decide()
    page = b.resources()
    block = re.search(r'<article class="fact" id="history-fact-' + re.escape(fact['id']) + r'">(.*?)</article>', page, re.S).group(1)
    assert 'Checked <time datetime="2026-10-08">' in block
    assert 'Our tool could not reach the page on <time datetime="2026-10-20">' in block
    assert 'Checked <time datetime="2026-10-09">' not in block


def test_resources_reject_unsafe_external_link(tmp_path):
    b = resource_builder()
    data = json.loads((Path(ROOT) / 'data/nations/resources.json').read_text(encoding='utf-8'))
    data['resources'][0]['links'][0]['url'] = 'javascript:alert(1)'
    target = tmp_path / 'data/nations/resources.json'
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(data), encoding='utf-8')
    b.root = str(tmp_path)
    with pytest.raises(B.BuildError, match='refused URL'):
        b.resources()

def test_nation_cannot_overwrite_the_resources_route(monkeypatch):
    model = B.L.Model(ROOT)
    model.nations[0]['id'] = 'resources'
    monkeypatch.setattr(B.L, 'Model', lambda *args, **kwargs: model)
    with pytest.raises(B.BuildError, match='support pages: resources'):
        B.Builder(ROOT)
