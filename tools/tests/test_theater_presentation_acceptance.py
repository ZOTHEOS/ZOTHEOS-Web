"""Independent presentation contract. Fictional records are not film research.

Exercise the actual builder and default production page, plus real-script focus
and privacy behavior. CSS structure is only a preliminary gate; actual 320/390
phone and desktop layout still requires browser inspection.
"""
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', r'C:\ZOTHEOS-Web'))
sys.path.insert(0, str(ROOT / 'tools/tests'))
from theater_acceptance_v1_helpers import DOM, fixture_build, fictional_catalog


def build(tmp_path, data):
    run = fixture_build(tmp_path, data)
    assert run.returncode == 0, run.stdout + run.stderr
    return DOM((tmp_path / 'theater.html').read_text(encoding='utf-8'))


def one(dom, ident):
    nodes = dom.by_id(ident)
    assert len(nodes) == 1, ident + ' must be a unique usable target'
    return nodes[0]


def concealed(node):
    while node is not None:
        if 'hidden' in node.attrs or node.attrs.get('aria-hidden') == 'true':
            return True
        if node.tag == 'details' and 'open' not in node.attrs:
            return True
        node = node.parent
    return False


def normalized(text):
    return ' '.join(text.replace('–', '-').replace('—', ', ').split())


def featured(data):
    return next(f for f in data['films'] if f['id'] == data['featured'])


@pytest.mark.parametrize('ident,key', [('theaterCredits', 'credits'), ('theaterContentNote', 'content_note')])
def test_creators_and_before_watching_are_visible_before_the_screen(tmp_path, fictional_catalog, ident, key):
    d = build(tmp_path, fictional_catalog)
    node, screen = one(d, ident), one(d, 'theaterPlayer')
    assert normalized(featured(fictional_catalog)[key]) == node.text
    assert not concealed(node), 'Essential context must not require opening Sources'
    assert d.elements.index(node) < d.elements.index(screen), 'Read the makers and content note before reaching the player'


def test_before_watching_note_has_a_visible_human_readable_label(tmp_path, fictional_catalog):
    d = build(tmp_path, fictional_catalog)
    note = one(d, 'theaterContentNote')
    ancestor = note.parent
    assert ancestor is not None and 'before watching' in ancestor.text.casefold()
    assert not concealed(ancestor)


def test_featured_publisher_is_exposed_as_data_not_only_inside_search(tmp_path, fictional_catalog):
    fictional_catalog['films'][0]['publisher'] = 'Fictional Publisher <review> & Partners'
    d = build(tmp_path, fictional_catalog)
    publisher = one(d, 'theaterPublisher')
    assert publisher.text == featured(fictional_catalog)['publisher']
    assert not concealed(publisher)
    assert not any(e.tag == 'review' for e in d.elements)


def test_supplied_perspective_is_attributed_and_never_invented(tmp_path, fictional_catalog):
    film = featured(fictional_catalog)
    film['perspective'] = 'Fictional publisher identifies the participants; no universal representation is claimed.'
    d = build(tmp_path, fictional_catalog)
    node = one(d, 'theaterPerspective')
    assert node.text == film['perspective']
    assert not concealed(node)
    card = one(d, 'film-' + film['id'])
    assert card.attrs.get('data-perspective') == film['perspective']


def test_absent_perspective_does_not_become_a_synthesized_identity_claim(tmp_path, fictional_catalog):
    for film in fictional_catalog['films']:
        film.pop('perspective', None)
    d = build(tmp_path, fictional_catalog)
    nodes = d.by_id('theaterPerspective')
    assert not nodes or all(not e.text.strip() or concealed(e) for e in nodes)


@pytest.mark.parametrize('field', ['title', 'credits', 'publisher', 'content_note', 'perspective'])
def test_selected_metadata_is_escaped_without_dropping_its_meaning(tmp_path, fictional_catalog, field):
    film = featured(fictional_catalog)
    film[field] = 'Fictional <img src=x onerror=bad()> & "review"'
    d = build(tmp_path, fictional_catalog)
    target = {'title':'theaterTitle', 'credits':'theaterCredits', 'publisher':'theaterPublisher',
              'content_note':'theaterContentNote', 'perspective':'theaterPerspective'}[field]
    assert one(d, target).text == film[field]
    assert not any(e.tag == 'img' and e.attrs.get('src') == 'x' for e in d.elements)


