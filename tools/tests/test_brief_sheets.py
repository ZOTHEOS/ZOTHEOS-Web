"""Printable brief sheets, /nations/brief/<chapter> (Living Gallery, Batch 1, piece 3).

Fictional records exercise the real renderer and builder; the committed pages are checked against the committed
plain-text briefs, line for line. These tests do not certify source truth, legal sufficiency, permission or outcomes.
"""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

import pytest

REPO = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(REPO / 'tools/tests'))
sys.path.insert(0, str(REPO / 'tools'))
from test_indigenous_pathways import fixture_catalogue, fixture_model, tree  # noqa: E402

BLANK = '____________________'
CONTROLS = {'form', 'input', 'button', 'textarea', 'select', 'script', 'iframe', 'img', 'svg', 'video', 'audio', 'canvas'}
CREDIT = 'Original project geometry by ZOTHEOS. It has no traditional or ceremonial meaning.'


@pytest.fixture
def sheets(tmp_path, monkeypatch):
    data, model = fixture_catalogue(), fixture_model()
    path = tmp_path / 'data/nations/pathways.json'
    path.parent.mkdir(parents=True)
    art = importlib.import_module('zth_art')
    monkeypatch.setattr(art, 'ART_STEPS', art.ART_STEPS)

    def module():
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf8')
        spec = importlib.util.spec_from_file_location('brief_sheet_contract', REPO / 'tools/nations_pathways.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return data, model, module, tmp_path, art


def classes(node):
    return node.attrs.get('class', '').split()


def sheet_lines(html):
    """The text of every [data-line] element in order, each blank written as the text file writes it (the hidden word
    'Blank.' becomes a space and the underscores), each heading in the capitals the text file uses."""
    def text(node):
        if 'bs-rule' in classes(node):
            return ' ' + BLANK
        return ''.join(text(c) if hasattr(c, 'tag') else c for c in node.children)
    lines = []
    for node in tree(html).walk():
        if 'data-line' in node.attrs:
            line = text(node)
            lines.append(line.upper() if node.attrs.get('data-case') == 'upper' else line)
    return lines


def test_preview_equals_download_line_for_line(sheets):
    data, model, module, root, _ = sheets
    mod = module()
    texts = mod.chapter_briefs(str(root), model)
    built = mod.brief_sheets(str(root), model)
    assert [cid for cid, _, _ in built] == [c['id'] for c in data['chapters']]
    for cid, title, html in built:
        assert sheet_lines(html) == [line for line in texts['action-brief-' + cid + '.txt'].split('\n') if line]
        assert title == next(c['title'] for c in data['chapters'] if c['id'] == cid)


def test_committed_sheets_match_committed_plain_text_briefs():
    """The pages as built say exactly what the downloads say, one sheet per brief, each in the sitemap and linked once
    from its chapter of the guide."""
    pages = sorted((REPO / 'nations/brief').glob('*.html'))
    briefs = sorted((REPO / 'static/nations').glob('action-brief-*.txt'))
    assert pages, 'the build writes one printable sheet per public pathway'
    assert {p.stem for p in pages} == {b.stem[len('action-brief-'):] for b in briefs}
    sitemap = (REPO / 'sitemap.xml').read_text(encoding='utf8')
    guide = (REPO / 'nations/paths-to-action.html').read_text(encoding='utf8')
    for page in pages:
        html = page.read_text(encoding='utf8')
        text = (REPO / 'static/nations' / ('action-brief-' + page.stem + '.txt')).read_text(encoding='utf8')
        main = html[html.index('<main id="main">'):html.index('</main>')]
        assert sheet_lines(main) == [line for line in text.split('\n') if line]
        assert sitemap.count(f'<loc>https://zotheos.org/nations/brief/{page.stem}</loc>') == 1
        assert guide.count(f'href="/nations/brief/{page.stem}"') == 1
        title = re.search(r'<h1 class="page-h bs-title" id="bs-title" data-line>([^<]+)</h1>', html).group(1)
        assert '<title>' + title + ' Brief Sheet | Indigenous nations today</title>' in html


def test_sheet_structure_links_and_blank_fields(sheets):
    data, model, module, root, _ = sheets
    mod = module()
    cid, title, html = mod.brief_sheets(str(root), model)[0]
    doc = tree(html)
    h1 = [n for n in doc.walk() if n.tag == 'h1']
    assert len(h1) == 1 and h1[0].text == title and h1[0].attrs.get('id') == 'bs-title'
    fields = [n for n in doc.walk() if n.tag == 'ol' and 'bs-fields' in classes(n)]
    assert len(fields) == 1
    rows = [n for n in fields[0].children if getattr(n, 'tag', '') == 'li']
    expected = [line for line in mod.chapter_brief(str(root), model, cid).split('\n') if line.endswith(BLANK)]
    assert len(rows) == len(expected) == 12
    for row in rows:
        blank = [n for n in row.walk() if 'bs-rule' in classes(n)]
        assert len(blank) == 1 and blank[0].text == 'Blank.'
    anchors = [n for n in doc.walk() if n.tag == 'a']
    back = [n.text for n in anchors if n.attrs.get('href') == '/nations/paths-to-action#pw-' + cid]
    assert back == ['https://zotheos.org/nations/paths-to-action#pw-' + cid, 'Back To This Pathway ↑']
    download = [n for n in anchors if n.attrs.get('href') == '/static/nations/action-brief-' + cid + '.txt']
    assert len(download) == 1 and 'download' in download[0].attrs
    # WCAG 2.5.3 (label in name): the accessible name starts with the visible words, then names the pathway.
    visible = download[0].text.replace('↗', '').strip()
    assert visible == mod.SHEET_DOWNLOAD == 'Download This Pathway Brief'
    assert download[0].attrs['aria-label'] == visible + ': ' + title
    assert mod.SHEET_NOTE in doc.text
    for node in anchors:
        if node.attrs.get('href', '').startswith('https://'):
            assert set(node.attrs.get('rel', '').split()) == {'noopener', 'noreferrer'} and node.attrs.get('target') == '_blank'


def test_sheet_carries_no_nation_example_name_or_control(sheets):
    data, model, module, root, _ = sheets
    data['chapters'][0]['examples'][0]['practice'] = {
        'question': 'Practice question sentinel', 'steps': ['Practice step sentinel'],
        'boundary': 'Practice boundary sentinel', 'reflection': 'Practice reflection sentinel'}
    mod = module()
    for _, _, html in mod.brief_sheets(str(root), model):
        doc = tree(html)
        assert not [n for n in doc.walk() if n.tag in CONTROLS]
        assert not re.search(r'\son\w+\s*=|\sstyle\s*=|tabindex', html, re.I)
        for forbidden in ['Fixture Nation', '/nations/fixture-nation', 'pw-example', 'Exact public fact',
                          'nation.example.test', 'Practice question sentinel', 'Practice step sentinel']:
            assert forbidden not in html


def test_a_line_the_sheet_does_not_know_is_still_shown_as_written(sheets, monkeypatch):
    """The sheet reads the text file's own lines. A line Codex adds later appears on the sheet as written, in place,
    so the sheet never needs a second copy of the brief's words."""
    data, model, module, root, _ = sheets
    mod = module()
    original = mod._chapter_brief_text
    monkeypatch.setattr(mod, '_chapter_brief_text', lambda c, s: original(c, s).replace(
        '\nREFLECTION\n', '\nREFLECTION\nAn added sentence sentinel.\n').replace(
        '\nSOURCES AND DATES\n', '\nSOURCES AND DATES\nA source line in a new format sentinel\n'))
    for cid, _, html in mod.brief_sheets(str(root), model):
        text = mod._chapter_brief_text(next(c for c in data['chapters'] if c['id'] == cid), mod.load(str(root), model)[2])
        assert sheet_lines(html) == [line for line in text.split('\n') if line]
        assert 'An added sentence sentinel.' in html


def test_named_source_hold_removes_sheet_link_and_sitemap_entry(sheets, tmp_path):
    data, model, module, root, _ = sheets
    data['sources'][0]['nation'] = 'fixture-nation'
    model.by_id.clear()
    mod = module()
    ids = [cid for cid, _, _ in mod.brief_sheets(str(root), model)]
    assert ids == ['language-and-culture']
    guide = mod.render(str(root), model)
    assert '/nations/brief/land-and-water' not in guide and guide.count('href="/nations/brief/language-and-culture"') == 1
    import nations_build as builder
    out = tmp_path / 'site'
    out.mkdir()
    (out / 'sitemap.xml').write_text('<?xml version="1.0"?>\n<urlset>\n</urlset>\n', encoding='utf8')
    stub = SimpleNamespace(m=SimpleNamespace(regions=[], by_country={}, nations=[]))
    builder.Builder.write_sitemap(stub, str(out), {f'nations/brief/{cid}.html': '' for cid in ids})
    sitemap = (out / 'sitemap.xml').read_text(encoding='utf8')
    assert '/nations/brief/language-and-culture</loc>' in sitemap and '/nations/brief/land-and-water' not in sitemap


def test_brief_is_a_reserved_path_and_a_nation_named_brief_stops_the_build(monkeypatch, tmp_path):
    import nations_lib as L
    import nations_build as builder
    assert 'brief' in L.RESERVED_IDS
    monkeypatch.setattr(L, 'Model', lambda root, date=None: SimpleNamespace(errors=[], nations=[{'id': 'brief'}]))
    with pytest.raises(builder.BuildError, match='brief'):
        builder.Builder(str(tmp_path))


@pytest.mark.parametrize('case', ['missing-word', 'part-inside-word', 'one-part', 'no-parts', 'duplicate', 'extra-key'])
def test_a_plate_that_strays_stops_the_sheets_and_the_briefs(sheets, case):
    data, model, module, root, _ = sheets
    chapter = data['chapters'][0]
    chapter['deliverable'] = 'A one-page question list with dated sources, a named decision-maker and open questions.'
    plate = {'name': 'A one-page question list', 'parts': ['dated sources', 'a named decision-maker', 'open questions']}
    if case == 'missing-word':plate['parts'].append('a budget')
    elif case == 'part-inside-word':plate['parts'][0] = 'dated source'
    elif case == 'one-part':plate['parts'] = ['dated sources']
    elif case == 'no-parts':plate['parts'] = []
    elif case == 'duplicate':plate['parts'].append('dated sources')
    else:plate['note'] = 'not allowed'
    chapter['plate'] = plate
    mod = module()
    with pytest.raises(ValueError):
        mod.brief_sheets(str(root), model)
    with pytest.raises(ValueError):
        mod.chapter_briefs(str(root), model)


@pytest.mark.parametrize('steps', [False, True], ids=['plain', 'stepped'])
def test_the_sheet_carries_the_guide_plate_and_credits_stepped_geometry_only(sheets, steps):
    data, model, module, root, art = sheets
    data['chapters'][0]['deliverable'] = 'A one-page question list with dated sources and open questions.'
    data['chapters'][0]['plate'] = {'name': 'A one-page question list', 'parts': ['dated sources', 'open questions']}
    data['chapters'][1]['deliverable'] = 'A permission question, with identifying details kept out of public material.'
    data['chapters'][1]['plate'] = {'name': 'A permission question', 'parts': [],
                                    'kept_out': 'identifying details kept out of public material'}
    art.ART_STEPS = steps
    mod = module()
    first, second = [html for _, _, html in mod.brief_sheets(str(root), model)]
    plates = [n for n in tree(first).walk() if 'pw-plate' in classes(n)]
    assert len(plates) == 1 and plates[0].attrs.get('aria-hidden') == 'true'
    assert plates[0].attrs.get('data-origin') == 'zotheos-original'
    assert ('zth-steps' if steps else 'zth-plain') in classes(plates[0])
    assert [n.text for n in plates[0].walk() if n.tag == 'li'] == ['dated sources', 'open questions']
    # The sheet's plate is the guide's plate, byte for byte.
    assert art.plate(data['chapters'][0]['plate']) in first
    assert first.count(CREDIT) == (1 if steps else 0)
    kept = tree(second)
    assert not [n for n in kept.walk() if 'pw-plate-parts' in classes(n)]
    assert 'Privacy Rule' in kept.text and 'identifying details kept out of public material' in kept.text
    assert first.index('Something You Can Prepare</h2>') < first.index('pw-plate') < first.index('class="pw-plate-caption" data-line>')


def test_sheet_styles_are_flat_and_still():
    css = re.sub(r'/\*.*?\*/', '', (REPO / 'tools/nations/partials/nations.css').read_text(encoding='utf8'), flags=re.S)
    ours = [(sel, body) for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css) if re.search(r'\.(brief-|bs-|pw-sheet)', sel)]
    assert len(ours) > 20
    for sel, body in ours:
        for bad in ('gradient', 'shadow', 'filter', 'blur', 'transition', 'opacity', 'color-mix', 'rgba'):
            assert bad not in body, (sel, bad)
        for value in re.findall(r'animation\s*:\s*([^;]+)', body):
            assert value.strip() == 'none', sel
    title = [b for s, b in ours if 'bs-title' in s and 'print' not in s][0]
    assert 'background:none' in title and 'animation:none' in title, 'the sheet title is one flat ink in every theme'


