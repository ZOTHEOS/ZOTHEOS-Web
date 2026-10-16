"""Independent chapter-brief behavior contract, authored before implementation.

Fictional public records exercise the actual renderer and builder. These tests
do not certify source truth, legal sufficiency, permission or real outcomes.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

import pytest

REPO=Path(os.environ.get('ZOTHEOS_TEST_REPO',Path(__file__).resolve().parents[2]))
sys.path.insert(0,str(REPO/'tools/tests'))
sys.path.insert(0,str(REPO/'tools'))
from test_indigenous_pathways import fixture_catalogue, fixture_model, tree


@pytest.fixture
def chapter_guide(tmp_path):
    data,model=fixture_catalogue(),fixture_model()
    path=tmp_path/'data/nations/pathways.json'
    path.parent.mkdir(parents=True)
    def call(kind='one',cid='land-and-water'):
        path.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
        spec=importlib.util.spec_from_file_location('chapter_brief_contract',REPO/'tools/nations_pathways.py')
        mod=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        name={'one':'chapter_brief','all':'chapter_briefs','render':'render','shared':'action_brief'}[kind]
        fn=getattr(mod,name,None)
        assert callable(fn),'The chapter-specific public brief helper must exist; expected prebuild RED.'
        return fn(tmp_path,model,cid) if kind=='one' else fn(tmp_path,model)
    return data,model,call,tmp_path


def test_selected_brief_contains_only_the_selected_chapter_and_its_authority_questions(chapter_guide):
    data,_,call,_=chapter_guide
    brief=call()
    assert isinstance(brief,str)
    selected,other=data['chapters']
    for value in [selected['title'],selected['deliverable'],selected['reflection'],*selected['verify']]:
        assert value in brief
    for value in [other['title'],other['deliverable'],other['reflection'],*other['verify']]:
        assert value not in brief
    assert 'https://zotheos.org/nations/paths-to-action#pw-land-and-water' in brief
    assert '<html' not in brief.lower() and '<script' not in brief.lower()


def test_reader_answers_remain_blank_with_privacy_and_unreleased_service_boundaries(chapter_guide):
    _,_,call,_=chapter_guide
    brief=call()
    for phrase in ['Question or need:','Who is affected:','Who has authority','Requested change:',
                   'What remains uncertain or disputed:','Permissions and information that must stay private:',
                   'Verified deadline','Responsible person or institution:','Next step I choose:']:
        lines=[line for line in brief.splitlines() if phrase in line]
        assert len(lines)==1 and re.search(r'_{3,}|\[ \]',lines[0]),phrase
    low=brief.lower()
    assert 'offline' in low and 'place you control' in low
    assert 'not' in low and 'submitted' in low
    assert 'not' in low and 'legal advice' in low and 'community consent' in low
    assert 'proposed' in low and 'not released' in low


def test_selected_sources_preserve_exact_urls_and_distinct_context_and_check_dates(chapter_guide):
    data,_,call,_=chapter_guide
    brief=call()
    selected,other=data['sources']
    for value in [selected['title'],selected['publisher'],selected['url'],selected['reviewed'],selected['as_of']]:
        assert value in brief
    assert brief.count(selected['url'])==1
    assert other['url'] not in brief and other['title'] not in brief
    assert 'context' in brief.lower() and 'checked' in brief.lower()


def test_step_only_source_is_included_once_and_a_repeated_reference_is_deduplicated(chapter_guide):
    data,_,call,_=chapter_guide
    data['chapters'][0]['steps'][0]['source_ids']=['culture-source']
    data['chapters'][0]['steps'][1]['source_ids']=['river-source','culture-source']
    brief=call()
    assert brief.count(data['sources'][0]['url'])==1
    assert brief.count(data['sources'][1]['url'])==1
    assert data['sources'][1]['reviewed'] in brief


def test_plain_brief_does_not_publish_example_facts_practice_or_raw_records(chapter_guide):
    data,model,call,_=chapter_guide
    data['chapters'][0]['examples'][0]['practice']={
        'question':'Hypothetical question sentinel','steps':['Hypothetical step sentinel'],
        'boundary':'Hypothetical boundary sentinel','reflection':'Hypothetical reflection sentinel'}
    model.raw['nations'][0]['name']='PRIVATE RAW IDENTITY'
    for kind in ['one','all']:
        result=call(kind)
        text='\n'.join(result.values()) if isinstance(result,dict) else result
        for forbidden in ['Fixture Nation','Exact public fact','https://nation.example.test/',
                          'PRIVATE RAW','Hypothetical question sentinel','Hypothetical step sentinel',
                          'Hypothetical boundary sentinel','Hypothetical reflection sentinel']:
            assert forbidden not in text


def test_mapping_has_only_safe_stable_filenames_and_exact_single_chapter_texts(chapter_guide):
    data,_,call,_=chapter_guide
    output=call('all')
    assert isinstance(output,dict) and len(output)==len(data['chapters'])
    assert set(output)=={'action-brief-'+c['id']+'.txt' for c in data['chapters']}
    assert all(re.fullmatch(r'action-brief-[a-z][a-z0-9]*(?:-[a-z0-9]+)*\.txt',name) for name in output)
    for chapter in data['chapters']:
        assert output['action-brief-'+chapter['id']+'.txt']==call('one',chapter['id'])
    before=copy.deepcopy(output)
    data['chapters'].reverse()
    assert call('all')==before


@pytest.mark.parametrize('cid',[None,True,0,[],{},'', 'unknown','../land-and-water','land-and-water/../../x',
                               '/land-and-water','land-and-water.txt','LAND-AND-WATER','land-and-water\x00',
                               'https://example.test/','..\\land-and-water'])
def test_unknown_unsafe_or_nonstring_selection_fails_closed(chapter_guide,cid):
    _,_,call,_=chapter_guide
    with pytest.raises(ValueError):call('one',cid)


@pytest.mark.parametrize('where',['chapter','step'])
def test_held_framework_source_removes_chapter_download_and_export(chapter_guide,where):
    data,model,call,_=chapter_guide
    if where=='step':
        data['chapters'][0]['steps'][0]['source_ids']=['culture-source']
        data['sources'][1]['nation']='fixture-nation'
    else:data['sources'][0]['nation']='fixture-nation'
    model.by_id.clear()
    with pytest.raises(ValueError):call()
    output=call('all')
    assert 'action-brief-land-and-water.txt' not in output
    html=call('render')
    assert '/static/nations/action-brief-land-and-water.txt' not in html
    assert 'Deliverable sentinel' not in html


@pytest.mark.parametrize('hold',['nation','one-fact','all-facts'])
def test_example_only_hold_cannot_hide_unrelated_public_chapter_or_leak_raw_data(chapter_guide,hold):
    _,model,call,_=chapter_guide
    if hold=='nation':model.by_id.clear()
    elif hold=='one-fact':model.by_id['fixture-nation']['facts'].pop()
    else:model.by_id['fixture-nation']['facts'].clear()
    brief=call()
    assert 'Deliverable sentinel' in brief and 'Fixture Nation' not in brief
    assert 'action-brief-land-and-water.txt' in call('all')


@pytest.mark.parametrize('bad',['unsafe-id','duplicate-id','unknown-step-source','unknown-example-fact',
                               'invalid-practice','bad-date','bad-url','bad-text'])
@pytest.mark.parametrize('selected',['land-and-water','language-and-culture','unknown'])
def test_whole_catalogue_is_validated_before_export_even_when_bad_chapter_is_held(chapter_guide,bad,selected):
    data,model,call,_=chapter_guide
    chapter=data['chapters'][0]
    data['sources'][0]['nation']='fixture-nation'
    model.by_id.clear()
    if bad=='unsafe-id':chapter['id']='../../leak'
    elif bad=='duplicate-id':data['chapters'].append(copy.deepcopy(chapter))
    elif bad=='unknown-step-source':chapter['steps'][0]['source_ids']=['missing']
    elif bad=='unknown-example-fact':chapter['examples'][0]['fact_ids']=['unreviewed']
    elif bad=='invalid-practice':chapter['examples'][0]['practice']={'question':'Only one field'}
    elif bad=='bad-date':data['sources'][0]['reviewed']='2026-02-30'
    elif bad=='bad-url':data['sources'][0]['url']='javascript:alert(1)'
    else:chapter['deliverable']='private\x00control'
    for kind in ['one','all']:
        with pytest.raises(ValueError):call(kind,selected)


def test_renderer_places_one_native_download_beside_each_public_deliverable(chapter_guide):
    data,_,call,_=chapter_guide
    doc=tree(call('render'))
    for chapter in data['chapters']:
        href='/static/nations/action-brief-'+chapter['id']+'.txt'
        links=[n for n in doc.walk() if n.tag=='a' and n.attrs.get('href')==href]
        assert len(links)==1 and 'download' in links[0].attrs
        assert 'brief' in links[0].text.lower() and 'download' in links[0].text.lower()
        nearby=links[0].parent
        while nearby.parent is not None and chapter['deliverable'] not in nearby.text:nearby=nearby.parent
        assert chapter['deliverable'] in nearby.text
        assert nearby.tag!='div' or 'pw-reading' not in nearby.attrs.get('class','')
    shared=[n for n in doc.walk() if n.tag=='a' and n.attrs.get('href')=='/static/nations/action-brief.txt']
    assert len(shared)==1 and 'download' in shared[0].attrs
    assert len([n for n in doc.walk() if n.tag=='nav'])==1
    assert not [n for n in doc.walk() if n.tag in {'form','script','button','input','textarea','select','iframe'}]


def test_exports_do_not_mutate_reader_catalogue_or_canonical_model(chapter_guide):
    data,model,call,_=chapter_guide
    before_data,before_model=copy.deepcopy(data),copy.deepcopy(vars(model))
    call();call('all');call('render')
    assert data==before_data and vars(model)==before_model


def test_actual_builder_writes_real_chapter_files_matching_links_without_font_pipeline(chapter_guide):
    data,model,call,root=chapter_guide
    expected=call('all')
    import nations_build as builder
    b=object.__new__(builder.Builder)
    b.root=str(root)
    b.m=model
    # Isolate the real build orchestration from unrelated fonts/data/page work.
    # The guide helpers and text-file writer remain the actual production code.
    b.m.nations=[];b.m.regions=[];b.m.by_country={}
    b.m.build_date='2026-10-16';b.m.counts={'shown':0}
    b.m.last_full_check=lambda:'2026-10-16'
    b.part=lambda name:''
    (root/'index.html').write_text('<script></script><style id="zth-fonts"></style>',encoding='utf8')
    b.build_data=lambda out:setattr(b,'index_json','{}')
    b.hub=lambda:'<main>Fictional hub</main>'
    b.support_pages=lambda:{'paths-to-action':call('render')}
    b.write_vercel=lambda out:None
    b.write_sitemap=lambda out,pages:None
    b.build(str(root))
    for name,text in expected.items():
        path=root/'static/nations'/name
        assert path.is_file(),'The real builder must write every public chapter export.'
        assert path.read_text(encoding='utf8')==text
    assert (root/'static/nations/action-brief.txt').read_text(encoding='utf8')==call('shared')
