"""Independent prebuild contract for opt-in native history reading. Fictional data only.

Real Context output is parsed. These cases do not certify browser geometry or source meaning.
"""
import copy
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

import pytest

R=Path(os.environ.get('ZOTHEOS_TEST_REPO',str(Path(__file__).resolve().parents[2])))
sys.dont_write_bytecode=True
sys.path.insert(0,str(R/'tools'))
if os.environ.get('ZOTHEOS_CONTEXT_MODULE'):
    spec=importlib.util.spec_from_file_location('history_context_under_test',os.environ['ZOTHEOS_CONTEXT_MODULE'])
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    Context=module.Context
else:
    from nations_context import Context

LABEL='In This History'
CONTEXT_LABEL='In This Context'
RESOURCE_LABEL='Publisher Resources'
RESOURCE_HEADING="From the publisher's own pages"
DAY='2026-10-12'
SCHOOL='FICTIONAL: Schools And Community Persistence'
RIVER='FICTIONAL: River Work And Future Goals'
BODY1='A fictional school account; no historical or community approval claim.'
BODY2='A fictional river account; an ambition is not a measured outcome.'
URL1='https://alpha.example/schools'
URL2='https://alpha.example/river'

class Node:
    def __init__(self,tag,attrs=()):self.tag=tag;self.attrs=dict(attrs);self.children=[]
    def text(self):return ''.join(c.text() if isinstance(c,Node) else c for c in self.children)
    def nodes(self):
        return [self]+[v for c in self.children if isinstance(c,Node) for v in c.nodes()]

class DOM(HTMLParser):
    def __init__(self,markup):
        super().__init__(convert_charrefs=True);self.root=Node('root');self.stack=[self.root];self.feed(markup)
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs);self.stack[-1].children.append(node)
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append(node)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:self.stack=self.stack[:i];break
    def handle_data(self,data):self.stack[-1].children.append(data)
    def nodes(self):return self.root.nodes()

def public_model():
    alpha={'id':'test-alpha','name':'Fictional Alpha','facts':[{'id':'alpha-public'}]}
    beta={'id':'test-beta','name':'Fictional Beta','facts':[]}
    return SimpleNamespace(nations=[alpha,beta],by_id={n['id']:n for n in [alpha,beta]},
      raw={'nations':[{'id':'test-alpha','facts':[{'id':'alpha-public'},{'id':'alpha-held'}]},
                     {'id':'test-beta','facts':[]},{'id':'test-gone','facts':[]}]})

def data():
    doc={'reviewed':DAY,'public_notes':[
       {'nation':'test-alpha','reading_id':'schools','title':SCHOOL,'text':BODY1,'source_urls':[URL1]},
       {'nation':'test-alpha','reading_id':'river-work','title':RIVER,'text':BODY2,'source_urls':[URL2]}],
       'official_resources':[
       {'nation':'test-alpha','url':URL1,'label':'Fictional Schools Primary Source','purpose':'Fictional source account.'},
       {'nation':'test-alpha','url':URL2,'label':'Fictional River Primary Source','purpose':'Fictional source account.'}]}
    allow={'version':1,'links':[
       {'nation':'test-alpha','url':URL1,'publisher':'Fictional Alpha','reviewed':'2026-10-08'},
       {'nation':'test-alpha','url':URL2,'publisher':'Fictional Alpha','reviewed':'2026-10-09'}]}
    return doc,allow

def write(tmp,docs,allow):
    folder=tmp/'data/nations';sources=folder/'sources';sources.mkdir(parents=True,exist_ok=True)
    if isinstance(docs,dict):docs=[docs]
    for i,doc in enumerate(docs):
        (sources/f'{i:02d}.context.json').write_text(json.dumps(doc),encoding='utf8')
    (folder/'context_links.json').write_text(json.dumps(allow),encoding='utf8')

def render(tmp,doc=None,allow=None,model=None,nid='test-alpha'):
    if doc is None:doc,allow=data()
    write(tmp,doc,allow)
    return Context(tmp,model or public_model()).page(nid)

def navigation(dom):
    return [n for n in dom.nodes() if n.tag=='nav' and n.attrs.get('aria-label') in {LABEL,CONTEXT_LABEL}]

def target_map(dom):
    return {n.text():n for n in dom.nodes() if n.tag=='h3' and n.attrs.get('id','').startswith('nHistory-')}