def test_headings_read_as_words_and_addresses_wrap_only_at_slashes(sheets):
    data, model, module, root, _ = sheets
    mod = module()
    cid, _, html = mod.brief_sheets(str(root), model)[0]
    doc = tree(html)
    heads = [n for n in doc.walk() if n.tag == 'h2']
    assert [h.text for h in heads] == ['Something You Can Prepare', 'Who Decides And What To Verify', 'Reflection', 'Sources And Dates']
    assert all(h.attrs.get('data-case') == 'upper' for h in heads)
    guide = [n for n in doc.walk() if 'bs-guide' in classes(n)][0]
    kept = [n.text for n in guide.walk() if 'bs-nw' in classes(n)]
    assert 'paths-to-action' in kept and '#pw-' + cid in kept
    assert re.search(r'<a href="/nations/paths-to-action#pw-[^"]+"><span class="bs-url">https:/<wbr>/<wbr>zotheos\.org/<wbr>nations/<wbr>', html)


def test_the_guide_note_sits_between_the_download_and_the_sheet_link(sheets):
    data, model, module, root, _ = sheets
    mod = module()
    doc = tree(mod.render(str(root), model))
    for c in data['chapters']:
        result = [n for n in doc.walk() if 'pw-result' in classes(n) and ('pw-prepare-' + c['id']) in
                  [k.attrs.get('id') for k in n.children if hasattr(k, 'tag')]][0]
        kids = [k for k in result.children if hasattr(k, 'tag')]
        names = [k.attrs.get('class', k.tag) for k in kids]
        assert names[-3:] == ['pw-chapter-download', 'pw-download-note', 'pw-sheet']
        link = kids[-1]
        assert link.attrs['href'] == '/nations/brief/' + c['id'] and link.text == mod.SHEET_LINK
        assert link.attrs['aria-label'] == mod.SHEET_LINK + ': ' + c['title']