def test_back_to_collection_is_a_native_anchor_and_recovery_heading_is_focusable(tmp_path, fictional_catalog):
    d = build(tmp_path, fictional_catalog)
    back = one(d, 'theaterBack')
    assert back.tag == 'a' and back.attrs.get('href') == '#collection'
    assert 'collection' in back.text.casefold() and not concealed(back)
    assert one(d, 'collection-heading').attrs.get('tabindex') == '-1'


@pytest.mark.parametrize('provider,value', [('youtube_id','abcdefghijk'), ('vimeo_id','141218300'),
                                          ('pbs_id','3109669877'), ('nfb_slug','fictional_story')])
def test_each_provider_has_one_no_script_player_and_a_real_official_fallback(tmp_path, fictional_catalog, provider, value):
    film = featured(fictional_catalog)
    for key in ['youtube_id', 'vimeo_id', 'pbs_id', 'nfb_slug']:
        film.pop(key, None)
    film[provider] = value
    d = build(tmp_path, fictional_catalog)
    frames = [e for e in d.elements if e.tag == 'iframe']
    assert len(frames) == 1
    frame = frames[0]
    assert frame.parent.tag == 'noscript', 'No active wrong-provider frame before a #film link resolves'
    query = parse_qs(urlsplit(frame.attrs['src']).query)
    assert query.get('autoplay') == ['0']
    assert 'enablejsapi' not in query
    assert not re.search(r'(^|;)\s*autoplay\b', frame.attrs.get('allow', ''))
    assert one(d, 'theaterWatch').attrs.get('href') == film['watch_url']


def test_source_only_story_has_no_substitute_player_and_honest_fallback(tmp_path, fictional_catalog):
    film = featured(fictional_catalog)
    for key in ['youtube_id', 'vimeo_id', 'pbs_id', 'nfb_slug']:
        film.pop(key, None)
    film['viewing'] = 'official-page'
    d = build(tmp_path, fictional_catalog)
    assert not [e for e in d.elements if e.tag == 'iframe']
    assert 'hidden' in one(d, 'theaterPlayer').attrs
    assert one(d, 'theaterWatch').attrs.get('href') == film['watch_url']
    assert 'official source' in one(d, 'theaterPlayerStatus').text.casefold()
    assert not re.search(r'\b(?:sound|captions|pause|play)\b', ' '.join(e.text for e in d.elements if e.tag == 'button' and not concealed(e) and e.attrs.get('aria-disabled') != 'true' and 'disabled' not in e.attrs), re.I)


def test_real_default_generated_page_declares_authorized_muted_preview_mode():
    d = DOM((ROOT / 'theater.html').read_text(encoding='utf-8'))
    html = next(e for e in d.elements if e.tag == 'html')
    assert html.attrs.get('data-preview-autoplay') == 'on', 'Owner explicitly selected Start Muted When In View'
    frames = [e for e in d.elements if e.tag == 'iframe']
    assert len(frames) == 1
    for e in d.elements:
        assert 'autoplay' not in e.attrs
        if e.tag == 'iframe':
            assert parse_qs(urlsplit(e.attrs['src']).query).get('autoplay') == ['0']
            assert 'enablejsapi' not in e.attrs['src'].casefold()
            assert not re.search(r'(^|;)\s*autoplay\b', e.attrs.get('allow', ''))
    text = d.root.text.casefold()
    assert 'without sound' in text or 'muted' in text
    assert 'in view' in text or 'in-view' in text
    assert 'ip address' in text or 'request information' in text


