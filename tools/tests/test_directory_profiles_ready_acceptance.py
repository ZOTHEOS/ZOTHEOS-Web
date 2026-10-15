"""Independent behavioral acceptance authored before Profiles Ready implementation.
Only fictional renderer fixtures; no website mutations, network or invented profiles.
"""
from html.parser import HTMLParser
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace
import pytest
ROOT=Path(os.environ.get('ZOTHEOS_TEST_REPO',Path(__file__).resolve().parents[2]))
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'tools'))
import nations_directory as D

class Tags(HTMLParser):
    def __init__(self):
        super().__init__();self.tags=[];self.stack=[];self.ancestors={};self.wrapped_labels=set()
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs);self.ancestors[len(self.tags)]=[a.get('id') for _,a in self.stack]
        if tag=='input' and any(t=='label' for t,_ in self.stack):self.wrapped_labels.add(attrs.get('id'))
        self.tags.append((tag,attrs,self.getpos()))
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append((tag,attrs))
    def handle_endtag(self,tag):
        for index in range(len(self.stack)-1,-1,-1):
            if self.stack[index][0]==tag:
                self.stack=self.stack[:index];break

def parse(value):
    p=Tags();p.feed(value);return p

@pytest.mark.parametrize('crosswalk,public,expected',[
    ({'status':'confirmed','registry_id':'fictional-public-profile'},True,'ready'),
    ({'status':'confirmed','registry_id':'fictional-public-profile'},False,'pending'),
    ({'status':'unreviewed','registry_id':None},True,'pending'),
])
def test_directory_ready_flag_tracks_public_reviewed_links(crosswalk,public,expected):
    row={'directory_id':'fictional-directory-row','name':'Fictional Name','directory_name':'Fictional Name','registry_crosswalk':crosswalk}
    b=SimpleNamespace(brand=SimpleNamespace(serif_ok=lambda value:False),m=SimpleNamespace(by_id={'fictional-public-profile':{}} if public else {}))
    result=D.entry(b,row);p=parse(result);li=next(attrs for tag,attrs,_ in p.tags if tag=='li')
    assert li.get('data-directory-profile')==expected
    links=[a.get('href','') for tag,a,_ in p.tags if tag=='a']
    assert ('/nations/fictional-public-profile' in links)==(expected=='ready')
    if expected=='pending':assert 'Profile Link Pending' in result

def test_optional_checkbox_is_native_labeled_and_hint_links_to_all_profiles():
    import nations_build as B
    b=B.Builder(str(ROOT));b.sp=lambda key,body,description:body
    result=D.page(b);p=parse(result)
    target=[(tag,a,pos) for tag,a,pos in p.tags if a.get('id')=='directoryProfilesOnly']
    assert len(target)==1,'A native optional Profiles Ready control must exist'
    tag,attrs,pos=target[0];assert tag=='input' and attrs.get('type')=='checkbox'
    assert 'Profiles Ready To Read' in result
    assert any(tag=='label' and a.get('for')=='directoryProfilesOnly' for tag,a,_ in p.tags) or 'directoryProfilesOnly' in p.wrapped_labels
    assert result.index('id="directoryInventory"')<result.index('id="directoryProfilesOnly"')<result.index('id="directoryResult"')
    hint=next((a for tag,a,_ in p.tags if a.get('id')=='directoryProfileHint'),None);assert hint is not None and 'hidden' in hint
    assert 'Filters reviewed directory links; other researched profiles may not be linked here yet.' in result
    assert any(tag=='a' and a.get('href')=='/nations#find' and 'directoryProfileHint' in p.ancestors[i] for i,(tag,a,_) in enumerate(p.tags))
    assert '<noscript>' in result and 'All names remain visible without JavaScript' in result

def test_profiles_ready_interactions_and_older_markup():
    node=shutil.which('node')
    if not node:pytest.skip('Node not installed')
    script=Path(__file__).with_name('directory-profiles-ready-acceptance.cjs')
    result=subprocess.run([node,str(script),str(ROOT/'tools/nations/partials/appearance.js')],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr

@pytest.mark.parametrize('action',['hide_nation','takedown'])
def test_profile_holds_remove_confirmed_directory_rows(action,monkeypatch):
    row={'directory_id':'fictional-directory-row','name':'Fictional Name','directory_name':'Fictional Name','registry_crosswalk':{'status':'confirmed','registry_id':'fictional-public-profile'}}
    model=SimpleNamespace(root=ROOT,raw={'nations':[{'id':'fictional-public-profile'}]},overrides={action:[{'nation':'fictional-public-profile'}]},by_id={})
    b=SimpleNamespace(root=ROOT,m=model)
    monkeypatch.setattr(D.I,'directory_holds',lambda root:set())
    assert D.visible_entries(b,[row])==[]
