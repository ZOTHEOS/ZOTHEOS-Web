"""Independent prebuild acceptance for optional short context-note headings.
Fictional fixtures only. No publication data, network, or Web writes.
"""
import hashlib
import html
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
from nations_context import Context

NID = 'fictional-history-acceptance'
FID = 'fictional-history-fact'
TITLE = 'Land <Memory> & "Meaning"'
BODY = 'A fictional history paragraph for heading acceptance.'
OLD = 'An untitled legacy context note.'
# Fictional untitled fixture; only the approved ZOTHEOS editorial credit changed on 2026-10-16.
LEGACY_SHA256 = '5cef1f03c1015fe4d90706dc7211e896aac3b4be23a0518beca94e19155d4516'


def context(root, notes, *, held_profile=False, held_fact=False):
    folder = root / 'data/nations'
    (folder / 'sources').mkdir(parents=True, exist_ok=True)
    (folder / 'context_links.json').write_text(json.dumps({'version': 1, 'links': []}), encoding='utf-8')
    (folder / 'sources' / 'fictional.context.json').write_text(json.dumps({
        'reviewed': '2020-01-02', 'public_notes': notes}), encoding='utf-8')
    raw = {'id': NID, 'name': 'Fictional History Acceptance', 'facts': [{'id': FID}]}
    public = dict(raw, facts=[] if held_fact else raw['facts'])
    model = SimpleNamespace(raw={'nations': [raw]}, nations=[] if held_profile else [public],
                            by_id={} if held_profile else {NID: public}, build_date='2020-01-02')
    return Context(root, model)


def note(**values):
    return dict({'nation': NID, 'text': BODY}, **values)


def test_optional_heading_escapes_precedes_body_and_follows_removal_controls(tmp_path):
    legacy = context(tmp_path, [{'nation': NID, 'text': OLD}]).page(NID)
    assert hashlib.sha256(legacy.encode()).hexdigest() == LEGACY_SHA256
    titled = note(title=TITLE, fact_ids=[FID])
    output = context(tmp_path, [{'nation': NID, 'text': OLD}, titled]).page(NID)
    heading = '<h3 class="n-sec-h">' + html.escape(TITLE, quote=True) + '</h3>'
    problems = []
    if heading not in output:
        problems.append('The escaped optional heading is missing')
    elif output.index(heading) > output.index(html.escape(BODY)):
        problems.append('The heading follows its paragraph instead of preceding it')
    if TITLE in output:
        problems.append('Unescaped title content reached the HTML')
    if '<p class="fact-t">' + OLD + '</p>' not in output:
        problems.append('Legacy untitled paragraph changed')
    for mode in ('held_profile', 'held_fact'):
        held = context(tmp_path, [titled], **{mode: True}).page(NID)
        if html.escape(TITLE, quote=True) in held or BODY in held:
            problems.append(mode + ' left the heading or note public')
    removed = context(tmp_path, [{'nation': NID, 'text': OLD}]).page(NID)
    if hashlib.sha256(removed.encode()).hexdigest() != LEGACY_SHA256:
        problems.append('Removing the titled note changed legacy output')
    assert not problems, problems


def test_optional_heading_rejects_invalid_or_oversized_titles(tmp_path):
    invalid = [None, False, 17, [], {}, '', '   ', 'x' * 161]
    accepted = []
    for index, value in enumerate(invalid):
        try:
            context(tmp_path / str(index), [note(title=value)])
        except ValueError:
            pass
        else:
            accepted.append(type(value).__name__ + ':' + repr(value)[:32])
    assert not accepted, 'Invalid heading values were silently accepted: ' + repr(accepted)
    # The boundary itself remains valid; this is text, never HTML or a new fact receipt.
    context(tmp_path / 'boundary', [note(title='x' * 160)])