def test_actual_catalogue_titles_credits_sources_and_native_story_targets_are_lossless():
    data = json.loads((ROOT / 'data/theater/films.json').read_text(encoding='utf-8'))
    d = DOM((ROOT / 'theater.html').read_text(encoding='utf-8'))
    cards = [e for e in d.elements if 'data-theater-film' in e.attrs]
    assert len(cards) == len(data['films'])
    assert {e.attrs['data-theater-film'] for e in cards} == {f['id'] for f in data['films']}
    for film in data['films']:
        card = one(d, 'film-' + film['id'])
        assert 'hidden' not in card.attrs
        for key in ['title', 'credits', 'synopsis', 'availability', 'content_note']:
            assert normalized(film[key]) in card.text, (film['id'], key)
        links = [e.attrs.get('href') for e in card.descendants() if e.tag == 'a']
        assert film['watch_url'] in links and '/theater#film-' + film['id'] in links
        for source in film['sources']:
            assert source['url'] in links
            assert normalized(source['title']) in card.text and normalized(source['publisher']) in card.text
            assert any(e.tag == 'time' and e.attrs.get('datetime') == source['checked'] for e in card.descendants())


def test_appearance_effect_language_and_five_themes_survive_the_presentation_change():
    d = DOM((ROOT / 'theater.html').read_text(encoding='utf-8'))
    for ident in ['appearancePop', 'fxAmount', 'apLanguageRow', 'apReturnToFilm', 'site-translation', 'translateSection', 'translateText']:
        one(d, ident)
    themes = [e for e in d.elements if 'data-set' in e.attrs and e.tag == 'button']
    assert {e.attrs['data-set'] for e in themes} == {'','maya','codex','skeleton','calavera'}
    assert len(themes) == 5
    fx = one(d, 'fxAmount')
    assert fx.attrs.get('role') == 'radiogroup'
    assert {e.text for e in fx.descendants() if e.attrs.get('role') == 'radio'} == {'Light','Medium','Heavy'}
    assert one(d, 'translateText').attrs.get('href', '').startswith('https://translate.google.com/')
    assert any(e.tag == 'a' and e.attrs.get('href') == '#site-translation' for e in d.elements)


def test_native_frame_is_local_decorative_and_no_rendered_loop_is_silently_shipped():
    d = DOM((ROOT / 'theater.html').read_text(encoding='utf-8'))
    one(d, 'theaterStage')
    components = [e for e in d.elements if e.tag == 'script' and 'function ZtFrame(' in e.text and 'createElementNS' in e.text]
    assert len(components) == 1, 'One local original stepped frame component, as supplied by the package'
    assert not any(e.tag in {'video','audio','object','embed'} for e in d.elements)
    assert not any(e.tag == 'script' and e.attrs.get('src','').startswith(('http:', 'https:', '//')) for e in d.elements)


def test_responsive_structural_floor_and_touch_targets_require_followup_browser_gate():
    css = (ROOT / 'static/theater/theater.css').read_text(encoding='utf-8')
    d = DOM((ROOT / 'theater.html').read_text(encoding='utf-8'))
    viewport = [e for e in d.elements if e.tag == 'meta' and e.attrs.get('name') == 'viewport']
    assert len(viewport) == 1 and 'width=device-width' in viewport[0].attrs.get('content','')
    assert re.search(r'@media[^{}]*\(\s*max-width\s*:\s*(?:[4-9]\d\d|1\d\d\d)px\s*\)', css)
    assert re.search(r'min-(?:height|block-size)\s*:\s*(?:4[4-9]|[5-9]\d)px', css)
    assert 'overflow-wrap' in css and ('minmax(0,' in re.sub(r'\s+','',css) or 'min-width:0' in re.sub(r'\s+','',css))
    assert 'th-nw' in css


