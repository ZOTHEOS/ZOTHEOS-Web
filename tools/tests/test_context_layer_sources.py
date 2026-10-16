"""Independent optional per-layer citations contract. All data are fictional.

The real Context renderer runs against an isolated model/approved-resource set.
These checks do not certify historical meaning, browser geometry or approval by a Nation.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

R=Path(os.environ.get('ZOTHEOS_TEST_REPO',str(Path(__file__).resolve().parents[2])))
sys.dont_write_bytecode=True
sys.path.insert(0,str(R/'tools'))
sys.path.insert(0,str(R/'tools/tests'))
from nations_context import Context
from theater_acceptance_v1_helpers import DOM

DAY='2026-10-12'
URL1='https://alpha.example/history?edition=1&scope=public'
URL2='https://alpha.example/river'
URLB='https://beta.example/history'
TITLE1='Fictional School History'
BODY1='FICTIONAL FIRST LAYER: Schools and community continuity.'
BODY2='FICTIONAL SECOND LAYER: River work and future aims.'
SOURCE1='Alpha: School History'
SOURCE2='Alpha: River Initiative'
LABEL='Sources For This Layer'


def public_model():
    alpha={'id':'test-alpha','name':'Fictional Alpha','facts':[{'id':'alpha-public'}]}
    beta={'id':'test-beta','name':'Fictional Beta','facts':[]}
    return SimpleNamespace(nations=[alpha,beta],by_id={n['id']:n for n in [alpha,beta]},
        raw={'nations':[{'id':'test-alpha','facts':[{'id':'alpha-public'},{'id':'alpha-held'}]},
                        {'id':'test-beta','facts':[]},{'id':'test-gone','facts':[]}]})


def fixture_data():
    doc={'reviewed':DAY,'public_notes':[
        {'nation':'test-alpha','title':TITLE1,'text':BODY1,'source_urls':[URL1]},
        {'nation':'test-alpha','title':'Fictional River Work','text':BODY2,'source_urls':[URL2]}],
        'official_resources':[
          {'nation':'test-alpha','url':URL1,'label':SOURCE1,'purpose':'Read the fictional school account.'},
          {'nation':'test-alpha','url':URL2,'label':SOURCE2,'purpose':'Read the fictional river account.'},
          {'nation':'test-beta','url':URLB,'label':'Beta History','purpose':'Another Nation, separately sourced.'}]}
    allow={'version':1,'links':[
        {'nation':'test-alpha','url':URL1,'publisher':'Fictional Alpha Publisher','reviewed':'2026-10-10'},
        {'nation':'test-alpha','url':URL2,'publisher':'Fictional Alpha Publisher','reviewed':'2026-10-11'},
        {'nation':'test-beta','url':URLB,'publisher':'Fictional Beta Publisher','reviewed':'2026-10-09'}]}
    return doc,allow


def write_data(tmp_path,doc,allow):
    folder=tmp_path/'data/nations';(folder/'sources').mkdir(parents=True,exist_ok=True)
    (folder/'sources/fixture.context.json').write_text(json.dumps(doc),encoding='utf-8')
    (folder/'context_links.json').write_text(json.dumps(allow),encoding='utf-8')
    return folder


def renderer(tmp_path,doc,allow,model=None):
    write_data(tmp_path,doc,allow)
    return Context(tmp_path,model or public_model())


def between_first_and_second(page):
    # Reading order supplies an implementation-independent note association:
    # citations must occur after the first note and before the next note.
    start=page.index(BODY1);end=page.index('Fictional River Work')
    return DOM(page[start:end])


def anchors(dom):
    return [e for e in dom.elements if e.tag=='a']


def test_explicit_source_is_native_under_its_layer_before_the_next_layer(tmp_path):
    doc,allow=fixture_data();page=renderer(tmp_path,doc,allow).page('test-alpha')
    layer=between_first_and_second(page)
    assert LABEL in layer.root.text
    link,=[e for e in anchors(layer) if e.attrs.get('href')==URL1]
    assert SOURCE1 in link.text and SOURCE2 not in layer.root.text
    assert 'noopener' in link.attrs.get('rel','') and 'noreferrer' in link.attrs.get('rel','')
    assert not any(e.tag in ('script','iframe','button') for e in layer.elements)


def test_multi_source_note_retains_explicit_order_and_distinct_checked_dates(tmp_path):
    doc,allow=fixture_data();doc['public_notes'][0]['source_urls']=[URL2,URL1]
    page=renderer(tmp_path,doc,allow).page('test-alpha');layer=between_first_and_second(page)
    assert [e.attrs['href'] for e in anchors(layer)]==[URL2,URL1]
    assert 'Fictional Alpha Publisher' in layer.root.text
    dates=[e.attrs.get('datetime') for e in layer.elements if e.tag=='time']
    assert '2026-10-10' in dates and '2026-10-11' in dates
    assert DAY in dates,'Context review date and source review dates stay separate'


def test_no_implicit_source_backfill_and_legacy_html_remains_exact(tmp_path):
    doc,allow=fixture_data()
    for note in doc['public_notes']:note.pop('source_urls')
    page=renderer(tmp_path,doc,allow).page('test-alpha')
    golden=Path(__file__).with_name('legacy-layer-golden.html').read_text(encoding='utf-8')
    assert page==golden
    assert LABEL not in between_first_and_second(page).root.text


@pytest.mark.parametrize('value',[None,[],URL1,{},[None],[7],[True],[URL1,URL1]])
def test_present_malformed_or_duplicate_source_references_fail_closed(tmp_path,value):
    doc,allow=fixture_data();doc['public_notes'][0]['source_urls']=value
    with pytest.raises(ValueError):renderer(tmp_path,doc,allow)


def test_more_than_four_explicit_sources_is_rejected(tmp_path):
    doc,allow=fixture_data();urls=[URL1,URL2]
    for i in range(3):
        url='https://alpha.example/extra-'+str(i);urls.append(url)
        allow['links'].append({'nation':'test-alpha','url':url,'publisher':'Alpha','reviewed':DAY})
        doc['official_resources'].append({'nation':'test-alpha','url':url,'label':'Extra '+str(i),'purpose':'Fictional.'})
    doc['public_notes'][0]['source_urls']=urls
    with pytest.raises(ValueError):renderer(tmp_path,doc,allow)


def test_four_explicit_sources_are_supported_without_silent_truncation(tmp_path):
    doc,allow=fixture_data();urls=[URL1,URL2]
    for i in range(2):
        url='https://alpha.example/boundary-'+str(i);urls.append(url)
        allow['links'].append({'nation':'test-alpha','url':url,'publisher':'Alpha','reviewed':DAY})
        doc['official_resources'].append({'nation':'test-alpha','url':url,'label':'Boundary '+str(i),'purpose':'Fictional.'})
    doc['public_notes'][0]['source_urls']=urls
    layer=between_first_and_second(renderer(tmp_path,doc,allow).page('test-alpha'))
    assert [e.attrs['href'] for e in anchors(layer)]==urls


@pytest.mark.parametrize('url',[
    'https://alpha.example/never-reviewed',URL1+'&unreviewed=1',URLB,
    'https://alpha.example/history?scope=public&edition=1',
])
def test_exact_nation_url_and_reviewed_resource_required_not_same_host_or_other_nation(tmp_path,url):
    doc,allow=fixture_data();doc['public_notes'][0]['source_urls']=[url]
    with pytest.raises(ValueError):renderer(tmp_path,doc,allow)


def test_approved_url_without_a_corresponding_resource_cannot_be_guessed_into_a_citation(tmp_path):
    doc,allow=fixture_data();url='https://alpha.example/approved-but-not-described'
    allow['links'].append({'nation':'test-alpha','url':url,'publisher':'Alpha','reviewed':DAY})
    doc['public_notes'][0]['source_urls']=[url]
    with pytest.raises(ValueError):renderer(tmp_path,doc,allow)


@pytest.mark.parametrize('url',[
    'javascript:alert(1)','http://alpha.example/history','//alpha.example/history',
    'https://user:password@alpha.example/history','https://alpha.example:0/history',
    'https://alpha.example:/history','https://alpha.example:bad/history',
    'https://alpha.example\\evil.test/history',
])
def test_unsafe_urls_cannot_be_made_safe_by_an_approval_entry(tmp_path,url):
    doc,allow=fixture_data();doc['public_notes'][0]['source_urls']=[url]
    doc['official_resources'][0]['url']=url;allow['links'][0]['url']=url
    with pytest.raises(ValueError):renderer(tmp_path,doc,allow)


def test_explicit_held_resource_suppresses_layer_and_citation_without_leaking_text_or_url(tmp_path):
    doc,allow=fixture_data();doc['official_resources'][0]['fact_ids']=['alpha-held']
    page=renderer(tmp_path,doc,allow).page('test-alpha')
    assert TITLE1 not in page and BODY1 not in page and SOURCE1 not in page
    assert URL1 not in page and 'alpha.example/history' not in page
    assert BODY2 in page and SOURCE2 in page


def test_one_held_resource_in_a_multi_source_note_suppresses_the_whole_associated_layer(tmp_path):
    doc,allow=fixture_data();doc['public_notes'][0]['source_urls']=[URL1,URL2]
    doc['official_resources'][1]['fact_ids']=['alpha-held']
    page=renderer(tmp_path,doc,allow).page('test-alpha')
    assert BODY1 not in page and BODY2 not in page
    assert SOURCE2 not in page and URL2 not in page


def test_note_fact_hold_still_suppresses_its_new_source_group(tmp_path):
    doc,allow=fixture_data();doc['public_notes'][0]['fact_ids']=['alpha-held']
    page=renderer(tmp_path,doc,allow).page('test-alpha')
    assert BODY1 not in page and TITLE1 not in page
    # Its separately public resource may still appear in the footer; no invented
    # citation group is permitted before the unrelated next note.
    assert page.count(LABEL)==1


def test_hidden_nation_does_not_return_note_sources_or_resurrect_a_record(tmp_path):
    doc,allow=fixture_data();model=public_model();model.nations=model.nations[1:];model.by_id.pop('test-alpha')
    ctx=renderer(tmp_path,doc,allow,model)
    assert ctx.page('test-alpha')=='' and SOURCE1 not in ctx.page('test-beta')


def test_source_label_publisher_and_note_heading_are_escaped(tmp_path):
    doc,allow=fixture_data()
    doc['public_notes'][0]['title']='<script>badHeading()</script>'
    doc['official_resources'][0]['label']='<img src=x onerror=badLabel()> & "source"'
    allow['links'][0]['publisher']='<svg onload=badPublisher()>'
    page=renderer(tmp_path,doc,allow).page('test-alpha');layer=between_first_and_second(page)
    assert '<img src=x onerror=badLabel()>' in layer.root.text
    assert '<svg onload=badPublisher()>' in layer.root.text
    assert not any(e.tag in ('img','svg','script') for e in DOM(page).elements)


def test_long_native_source_labels_use_the_existing_wrapping_touch_target_list(tmp_path):
    doc,allow=fixture_data();doc['official_resources'][0]['label']='FictionalSourceLabel'*7
    page=renderer(tmp_path,doc,allow).page('test-alpha');layer=between_first_and_second(page)
    link,=[e for e in anchors(layer) if e.attrs.get('href')==URL1]
    parent=link.parent
    while parent and 'src-u' not in parent.attrs.get('class','').split():parent=parent.parent
    assert parent is not None,'Reuse the existing native wrapping source-list treatment'
    css=(R/'tools/nations/partials/nations.css').read_text(encoding='utf-8')
    assert 'min-height: 44px' in css and 'overflow-wrap: anywhere' in css


@pytest.mark.parametrize('resource_name,note_name',[('a.context.json','z.context.json'),('z.context.json','a.context.json')])
def test_explicit_association_across_context_files_does_not_depend_on_filename_order(tmp_path,resource_name,note_name):
    doc,allow=fixture_data()
    resources={'reviewed':DAY,'official_resources':doc.pop('official_resources')}
    folder=write_data(tmp_path,{},allow)
    (folder/'sources/fixture.context.json').unlink()
    for name,data in [(resource_name,resources),(note_name,doc)]:
        (folder/'sources'/name).write_text(json.dumps(data),encoding='utf-8')
    page=Context(tmp_path,public_model()).page('test-alpha');layer=between_first_and_second(page)
    assert LABEL in layer.root.text and [e.attrs['href'] for e in anchors(layer)]==[URL1]


@pytest.mark.parametrize('conflict',['label','held_visibility'])
def test_conflicting_duplicate_resource_associations_fail_rather_than_choose_arbitrarily(tmp_path,conflict):
    doc,allow=fixture_data();folder=write_data(tmp_path,doc,allow)
    duplicate=copy.deepcopy(doc['official_resources'][0])
    if conflict=='label':duplicate['label']='A Different Unresolved Source Label'
    else:duplicate['fact_ids']=['alpha-held']
    extra={'reviewed':DAY,'official_resources':[duplicate]}
    (folder/'sources/second.context.json').write_text(json.dumps(extra),encoding='utf-8')
    with pytest.raises(ValueError):Context(tmp_path,public_model())


def test_identical_duplicate_resource_definition_does_not_duplicate_a_layer_citation(tmp_path):
    doc,allow=fixture_data();folder=write_data(tmp_path,doc,allow)
    (folder/'sources/second.context.json').write_text(json.dumps({'reviewed':DAY,'official_resources':[doc['official_resources'][0]]}),encoding='utf-8')
    page=Context(tmp_path,public_model()).page('test-alpha');layer=between_first_and_second(page)
    assert len([a for a in anchors(layer) if a.attrs.get('href')==URL1])==1
