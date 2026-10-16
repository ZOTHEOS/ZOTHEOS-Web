"""Independent supplemental prebuild cases. Fixtures are not historical claims."""
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit, parse_qs

import pytest

R=Path(os.environ.get('ZOTHEOS_TEST_REPO',r'C:\ZOTHEOS-Web'))
sys.path.insert(0,str(R/'tools/tests'))
from theater_acceptance_v1_helpers import DOM,fixture_build,fictional_catalog

def fixture_records(catalog,count):
    first=copy.deepcopy(catalog['films'][0])
    catalog['films']=[]
    for i in range(count):
        film=copy.deepcopy(first)
        film.update(id='fixture-'+str(i),title='Fictional Record '+str(i),
                    watch_url='https://publisher.example.test/story/'+str(i))
        catalog['films'].append(film)
    catalog['featured']=catalog['films'][0]['id']
    return catalog

def output(tmp_path,catalog):
    run=fixture_build(tmp_path,catalog)
    assert run.returncode==0,run.stdout+run.stderr
    return DOM((tmp_path/'theater.html').read_text(encoding='utf-8'))

def test_two_hundred_native_sources_remain_discoverable_without_javascript(tmp_path,fictional_catalog):
    d=output(tmp_path,fixture_records(fictional_catalog,200))
    cards=[e for e in d.elements if 'data-theater-film' in e.attrs]
    assert len(cards)==200
    for film,card in zip(fictional_catalog['films'],cards):
        assert 'hidden' not in card.attrs,'Pagination must enhance the static page, not remove no-JS access'
        links=[e for e in card.descendants() if e.tag=='a']
        assert any(e.attrs.get('href')==film['watch_url'] for e in links)
        assert any(e.tag=='h3' and film['title'] in e.text for e in card.descendants())
    frames=[e for e in d.elements if e.tag=='iframe']
    assert len(frames)==1,'No preloaded frame per card'

def test_optional_unindexed_geography_is_not_silently_us_based(tmp_path,fictional_catalog):
    d=output(tmp_path,fictional_catalog)
    card=next(e for e in d.elements if 'data-theater-film' in e.attrs)
    assert card.attrs.get('data-region')=='unindexed'
    assert card.attrs.get('data-location','')==''

@pytest.mark.parametrize('field,value',[
    ('region',''),('region',[]),('region','north-america<script>'),
    ('location',None),('location',' '),('location',{'text':'Unknown'}),
    ('form',None),('form',''),('form',['documentary']),
])
def test_present_invalid_geography_and_form_values_fail_closed(tmp_path,fictional_catalog,field,value):
    fictional_catalog['films'][0][field]=value
    run=fixture_build(tmp_path,fictional_catalog)
    assert run.returncode!=0 and not (tmp_path/'theater.html').exists()

@pytest.mark.parametrize('region',['north-america','central-america-caribbean','south-america','arctic','africa','asia','oceania','europe','global','unindexed'])
def test_distinct_world_regions_survive_the_real_renderer(tmp_path,fictional_catalog,region):
    film=fictional_catalog['films'][0]
    film.update(region=region,location='Fictional Place <img src=x onerror=bad()>',form='documentary')
    d=output(tmp_path,fictional_catalog)
    card=next(e for e in d.elements if 'data-theater-film' in e.attrs)
    assert card.attrs.get('data-region')==region
    assert card.attrs.get('data-location')==film['location']
    assert film['location'] in card.text
    assert not any(e.tag=='img' and e.attrs.get('src')=='x' for e in d.elements)

@pytest.mark.parametrize('form',['documentary','animation','drama','talk','news','other'])
def test_form_and_viewing_scope_are_distinct_metadata(tmp_path,fictional_catalog,form):
    film=fictional_catalog['films'][0]
    film.update(region='global',location='Fictional Place',form=form,viewing='trailer')
    d=output(tmp_path,fictional_catalog)
    card=next(e for e in d.elements if 'data-theater-film' in e.attrs)
    assert card.attrs.get('data-viewing')=='trailer'
    assert form.casefold() in card.text.casefold()