def assert_native_links(markup,expected):
    dom=DOM(markup);nav=navigation(dom)
    assert len(nav)==1,'One labelled native context/history navigation is required.'
    expected_label=CONTEXT_LABEL if any(href=='#nResources' for _,href in expected) else LABEL
    assert nav[0].attrs.get('aria-label')==expected_label
    labels=[n.text() for n in nav[0].nodes() if n.tag=='p' and 'lbl' in n.attrs.get('class','').split()]
    assert labels==[expected_label]
    assert 'nation-reading' in nav[0].attrs.get('class','').split(),'Reuse existing wrapping/44px native reading styles.'
    links=[n for n in nav[0].nodes() if n.tag=='a']
    assert [(n.text(),n.attrs.get('href')) for n in links]==expected
    targets={n.attrs['id']:n for n in dom.nodes() if 'id' in n.attrs}
    ids=[n.attrs['id'] for n in dom.nodes() if 'id' in n.attrs]
    assert len(ids)==len(set(ids)),'No duplicate DOM target IDs.'
    for link in links:
        assert link.attrs.get('href','').startswith('#') and 'onclick' not in link.attrs
        target=targets[link.attrs['href'][1:]]
        assert target.tag=='h3' and target.attrs.get('tabindex')=='-1'
        assert target.text()==(RESOURCE_HEADING if link.attrs['href']=='#nResources' else link.text())
        assert 'target' not in link.attrs and 'download' not in link.attrs
    assert markup.index('<nav')<markup.index('id="nHistory-'),'Navigation precedes its reading targets.'
    return dom

def test_two_visible_layers_get_named_native_jump_links(tmp_path):
    page=render(tmp_path)
    assert_native_links(page,[(SCHOOL,'#nHistory-schools'),(RIVER,'#nHistory-river-work'),(RESOURCE_LABEL,'#nResources')])
    assert page.count(BODY1)==page.count(BODY2)==1

def test_one_opted_layer_keeps_its_target_without_redundant_navigation(tmp_path):
    doc,allow=data();del doc['public_notes'][1]['reading_id']
    dom=DOM(render(tmp_path,doc,allow))
    assert not navigation(dom)
    targets=target_map(dom)
    assert list(targets)==[SCHOOL]
    assert targets[SCHOOL].attrs.get('id')=='nHistory-schools' and targets[SCHOOL].attrs.get('tabindex')=='-1'

def test_absent_opt_in_preserves_real_legacy_fragment_byte_for_byte(tmp_path):
    doc,allow=data()
    for note in doc['public_notes']:del note['reading_id']
    page=render(tmp_path,doc,allow)
    golden=Path(__file__).with_name('legacy-history-navigation-golden.html').read_text(encoding='utf8')
    assert page==golden
    assert not navigation(DOM(page)) and not target_map(DOM(page))

def test_holds_do_not_reassign_surviving_anchor(tmp_path):
    doc,allow=data();doc['public_notes'][0]['fact_ids']=['alpha-held']
    page=render(tmp_path,doc,allow);dom=DOM(page)
    assert not navigation(dom)
    assert SCHOOL not in dom.root.text() and BODY1 not in dom.root.text() and 'nHistory-schools' not in page
    assert target_map(dom)[RIVER].attrs['id']=='nHistory-river-work'

def test_referenced_resource_hold_suppresses_layer_and_navigation_entry(tmp_path):
    doc,allow=data();doc['official_resources'][0]['fact_ids']=['alpha-held']
    page=render(tmp_path,doc,allow);dom=DOM(page)
    assert not navigation(dom) and BODY1 not in page and 'nHistory-schools' not in page
    assert target_map(dom)[RIVER].attrs['id']=='nHistory-river-work'
    assert 'Fictional Schools Primary Source' not in dom.root.text()

def test_no_visible_layers_has_no_empty_navigation_or_hidden_ids(tmp_path):
    doc,allow=data()
    for note in doc['public_notes']:note['fact_ids']=['alpha-held']
    page=render(tmp_path,doc,allow)
    assert not navigation(DOM(page)) and 'nHistory-' not in page and BODY1 not in page and BODY2 not in page

def test_hidden_nation_is_not_resurrected_by_navigation(tmp_path):
    model=public_model();model.nations=[model.by_id['test-beta']];model.by_id={'test-beta':model.by_id['test-beta']}
    assert render(tmp_path,model=model)==''

def test_legacy_titled_layer_is_not_silently_added_to_navigation(tmp_path):
    doc,allow=data();doc['public_notes'].insert(1,{'nation':'test-alpha','title':'Legacy Title','text':'Legacy body.'})
    page=render(tmp_path,doc,allow)
    dom=assert_native_links(page,[(SCHOOL,'#nHistory-schools'),(RIVER,'#nHistory-river-work'),(RESOURCE_LABEL,'#nResources')])
    old=[n for n in dom.nodes() if n.tag=='h3' and n.text()=='Legacy Title']
    assert len(old)==1 and 'id' not in old[0].attrs and 'tabindex' not in old[0].attrs

def test_reordering_notes_changes_link_order_but_not_target_identity(tmp_path):
    doc,allow=data();doc['public_notes'].reverse()
    assert_native_links(render(tmp_path,doc,allow),[(RIVER,'#nHistory-river-work'),(SCHOOL,'#nHistory-schools'),(RESOURCE_LABEL,'#nResources')])

def test_editorial_title_change_does_not_rewrite_the_stable_target(tmp_path):
    doc,allow=data();doc['public_notes'][0]['title']='Revised Fictional School Heading'
    assert_native_links(render(tmp_path,doc,allow),[('Revised Fictional School Heading','#nHistory-schools'),(RIVER,'#nHistory-river-work'),(RESOURCE_LABEL,'#nResources')])

