"""Something You Can Prepare plates (Living Gallery, Batch 1, piece 2) on /nations/paths-to-action.

Fictional catalogue data exercises the real renderer; the last tests read the real catalogue and stylesheet source.
These cases check that every word on a plate is the deliverable's own, that nothing on a plate can be focused,
filled in or submitted, that held chapters stay held, and that the art never animates or blurs. They do not certify
design quality, permission or real-world outcomes.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

import pytest

REPO = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(REPO / 'tools/tests'))
sys.path.insert(0, str(REPO / 'tools'))
from test_indigenous_pathways import fixture_catalogue, fixture_model, tree  # noqa: E402

LAND = 'A source-linked land-and-water brief with one requested decision, its decision-maker, evidence gaps and a verified next date.'
LAND_PLATE = {'name': 'A source-linked land-and-water brief',
              'parts': ['one requested decision', 'its decision-maker', 'evidence gaps', 'a verified next date']}
PRIVATE = ('A private question list and document index for a qualified adviser, with verified dates and identifying '
           'information kept out of public material.')
PRIVATE_PLATE = {'name': 'A private question list and document index for a qualified adviser', 'parts': [],
                 'kept_out': 'identifying information kept out of public material'}


@pytest.fixture
def plates(tmp_path, monkeypatch):
    data, model = fixture_catalogue(), fixture_model()
    data['chapters'][0]['deliverable'] = LAND
    data['chapters'][0]['plate'] = copy.deepcopy(LAND_PLATE)
    data['chapters'][1]['deliverable'] = PRIVATE
    data['chapters'][1]['plate'] = copy.deepcopy(PRIVATE_PLATE)
    path = tmp_path / 'data/nations/pathways.json'
    path.parent.mkdir(parents=True)
    art = importlib.import_module('zth_art')
    shipped = art.ART_STEPS

    def call(kind='render', steps=None):
        path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf8')
        monkeypatch.setattr(art, 'ART_STEPS', shipped if steps is None else steps)
        spec = importlib.util.spec_from_file_location('pathway_plates_contract', REPO / 'tools/nations_pathways.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if kind == 'module':
            return module
        fn = {'render': module.render, 'all': module.chapter_briefs, 'shared': module.action_brief}[kind]
        return fn(tmp_path, model)
    return data, model, call


def classes(node):
    return node.attrs.get('class', '').split()


def plates_in(doc):
    return [n for n in doc.walk() if 'pw-plate' in classes(n)]


def chapter_sections(doc):
    return [n for n in doc.walk() if n.tag == 'section' and 'pw-chapter' in classes(n)]


def test_each_chapter_with_a_plate_shows_exactly_one_and_others_show_none(plates):
    data, _, call = plates
    del data['chapters'][1]['plate']
    sections = chapter_sections(tree(call()))
    assert len(sections) == 2
    assert len(plates_in(sections[0])) == 1 and plates_in(sections[1]) == []
    results = [n for n in sections[1].walk() if 'pw-result' in classes(n)]
    assert len(results) == 1 and 'pw-with-plate' not in classes(results[0])
    assert data['chapters'][1]['deliverable'] in results[0].text


def test_plate_words_are_the_deliverable_own_words_in_order(plates):
    data, _, call = plates
    doc = tree(call())
    first = plates_in(doc)[0]
    name = [n for n in first.walk() if 'pw-plate-name' in classes(n)][0].text
    parts = [n.text for n in first.walk() if n.tag == 'li']
    assert name == LAND_PLATE['name'] and parts == LAND_PLATE['parts']
    kept_whole = [n.text for n in first.walk() if 'pw-plate-nw' in classes(n)]
    assert kept_whole == ['source-linked', 'land-and-water', 'decision-maker']
    position = 0
    for word in [name, *parts]:
        found = re.compile(r"(?<![\w'’-])" + re.escape(word) + r"(?![\w'’-])").search(LAND, position)
        assert found, word
        position = found.end()


@pytest.mark.parametrize('case', [
    'wrong-case', 'inside-a-word', 'inside-a-hyphenated-word', 'out-of-order', 'not-in-sentence', 'duplicate-part',
    'one-part', 'nine-parts', 'kept-out-with-parts', 'no-parts-no-kept-out', 'unknown-key', 'missing-parts',
    'not-a-dict', 'part-not-text', 'padded-word', 'kept-out-not-in-sentence', 'name-after-parts', 'control-character',
    'overlong-compound'])
def test_a_plate_that_strays_from_the_deliverable_stops_every_output(plates, case):
    data, _, call = plates
    land, private = data['chapters'][0], data['chapters'][1]
    p = land['plate']
    if case == 'wrong-case': p['parts'][0] = 'One requested decision'
    elif case == 'inside-a-word': p['parts'][2] = 'evidence gap'
    elif case == 'inside-a-hyphenated-word': p['parts'][1] = 'decision'
    elif case == 'out-of-order': p['parts'][0], p['parts'][1] = p['parts'][1], p['parts'][0]
    elif case == 'not-in-sentence': p['parts'][3] = 'a promised outcome'
    elif case == 'duplicate-part': p['parts'][3] = p['parts'][2]
    elif case == 'one-part': p['parts'] = p['parts'][:1]
    elif case == 'nine-parts': p['parts'] = ['a'] * 9
    elif case == 'kept-out-with-parts': private['plate']['parts'] = ['verified dates']
    elif case == 'no-parts-no-kept-out': p['parts'] = []
    elif case == 'unknown-key': p['example'] = 'A Nation name'
    elif case == 'missing-parts': del p['parts']
    elif case == 'not-a-dict': land['plate'] = ['A source-linked land-and-water brief']
    elif case == 'part-not-text': p['parts'][0] = 7
    elif case == 'padded-word': p['parts'][0] = ' one requested decision'
    elif case == 'kept-out-not-in-sentence': private['plate']['kept_out'] = 'names kept private'
    elif case == 'name-after-parts': p['name'] = 'evidence gaps'; p['parts'] = ['one requested decision', 'its decision-maker']
    elif case == 'overlong-compound':
        land['deliverable'] = LAND.replace('land-and-water', 'land-and-water-and-coastal-sea')
        p['name'] = 'A source-linked land-and-water-and-coastal-sea brief'
    else: p['parts'][0] = 'one requested\x00decision'
    for kind in ['render', 'all', 'shared']:
        with pytest.raises(ValueError):
            call(kind)


def test_a_held_chapter_is_still_checked_and_shows_no_plate(plates):
    data, model, call = plates
    data['sources'][0]['nation'] = 'fixture-nation'
    model.by_id.clear()
    html = call()
    assert LAND_PLATE['name'] not in html and 'one requested decision' not in html
    assert len(plates_in(tree(html))) == 1
    data['chapters'][0]['plate']['parts'][0] = 'a promised outcome'
    with pytest.raises(ValueError):
        call()


def test_the_privacy_plate_shows_its_rule_and_no_part_rows(plates):
    _, _, call = plates
    private = plates_in(tree(call()))[1]
    assert not [n for n in private.walk() if n.tag in {'ul', 'ol', 'li'}]
    kept = [n for n in private.walk() if 'pw-plate-kept' in classes(n)]
    assert len(kept) == 1
    assert [c.text for c in kept[0].children if hasattr(c, 'tag')] == ['Privacy Rule', PRIVATE_PLATE['kept_out']]
    # The label must not repeat the phrase it introduces ("Kept Out ... kept out of").
    assert 'kept out' not in 'Privacy Rule'.lower()
    assert 'pw-plate-private' in classes(private) and 'pw-plate-private' not in classes(plates_in(tree(call()))[0])


def test_the_sentence_and_its_one_download_stay_beside_the_plate(plates):
    data, _, call = plates
    doc = tree(call())
    for chapter, section in zip(data['chapters'], chapter_sections(doc)):
        result = [n for n in section.walk() if 'pw-result' in classes(n)][0]
        assert 'pw-with-plate' in classes(result)
        captions = [n for n in result.walk() if 'pw-plate-caption' in classes(n)]
        assert len(captions) == 1 and captions[0].text == chapter['deliverable']
        kids = [c for c in result.children if hasattr(c, 'tag')]
        order = [('pw-plate' in classes(k)) and 'plate' or ('pw-plate-caption' in classes(k)) and 'caption' or k.tag for k in kids]
        assert order[:4] == ['h3', 'plate', 'caption', 'a'], order
        assert kids[0].attrs.get('id') == 'pw-prepare-' + chapter['id'], 'the Prepare A Brief shortcut still lands on the heading'
        downloads = [n for n in result.walk() if n.tag == 'a' and n.attrs.get('href', '').endswith('.txt')]
        assert len(downloads) == 1 and downloads[0].attrs['href'] == '/static/nations/action-brief-' + chapter['id'] + '.txt'


def test_a_plate_is_hidden_art_that_cannot_be_focused_filled_or_submitted(plates):
    _, _, call = plates
    html = call()
    for plate in plates_in(tree(html)):
        assert plate.attrs.get('aria-hidden') == 'true' and plate.attrs.get('data-origin') == 'zotheos-original'
        assert len({'zth-plain', 'zth-steps'} & set(classes(plate))) == 1
        for node in plate.walk():
            assert node.tag not in {'a', 'button', 'input', 'textarea', 'select', 'form', 'label', 'svg', 'img', 'script',
                                    'iframe', 'details', 'summary'}
            assert 'tabindex' not in node.attrs and 'href' not in node.attrs and 'style' not in node.attrs
            assert not any(k.startswith('on') for k in node.attrs)
    assert not re.search(r'\bon\w+\s*=', html, re.I)


def test_plate_text_is_escaped(plates):
    data, _, call = plates
    attack = '<img src=x onerror=alert(1)>'
    data['chapters'][0]['deliverable'] = 'A ' + attack + ' brief with one requested decision and its decision-maker.'
    data['chapters'][0]['plate'] = {'name': 'A ' + attack + ' brief', 'parts': ['one requested decision', 'its decision-maker']}
    html = call()
    assert '&lt;img' in html and not [n for n in tree(html).walk() if n.tag in {'img', 'svg'}]


def test_one_switch_sets_the_variant_and_only_the_climb_carries_the_credit(plates):
    _, _, call = plates
    plain, steps = call(steps=False), call(steps=True)
    credit = 'Original project geometry by ZOTHEOS. It has no traditional or ceremonial meaning.'
    assert 'zth-steps' not in plain and credit not in plain
    assert 'zth-plain' not in steps and steps.count(credit) == 1
    plain_plates = [p for p in plates_in(tree(plain)) if p.tag == 'div']
    steps_plates = [p for p in plates_in(tree(steps)) if p.tag == 'div']
    assert len(plain_plates) == len(steps_plates) == 2
    assert all('zth-plain' in classes(p) for p in plain_plates) and all('zth-steps' in classes(p) for p in steps_plates)
    # The one credit line on the page lives in the Climb's caption (piece 1), never under a plate.
    for section in chapter_sections(tree(steps)):
        assert credit not in section.text
    assert call('module').A.ART_STEPS is False, 'the plain variant ships until the Roots decision'


def test_the_note_under_the_download_says_the_file_is_a_blank_aid(plates):
    data, _, call = plates
    mod = call('module')
    doc = tree(call())
    notes = [n.text for n in doc.walk() if 'pw-download-note' in classes(n)]
    assert notes == [mod.DOWNLOAD_NOTE] * len(data['chapters'])
    # A chapter without a plate keeps the note it had.
    del data['chapters'][1]['plate']
    notes = [n.text for n in tree(call()).walk() if 'pw-download-note' in classes(n)]
    assert notes == [mod.DOWNLOAD_NOTE, 'Plain text. One pathway. Fill offline in a place you control.']
    assert 'Blank' in mod.DOWNLOAD_NOTE and 'One pathway' not in mod.DOWNLOAD_NOTE


def test_the_published_catalogue_gives_every_chapter_a_true_plate():
    data = json.loads((REPO / 'data/nations/pathways.json').read_text(encoding='utf-8'))
    spec = importlib.util.spec_from_file_location('pathway_plates_catalogue', REPO / 'tools/nations_pathways.py')
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO / 'tools'))
    spec.loader.exec_module(module)
    for chapter in data['chapters']:
        assert 'plate' in chapter, chapter['id']
        module.plate(chapter['plate'], chapter['deliverable'])
    families = next(c for c in data['chapters'] if c['id'] == 'children-and-families')
    assert families['plate']['parts'] == [] and families['plate']['kept_out']


def plate_rules(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    rules = []
    for match in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
        selector, body = match.group(1).strip(), match.group(2)
        if re.search(r'\.(pw-plate|zth-plain|zth-steps|pw-with-plate)', selector):
            rules.append((selector, body))
    return rules


def test_plate_art_is_flat_static_and_crisp_in_the_stylesheet_source():
    css = (REPO / 'tools/nations/partials/nations.css').read_text(encoding='utf-8')
    rules = plate_rules(css)
    assert len(rules) >= 10
    banned = re.compile(r'gradient|shadow|filter|blur|opacity|animation|transition|(?<!text-)transform|border-radius|'
                        r'rgba|color-mix|url\(|image|mask|clip', re.I)
    for selector, body in rules:
        assert not banned.search(body), (selector, body)
        for number in re.findall(r'(-?\d*\.\d+)px', body):
            pytest.fail(f'fractional pixel {number}px in {selector}')
    accents = [s for s, b in rules if 'cochineal' in b or 'gold' in b]
    assert accents == [], 'Plates are drawn in ink only; the accent is kept for selection marks.'
    # No stepped CSS ships until the Roots decision, and part markers are never a stair mark.
    assert not [s for s, _ in rules if 'zth-steps' in s]
    # The plate name is set in the reading sans, never the display serif (whose thin hyphen reads as a dash).
    name = [b for s, b in rules if s.strip() == '.pw-plate-name']
    assert name and 'var(--zn-read)' in name[0] and 'serif' not in name[0]


def test_the_committed_guide_shows_one_true_plate_per_public_chapter():
    """The page as built: one plate per chapter, each one's words in its sentence, and pathway 06 without part rows."""
    module = importlib.util.module_from_spec(spec := importlib.util.spec_from_file_location('plates_built', REPO / 'tools/nations_pathways.py'))
    spec.loader.exec_module(module)
    catalogue = {c['id']: c for c in json.loads((REPO / 'data/nations/pathways.json').read_text(encoding='utf-8'))['chapters']}
    doc = tree((REPO / 'nations/paths-to-action.html').read_text(encoding='utf-8'))
    sections = chapter_sections(doc)
    assert sections
    for section in sections:
        cid = section.attrs['aria-labelledby'][3:]
        found = [p for p in plates_in(section) if p.tag == 'div']
        assert len(found) == 1, cid
        caption = [n for n in section.walk() if 'pw-plate-caption' in classes(n)]
        assert caption[0].text == catalogue[cid]['deliverable']
        if catalogue[cid]['plate'].get('kept_out'):
            assert not [n for n in found[0].walk() if n.tag == 'li']
