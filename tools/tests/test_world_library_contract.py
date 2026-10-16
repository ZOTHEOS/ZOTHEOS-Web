"""Explicit worldwide-library revision. Actual output, fictional hostile inputs."""
import copy,json,sys,os,subprocess
from pathlib import Path
import pytest
R=Path(os.environ.get('ZOTHEOS_TEST_REPO',r'C:\ZOTHEOS-Web'))
sys.path.insert(0,str(R/'tools/tests'))
from theater_acceptance_v1_helpers import DOM,fixture_build,fictional_catalog

def test_player_controls_are_native_play_pause_without_an_unload_option():
    d=DOM((R/'theater.html').read_text(encoding='utf-8'))
    assert not d.by_id('theaterClose') and not d.by_id('theaterLoad')
    assert 'unload player' not in d.root.text.casefold()

def test_worldwide_facets_paging_and_coverage_routes_are_real():
    d=DOM((R/'theater.html').read_text(encoding='utf-8'))
    assert d.by_id('theaterRegion') and d.by_id('theaterViewing') and d.by_id('theaterMore')
    assert any(e.tag=='a' and e.attrs.get('href')=='/nations/directory' for e in d.elements)
    assert 'worldwide' in d.root.text.casefold()
    assert d.by_id('regional-resources'), 'Colorado companions remain regional, not worldwide stand-ins'

def test_home_and_nations_navigation_showcase_theater():
    for path in ['index.html','nations.html','nations/directory.html']:
        d=DOM((R/path).read_text(encoding='utf-8'))
        headers=[e for e in d.elements if e.tag=='header']
        assert any(a.tag=='a' and a.attrs.get('href')=='/theater' for h in headers for a in h.descendants()),path
    d=DOM((R/'index.html').read_text(encoding='utf-8'))
    hub,=d.by_id('explore-zotheos')
    assert {'/theater','/nations/directory','/nations/resources','/game'} <= {e.attrs.get('href') for e in hub.descendants() if e.tag=='a'}

def test_builder_supports_200_distinct_fictional_records_without_network(tmp_path,fictional_catalog):
    f=fictional_catalog['films'][0]
    fictional_catalog['films']=[]
    for i in range(200):
        x=copy.deepcopy(f);x.update(id='fixture-story-'+str(i),title='Fictional Story '+str(i),youtube_id='v'+str(i).zfill(10))
        fictional_catalog['films'].append(x)
    fictional_catalog['featured']=fictional_catalog['films'][0]['id']
    run=fixture_build(tmp_path,fictional_catalog)
    assert run.returncode==0,run.stdout+run.stderr
    d=DOM((tmp_path/'theater.html').read_text(encoding='utf-8'))
    assert len([e for e in d.elements if 'data-theater-film' in e.attrs])==200
    assert len([e for e in d.elements if e.tag=='iframe'])==1

@pytest.mark.parametrize('field,value',[('region','made-up-region'),('region',None),('form','unknown-form'),('location',''),('location',42)])
def test_new_geography_and_form_fields_fail_closed(tmp_path,fictional_catalog,field,value):
    fictional_catalog['films'][0][field]=value
    run=fixture_build(tmp_path,fictional_catalog)
    assert run.returncode!=0 and not (tmp_path/'theater.html').exists()

@pytest.mark.parametrize('slug',['bill-reid-remembers','some_film-title','Waaydanaa'])
def test_actual_bounded_nfb_slug_shapes_keep_the_fixed_provider_origin(tmp_path,fictional_catalog,slug):
    f=fictional_catalog['films'][0];f['youtube_id']=None;f['nfb_slug']=slug
    run=fixture_build(tmp_path,fictional_catalog)
    assert run.returncode==0,run.stdout+run.stderr
    d=DOM((tmp_path/'theater.html').read_text(encoding='utf-8'))
    assert any(e.tag=='iframe' and e.attrs.get('src')=='https://www.nfb.ca/film/'+slug+'/embed/player/?auto_play=false&autoplay=0' for e in d.elements)

def test_library_interactions_use_the_actual_script():
    p=Path(__file__).with_name('theater-library-acceptance.cjs')
    run=subprocess.run([r'C:\nvm4w\nodejs\node.exe',str(p),str(R/'static/theater/theater.js')],capture_output=True,text=True)
    assert run.returncode==0,run.stdout+run.stderr