@pytest.mark.parametrize('scenario', [
    'initial-muted', 'viewport-gate', 'controls-gate', 'still', 'calm', 'os-reduced', 'no-intersection-observer',
    'held-note', 'held-audio', 'held-captions', 'source-only', 'nfb-native', 'vimeo-muted',
    'manual-pause', 'out-of-view', 'hidden-tab', 'phone-cap', 'desktop-cap', 'short-desktop-cap',
    'origin-reject', 'source-reject', 'sound-gesture', 'sound-report-truth', 'caption-off-truth',
    'return-focus', 'deep-link', 'caption-state', 'review-query-cannot-override'
])
def test_actual_preview_runtime_contract(scenario):
    node = Path(r'C:\nvm4w\nodejs\node.exe')
    companion = Path(__file__).with_name('theater-muted-preview-acceptance.cjs')
    run = subprocess.run([str(node), str(companion), str(ROOT), scenario], capture_output=True, text=True, encoding='utf-8')
    assert run.returncode == 0, run.stdout + run.stderr


def overlay_build(tmp_path, data, policy):
    """Run real CLI with an isolated source root so policy input is truly exercised."""
    for rel in ['tools/nations/partials', 'tools/theater', 'static/theater', 'static/appearance']:
        source = ROOT / rel
        if source.is_dir():
            shutil.copytree(source, tmp_path / rel, dirs_exist_ok=True)
    (tmp_path / 'tools').mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'tools/csp_sync.py', tmp_path / 'tools/csp_sync.py')
    target = tmp_path / 'data/theater'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'films.json').write_text(json.dumps(data), encoding='utf-8')
    (target / 'preview_policy.json').write_text(json.dumps(policy), encoding='utf-8')
    return subprocess.run([sys.executable, str(ROOT / 'tools/theater_build.py'), '--root', str(tmp_path),
                           '--source-root', str(tmp_path)], capture_output=True, text=True,
                          env={**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'})


def test_preview_hold_policy_is_binding_even_when_a_record_says_allow(tmp_path, fictional_catalog):
    film = featured(fictional_catalog)
    film['preview'] = 'allow'
    policy = {'version':1, 'records':{film['id']:{'state':'hold', 'reason':'Conflicting observations await source review.'}}}
    run = overlay_build(tmp_path, fictional_catalog, policy)
    assert run.returncode == 0, run.stdout + run.stderr
    d = DOM((tmp_path / 'theater.html').read_text(encoding='utf-8'))
    card = one(d, 'film-' + film['id'])
    assert card.attrs.get('data-preview', '').startswith('hold'), 'Hold wins over a curated allow flag'
    assert film['watch_url'] in [e.attrs.get('href') for e in card.descendants() if e.tag == 'a']


@pytest.mark.parametrize('policy', [
    {'version':True, 'records':{}},
    {'version':2, 'records':{}},
    {'version':1, 'records':[]},
    {'version':1, 'records':{'unknown-record':{'state':'hold','reason':'Review pending.'}}},
    {'version':1, 'records':{'fixture-river':{'state':'allow','reason':'Unsafe override.'}}},
    {'version':1, 'records':{'fixture-river':{'state':'hold','reason':''}}},
    {'version':1, 'records':{'fixture-river':{'state':'hold','reason':17}}},
    {'version':1, 'records':{'fixture-river':{'state':'hold','reason':'x'*2001}}},
    {'version':1, 'records':{'fixture-river':{'state':'hold','reason':'hidden\u0001control'}}},
    {'version':1, 'records':{'fixture-river':{'state':'hold','reason':'Review pending.','override':True}}},
])
def test_invalid_preview_policy_fails_closed_before_publication(tmp_path, fictional_catalog, policy):
    run = overlay_build(tmp_path, fictional_catalog, policy)
    assert run.returncode != 0 and not (tmp_path / 'theater.html').exists()


def test_yanuni_conflicting_caption_evidence_cannot_silently_become_an_automatic_preview():
    data = json.loads((ROOT / 'data/theater/films.json').read_text(encoding='utf-8'))
    d = DOM((ROOT / 'theater.html').read_text(encoding='utf-8'))
    film = next(f for f in data['films'] if f['id'] == 'yanuni')
    card = one(d, 'film-yanuni')
    assert card.attrs.get('data-preview', '').startswith('hold')
    assert film['watch_url'] in [e.attrs.get('href') for e in card.descendants() if e.tag == 'a']
