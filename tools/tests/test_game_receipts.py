"""The playable cards retain the canonical nations and honest source receipts."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import ROOT


def game_eval(body, data):
    node = shutil.which('node')
    if not node:
        pytest.skip('node is not installed')
    setup = r'''
const fs=require('fs'),vm=require('vm');
const source=fs.readFileSync(process.argv[1]+'/game/index.src.html','utf8');
const context=vm.createContext({window:{},document:{getElementById:()=>null},setTimeout,clearTimeout,DATA:fs.readFileSync(0,'utf8')});
vm.runInContext('DATA=JSON.parse(DATA)',context);
vm.runInContext(source.match(/<script>([\s\S]*?)<\/script>/)[1],context);
const ev=s=>context.window.ZTH_GAME._ev(s);
ev('devNat=0');
'''
    result = subprocess.run([node, '-e', setup + body, ROOT], input=json.dumps(data),
                            capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_every_exported_nation_and_historical_fact_survives_ui_validation():
    nations = json.loads((Path(ROOT)/'game/nations.json').read_text(encoding='utf-8'))
    histories = json.loads((Path(ROOT)/'game/history.json').read_text(encoding='utf-8'))
    facts = [f for n in histories['nations'].values() for group in ('history', 'context') for f in n[group]]
    got = game_eval("console.log(JSON.stringify(ev('[natValid(DATA.nations).map(function(n){return n.id}), DATA.facts.every(function(f){return !!natFact(f, \\\"2099-01-01\\\")})]')));",
                    {'nations': nations['nations'], 'facts': facts})
    assert set(got[0]) == {n['id'] for n in nations['nations']}
    assert got[1]


def test_receipts_separate_source_access_check_and_human_or_grace_states():
    f = {'text': 'Published fact.', 'kind': 'history', 'source': {'publisher': 'Nation', 'title': 'History',
         'url': 'https://example.org/history', 'accessed': '2026-10-09'}, 'checked': '2026-10-08', 'state': 'ok'}
    rows = [f, dict(f, state='human'), dict(f, state='grace', note='2026-10-10')]
    legacy = dict(f)
    legacy.pop('checked')
    legacy.pop('state')
    rows.append(legacy)
    labels = game_eval("console.log(JSON.stringify(ev('DATA.map(function(f){return natReceipt(natFact(f, \\\"2026-10-12\\\"))})')));", rows)
    assert labels == ['Checked 2026-10-08.', 'Checked By A Person 2026-10-08.',
                      'Last Successful Check 2026-10-08.', 'Source Accessed 2026-10-09.']


def test_ui_rejects_unsafe_sources_future_receipts_and_unknown_states():
    f = {'text': 'Published fact.', 'kind': 'history', 'source': {'publisher': 'Nation', 'title': 'History',
         'url': 'https://example.org/history', 'accessed': '2026-10-09'}, 'checked': '2026-10-08', 'state': 'ok'}
    rows = [dict(f, source=dict(f['source'], url='javascript:alert(1)')), dict(f, checked='2099-01-01'),
            dict(f, state='invented'), dict(f, note='2099-01-01'), dict(f, text='x'*301), dict(f, kind='test')]
    got = game_eval("console.log(JSON.stringify(ev('DATA.map(function(f){return natFact(f, \\\"2026-10-12\\\")})')));", rows)
    assert got == [None]*len(rows)
