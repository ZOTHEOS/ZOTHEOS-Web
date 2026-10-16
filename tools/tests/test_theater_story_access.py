"""Independent rendered-output contract. Fictional films are never public claims."""
import copy
import json
import os
from pathlib import Path
import sys
import subprocess
import shutil
from urllib.parse import urlsplit

import pytest

R=Path(os.environ.get('ZOTHEOS_TEST_REPO',str(Path(__file__).resolve().parents[2])))
sys.path.insert(0,str(R/'tools/tests'))
from theater_acceptance_v1_helpers import DOM,fictional_catalog,fixture_build


def output(tmp_path,catalog):
    run=fixture_build(tmp_path,catalog)
    assert run.returncode==0,run.stdout+run.stderr
    return DOM((tmp_path/'theater.html').read_text(encoding='utf-8'))


def cards(dom):
    return [el for el in dom.elements if 'data-theater-film' in el.attrs]


def test_every_static_card_has_a_canonical_native_story_link_and_distinct_official_source(tmp_path,fictional_catalog):
    d=output(tmp_path,fictional_catalog)
    for card,film in zip(cards(d),fictional_catalog['films']):
        assert card.attrs.get('id')=='film-'+film['id']
        native=[el for el in card.descendants() if el.tag=='a' and el.attrs.get('href')=='/theater#film-'+film['id']]
        assert native,'Every cited story needs its own usable no-JS permalink'
        assert all(el.text.strip() or el.attrs.get('aria-label','').strip() for el in native)
        assert any(el.tag=='a' and el.attrs.get('href')==film['watch_url'] for el in card.descendants())
        assert 'hidden' not in card.attrs,'No-JS visitors must still reach every card'


def test_selected_story_link_is_native_canonical_and_not_a_copy_only_script_button(tmp_path,fictional_catalog):
    d=output(tmp_path,fictional_catalog)
    link,=d.by_id('theaterPermalink')
    assert link.tag=='a'
    assert link.attrs.get('href')=='/theater#film-'+fictional_catalog['featured']
    assert link.text.strip() or link.attrs.get('aria-label','').strip()


def test_static_featured_iframe_is_noscript_only_so_a_link_does_not_contact_the_wrong_provider(tmp_path,fictional_catalog):
    d=output(tmp_path,fictional_catalog)
    frames=[el for el in d.elements if el.tag=='iframe']
    assert frames,'Retain a useful no-JS featured player alongside native official links'
    for frame in frames:
        ancestor=frame.parent
        while ancestor is not None and ancestor.tag!='noscript':
            ancestor=ancestor.parent
        assert ancestor is not None,'An active static featured iframe contacts the wrong provider before a story hash can be resolved'
        assert urlsplit(frame.attrs.get('src','')).scheme=='https'


def test_access_facet_has_a_native_label_and_honest_non_guarantee_copy(tmp_path,fictional_catalog):
    d=output(tmp_path,fictional_catalog)
    access,=d.by_id('theaterAccess')
    assert access.tag=='select'
    label=next((el for el in d.elements if el.tag=='label' and el.attrs.get('for')=='theaterAccess'),None)
    assert label is not None and label.text.strip()
    choices={el.attrs.get('value'):el.text for el in access.descendants() if el.tag=='option'}
    assert choices=={'all':'All Sources','watch-here':'Watch Here','official-site':'Official Site'}
    assert any(word in d.root.text.casefold() for word in ['restrictions','regional availability','availability can change'])
    assert 'guaranteed playback' not in d.root.text.casefold()


def test_story_ids_are_static_targets_and_titles_remain_escaped(tmp_path,fictional_catalog):
    fictional_catalog['films'][0]['title']='Fictional <img src=x onerror=bad()> & "Story"'
    d=output(tmp_path,fictional_catalog)
    assert fictional_catalog['films'][0]['title'] in d.root.text
    assert not any(el.tag=='img' and el.attrs.get('src')=='x' for el in d.elements)
    story,=d.by_id('film-'+fictional_catalog['featured'])
    assert story.attrs.get('data-theater-film')==fictional_catalog['featured']


def test_all_two_hundred_story_targets_are_reachable_before_javascript(tmp_path,fictional_catalog):
    film=copy.deepcopy(fictional_catalog['films'][0]);fictional_catalog['films']=[]
    for i in range(200):
        record=copy.deepcopy(film);record.update(id='fixture-'+str(i),title='Fictional Record '+str(i))
        fictional_catalog['films'].append(record)
    fictional_catalog['featured']='fixture-0'
    d=output(tmp_path,fictional_catalog)
    assert len(cards(d))==200
    for i in range(200):
        target,=d.by_id('film-fixture-'+str(i))
        assert 'hidden' not in target.attrs
        assert any(el.tag=='a' and el.attrs.get('href')=='/theater#film-fixture-'+str(i) for el in target.descendants())
    assert len([el for el in d.elements if el.tag=='iframe'])==1


@pytest.mark.parametrize('bad_id',['../record','x#film-other','x?autoplay=1','x<script>','x%2Fother'])
def test_malformed_record_ids_fail_closed_before_story_links_are_rendered(tmp_path,fictional_catalog,bad_id):
    fictional_catalog['films'][0]['id']=bad_id;fictional_catalog['featured']=bad_id
    run=fixture_build(tmp_path,fictional_catalog)
    assert run.returncode!=0 and not (tmp_path/'theater.html').exists()


def test_actual_script_story_and_access_contract():
    node=shutil.which('node')
    assert node, 'Node.js is required for the real-script interaction contract'
    run=subprocess.run([node,str(Path(__file__).with_name('theater-story-access-acceptance.cjs')),str(R/'static/theater/theater.js')],capture_output=True,text=True,encoding='utf8')
    assert run.returncode==0,run.stdout+run.stderr