def test_visible_opt_in_layers_across_files_share_one_navigation(tmp_path):
    doc,allow=data();other=copy.deepcopy(doc)
    doc['public_notes']=doc['public_notes'][:1];other['public_notes']=other['public_notes'][1:];other['official_resources']=[]
    assert_native_links(render(tmp_path,[doc,other],allow),[(SCHOOL,'#nHistory-schools'),(RIVER,'#nHistory-river-work'),(RESOURCE_LABEL,'#nResources')])

def test_same_reading_id_in_distinct_nations_is_not_a_collision(tmp_path):
    doc,allow=data();doc['public_notes'].append({'nation':'test-beta','reading_id':'schools','title':'Other Government','text':'A separate fictional Nation.'})
    page=render(tmp_path,doc,allow)
    assert_native_links(page,[(SCHOOL,'#nHistory-schools'),(RIVER,'#nHistory-river-work'),(RESOURCE_LABEL,'#nResources')])
    assert 'Other Government' not in page

@pytest.mark.parametrize('hidden',[False,True])
def test_duplicate_ids_in_same_nation_fail_even_if_one_is_held(tmp_path,hidden):
    doc,allow=data();doc['public_notes'][1]['reading_id']='schools'
    if hidden:doc['public_notes'][1]['fact_ids']=['alpha-held']
    with pytest.raises(ValueError):render(tmp_path,doc,allow)

def test_duplicate_ids_across_files_fail_before_publishing_wrong_link(tmp_path):
    doc,allow=data();other={'reviewed':DAY,'public_notes':[{'nation':'test-alpha','reading_id':'schools','title':'Separate Title','text':'Separate candidate.'}]}
    with pytest.raises(ValueError):render(tmp_path,[doc,other],allow)

@pytest.mark.parametrize('invalid',[None,False,True,3,[],{},'', ' ', 'UpperCase','bad_id','-leading','trailing-',
    'double--dash','has space','a/b','quote"x','x#y','école','a'*49,'line\nfeed','x\x00y','x\x7fy'])
def test_malformed_or_oversized_explicit_id_is_not_ignored(tmp_path,invalid):
    doc,allow=data();doc['public_notes'][0]['reading_id']=invalid
    with pytest.raises(ValueError):render(tmp_path,doc,allow)

@pytest.mark.parametrize('title',[None,'','   ','\t\n'])
def test_opted_layer_requires_an_actual_nonblank_heading(tmp_path,title):
    doc,allow=data()
    if title is None:del doc['public_notes'][0]['title']
    else:doc['public_notes'][0]['title']=title
    with pytest.raises(ValueError):render(tmp_path,doc,allow)

@pytest.mark.parametrize('valid',['a','7-stories','a'*48])
def test_boundary_valid_ids_resolve_exactly(tmp_path,valid):
    doc,allow=data();doc['public_notes'][0]['reading_id']=valid
    assert_native_links(render(tmp_path,doc,allow),[(SCHOOL,'#nHistory-'+valid),(RIVER,'#nHistory-river-work'),(RESOURCE_LABEL,'#nResources')])

def test_unicode_and_hostile_heading_text_is_escaped_in_label_and_target(tmp_path):
    doc,allow=data();title='Fictional: Náhá & <img src=x onerror="alert(1)">';doc['public_notes'][0]['title']=title
    dom=assert_native_links(render(tmp_path,doc,allow),[(title,'#nHistory-schools'),(RIVER,'#nHistory-river-work'),(RESOURCE_LABEL,'#nResources')])
    assert not [n for n in dom.nodes() if n.tag in {'img','script','iframe'}]
    assert all(not k.startswith('on') for n in dom.nodes() for k in n.attrs)

def test_navigation_does_not_mint_sources_or_change_review_clocks(tmp_path):
    page=render(tmp_path);dom=DOM(page)
    assert_native_links(page,[(SCHOOL,'#nHistory-schools'),(RIVER,'#nHistory-river-work'),(RESOURCE_LABEL,'#nResources')])
    external=[n.attrs['href'] for n in dom.nodes() if n.tag=='a' and not n.attrs.get('href','').startswith('#')]
    assert external==[URL1,URL2,URL1,URL2]
    assert page.count('Sources For This Layer')==2
    dates=[n.attrs.get('datetime') for n in dom.nodes() if n.tag=='time']
    assert dates==[DAY,'2026-10-08',DAY,'2026-10-09','2026-10-08','2026-10-09']

def test_native_output_needs_no_script_storage_or_remote_media(tmp_path):
    page=render(tmp_path);dom=DOM(page)
    assert_native_links(page,[(SCHOOL,'#nHistory-schools'),(RIVER,'#nHistory-river-work'),(RESOURCE_LABEL,'#nResources')])
    assert all(n.tag not in {'script','iframe','img','video','audio','form','button','input'} for n in dom.nodes())
    assert not re.search(r'localStorage|sessionStorage|fetch\(|XMLHttpRequest|history\.',page)
