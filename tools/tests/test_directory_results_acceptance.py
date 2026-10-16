"""Prebuild acceptance for the results context and progressive enhancement."""
from html.parser import HTMLParser
import os
import shutil
import subprocess
import pytest
from pathlib import Path
import sys
ROOT=Path(os.environ.get('ZOTHEOS_TEST_REPO',Path(__file__).resolve().parents[2]))
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'tools'))
import nations_directory as D
import nations_build as B
class Tags(HTMLParser):
    def __init__(self):super().__init__();self.tags=[];self.stack=[];self.parents={}
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs);self.parents[len(self.tags)]=[a.get('id') for _,a in self.stack];self.tags.append((tag,attrs))
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:self.stack.append((tag,attrs))
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:self.stack=self.stack[:i];break

def page():
    b=B.Builder(str(ROOT));b.sp=lambda key,body,description:body
    text=D.page(b);p=Tags();p.feed(text);return text,p

def test_results_context_is_inside_focusable_results_before_source_groups():
    text,p=page();intro=[(i,t,a) for i,(t,a) in enumerate(p.tags) if a.get('id')=='directoryResultsIntro'];assert len(intro)==1,'Optional results intro must exist'
    i,t,a=intro[0];assert 'hidden' in a;assert 'directoryNames' in p.parents[i]
    names=next(a for t,a in p.tags if a.get('id')=='directoryNames');assert names.get('tabindex')=='-1'
    group=next(i for i,(t,a) in enumerate(p.tags) if a.get('data-directory-inventory'));assert intro[0][0]<group
    assert '<h2' in text[text.index('id="directoryResultsIntro"'):text.index('data-directory-inventory')]
    assert 'Matching Names' in text

def test_summary_is_plain_text_and_only_original_live_region_announces():
    text,p=page();summary=[(i,a) for i,(t,a) in enumerate(p.tags) if a.get('id')=='directoryResultsSummary'];assert len(summary)==1,'Adjacent summary must exist'
    i,a=summary[0];assert 'directoryResultsIntro' in p.parents[i];assert 'aria-live' not in a and a.get('role')!='status'
    statuses=[a for t,a in p.tags if a.get('role')=='status' or a.get('aria-live')];assert len(statuses)==1 and statuses[0].get('id')=='directoryResult'

def test_empty_guidance_is_hidden_and_has_native_routes_to_recover():
    text,p=page();empty=[(i,a) for i,(t,a) in enumerate(p.tags) if a.get('id')=='directoryResultsEmpty'];assert len(empty)==1,'Empty results guidance must exist'
    i,a=empty[0];assert 'hidden' in a and 'directoryResultsIntro' in p.parents[i]
    links=[a.get('href') for i,(t,a) in enumerate(p.tags) if t=='a' and 'directoryResultsEmpty' in p.parents[i]]
    assert '#directoryQuery' in links and '/nations#find' in links
    assert 'Adjust Filters' in text and 'Search Researched Profiles' in text
    assert 'All names remain visible without JavaScript' in text


def test_results_interactions_against_actual_directory_script():
    node=shutil.which('node')
    if not node: pytest.skip('Node unavailable')
    result=subprocess.run([node,str(Path(__file__).with_name('directory-results-acceptance.cjs')),str(ROOT/'tools/nations/partials/appearance.js')],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
