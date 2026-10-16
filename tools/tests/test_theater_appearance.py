"""Independent real-builder Appearance contract. Fictional films, no source fetches."""
from pathlib import Path
import os
import re
import sys

import pytest

R=Path(os.environ.get('ZOTHEOS_TEST_REPO',str(Path(__file__).resolve().parents[2])))
sys.path.insert(0,str(R/'tools/tests'))
from theater_acceptance_v1_helpers import DOM,fixture_build,fictional_catalog

@pytest.fixture
def rendered(tmp_path,fictional_catalog):
    result=fixture_build(tmp_path,fictional_catalog)
    assert result.returncode==0,result.stdout+result.stderr
    html=(tmp_path/'theater.html').read_text(encoding='utf8')
    return html,DOM(html)

def one(dom,id):
    nodes=dom.by_id(id);assert len(nodes)==1,id+' must occur exactly once'
    return nodes[0]

def test_theme_names_and_descriptions_match_the_actual_landing(rendered):
    _,dom=rendered;landing=DOM((R/'index.html').read_text(encoding='utf8'))
    source=one(landing,'appearancePop');actual=one(dom,'appearancePop')
    def choices(node):return [(x.attrs.get('data-set'),x.attrs.get('aria-label'),x.attrs.get('title')) for x in node.descendants() if x.attrs.get('role')=='radio' and 'data-set' in x.attrs]
    assert choices(actual)==choices(source)
    assert one(dom,'apThemeDescription').text==one(landing,'apThemeDescription').text

def test_motion_choices_and_roving_state_are_native_buttons(rendered):
    _,dom=rendered;group=one(dom,'motionGroup')
    radios=[x for x in group.descendants() if x.attrs.get('role')=='radio']
    assert [r.text for r in radios]==['Living','Calm','Still']
    assert all(r.tag=='button' and r.attrs.get('type')=='button' for r in radios)
    assert sum(r.attrs.get('tabindex')=='0' for r in radios)==1

def test_real_intensity_row_has_three_labelled_choices_and_idle_explanation(rendered):
    _,dom=rendered;group=one(dom,'fxAmount')
    assert group.attrs.get('role')=='radiogroup' and group.attrs.get('aria-labelledby')
    radios=[x for x in group.descendants() if x.attrs.get('role')=='radio']
    assert [(r.attrs.get('data-level'),r.text) for r in radios]==[('0','Light'),('1','Medium'),('2','Heavy')]
    assert all(r.tag=='button' and r.attrs.get('type')=='button' for r in radios)
    assert one(dom,'apFxNote').text and one(dom,'fxAmountRow')

def test_language_has_a_real_local_theater_destination_and_native_google_fallback(rendered):
    _,dom=rendered;row=one(dom,'apLanguageRow')
    assert any(a.tag=='a' and a.attrs.get('href')=='#site-translation' for a in row.descendants())
    panel=one(dom,'site-translation');assert panel.tag=='details'
    assert any(x.tag=='summary' and x.text for x in panel.descendants())
    select=one(dom,'translateSection');assert select.tag=='select'
    link=one(dom,'translateText')
    assert link.tag=='a' and link.attrs.get('href','').startswith('https://translate.google.com/')
    assert link.attrs.get('target')=='_blank' and {'noopener','noreferrer'}<=set(link.attrs.get('rel','').split())
    assert re.search(r'name|meaning',one(dom,'translationNote').text,re.I)

def test_final_action_returns_to_current_film_instead_of_replaying_a_nonexistent_intro(rendered):
    _,dom=rendered;control=one(dom,'apReturnToFilm')
    assert control.tag=='button' and control.attrs.get('type')=='button'
    assert 'film' in control.text.casefold()
    assert not dom.by_id('replayIntro')

def test_scoped_appearance_code_loads_after_shared_owner_before_player_code(rendered):
    html,dom=rendered;path=R/'static/theater/appearance.js'
    assert path.is_file(),'A scoped controller must not fork or replace the shared Theme/Motion owner.'
    shared=(R/'tools/nations/partials/appearance.js').read_text(encoding='utf8').strip()
    scoped=path.read_text(encoding='utf8').strip();player=(R/'static/theater/theater.js').read_text(encoding='utf8').strip()
    assert shared and scoped and player and html.index(shared)<html.index(scoped)<html.index(player)
    assert not [s for s in dom.elements if s.tag=='script' and s.attrs.get('src','').startswith('http')]

def test_native_official_sources_and_noscript_player_survive_appearance_change(rendered,fictional_catalog):
    _,dom=rendered
    hrefs={x.attrs.get('href') for x in dom.elements if x.tag=='a'}
    assert all(f['watch_url'] in hrefs for f in fictional_catalog['films'])
    for frame in [x for x in dom.elements if x.tag=='iframe']:
        node=frame.parent
        while node is not None and node.tag!='noscript':node=node.parent
        assert node is not None
        assert 'autoplay=0' in frame.attrs.get('src','')

def test_appearance_markup_does_not_duplicate_ids_or_remove_player_and_filter_hooks(rendered):
    _,dom=rendered;ids=[x.attrs['id'] for x in dom.elements if 'id' in x.attrs]
    assert len(ids)==len(set(ids))
    for id in ['appearanceBtn','appearancePop','navMenuBtn','theaterPlayer','theaterSearch','theaterTopic','theaterRegion','theaterViewing','theaterAccess','theaterPermalink','theaterMotion']:
        one(dom,id)

def test_privacy_copy_covers_the_real_intensity_preference_without_claiming_search_storage(rendered):
    _,dom=rendered;text=one(dom,'theater-privacy').text.casefold()
    assert 'intensity' in text and 'browser' in text
    assert re.search(r'(does not|never|not) save searches',text)