@pytest.mark.parametrize('key,value',[
    ('nfb_preview_slug','../preview'),('nfb_preview_slug','preview%2Fone'),
    ('nfb_preview_slug','preview?autoplay=1'),('nfb_preview_slug','x'*101),
    ('nfb_preview_type','feature'),('nfb_preview_type','trailer/other'),
])
def test_nfb_previews_cannot_escape_reviewed_route_shapes(tmp_path,fictional_catalog,key,value):
    film=fictional_catalog['films'][0]
    film.update(youtube_id=None,nfb_slug='fictional-film',nfb_preview_slug='fictional-preview',nfb_preview_type='trailer')
    film[key]=value
    run=fixture_build(tmp_path,fictional_catalog)
    assert run.returncode!=0 and not (tmp_path/'theater.html').exists()

@pytest.mark.parametrize('viewing',['full-film','official-page','short'])
def test_nfb_preview_requires_honest_trailer_or_excerpt_scope(tmp_path,fictional_catalog,viewing):
    fictional_catalog['films'][0].update(youtube_id=None,nfb_slug='fictional-film',
        nfb_preview_slug='fictional-preview',nfb_preview_type='trailer',viewing=viewing)
    run=fixture_build(tmp_path,fictional_catalog)
    assert run.returncode!=0 and not (tmp_path/'theater.html').exists()

@pytest.mark.parametrize('kind',['trailer','promo_clip'])
def test_nfb_explicit_preview_metadata_builds_only_the_exact_fixed_origin(tmp_path,fictional_catalog,kind):
    fictional_catalog['films'][0].update(youtube_id=None,nfb_slug='fictional-film',
        nfb_preview_slug='Fictional-Preview',nfb_preview_type=kind,viewing='excerpt')
    d=output(tmp_path,fictional_catalog)
    frame=next(e for e in d.elements if e.tag=='iframe')
    u=urlsplit(frame.attrs['src'])
    assert (u.scheme,u.netloc,u.path)==('https','www.nfb.ca','/film/fictional-film/'+kind+'/Fictional-Preview/embed/player/')
    assert parse_qs(u.query).get('autoplay')==['0']

def test_filters_and_paging_have_real_labels_and_native_buttons():
    d=DOM((R/'theater.html').read_text(encoding='utf-8'))
    for ident in ['theaterSearch','theaterTopic','theaterRegion','theaterViewing']:
        control,=d.by_id(ident)
        assert control.tag in ('input','select')
        assert any(e.tag=='label' and e.attrs.get('for')==ident and e.text.strip() for e in d.elements)
    for ident in ['theaterMore','theaterNext']:
        control,=d.by_id(ident)
        assert control.tag=='button' and control.attrs.get('type')=='button'
        assert control.text.strip()

def test_generated_privacy_no_longer_promises_removed_load_or_unload_controls():
    d=DOM((R/'theater.html').read_text(encoding='utf-8'))
    assert not re.search(r'\b(?:Unload Player|Load Player|Load YouTube Player|Load PBS Player)\b',d.root.text,re.I)
    privacy,=d.by_id('theater-privacy')
    assert 'automatically' in privacy.text.casefold()
    assert 'ip address' in privacy.text.casefold()

@pytest.mark.parametrize("fixture", ["theater-library-independent-regressions.cjs", "theater-library-provider-regressions.cjs", "theater-library-review-supplement.cjs"])
def test_supplemental_actual_script_contract(fixture):
    run=subprocess.run([r'C:\nvm4w\nodejs\node.exe',str(Path(__file__).with_name(fixture)),
                        str(R/'static/theater/theater.js')],capture_output=True,text=True,encoding='utf-8')
    assert run.returncode==0,run.stdout+run.stderr


def test_recorded_program_scope_is_distinct_and_no_script_controls_are_hidden(tmp_path,fictional_catalog):
    fictional_catalog['films'][0]['viewing']='recorded-program'
    d=output(tmp_path,fictional_catalog)
    card=next(e for e in d.elements if 'data-theater-film' in e.attrs)
    assert 'Recorded Program' in card.text and 'Full Film' not in card.text
    for ident in ['theaterNext','theaterMotion']:
        control,=d.by_id(ident)
        assert 'hidden' in control.attrs
    assert any(e.tag=='a' and e.attrs.get('href')==fictional_catalog['films'][0]['watch_url'] for e in d.elements)
