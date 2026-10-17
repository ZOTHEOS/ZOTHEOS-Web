"""Independent prebuild direct-reading and touch-action contract.

Observable first-result behavior uses fictional records and the actual script.
No claim of real device testing, source truth, or complete coverage is made.
"""
from pathlib import Path
from types import SimpleNamespace
import os
import shutil
import subprocess
import sys
import pytest

ROOT=Path(os.environ.get('ZOTHEOS_TEST_REPO',Path(__file__).resolve().parents[2]))
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tools/tests'))
import nations_directory as D
from test_indigenous_pathways import tree


def page():
    import nations_build as B
    b=B.Builder(str(ROOT));b.sp=lambda key,body,description:body
    return tree(D.page(b))


def test_two_direct_read_actions_start_hidden_and_have_context_and_native_semantics():
    doc=page()
    for key,context in [('directoryReadFirst','directoryTools'),('directoryResultsReadFirst','directoryResultsActions')]:
        matches=[n for n in doc.walk() if n.attrs.get('id')==key]
        assert len(matches)==1,'The direct reading action must exist in '+context
        node=matches[0]
        assert node.tag=='button' and node.attrs.get('type')=='button'
        assert 'hidden' in node.attrs and node.attrs.get('aria-controls')=='directoryNames'
        assert node.text.strip()=='Read First Matching Name'
        ancestors=[];parent=node.parent
        while parent is not None:ancestors.append(parent.attrs.get('id'));parent=parent.parent
        assert context in ancestors
    assert any(n.tag=='noscript' and 'All names remain visible without JavaScript' in n.text for n in doc.walk())
    assert any(n.tag=='a' and n.attrs.get('href')=='#directoryNames' for n in doc.walk())
    assert any(n.tag=='a' and n.attrs.get('href')=='#directoryQuery' for n in doc.walk())


def test_actual_script_direct_reading_behaviors():
    node=os.environ.get('ZOTHEOS_TEST_NODE') or shutil.which('node')
    if not node:pytest.skip('Node unavailable')
    result=subprocess.run([node,str(Path(__file__).with_name('directory-first-read-acceptance.cjs')),str(ROOT/'tools/nations/partials/appearance.js')],capture_output=True,text=True,encoding='utf8')
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('public,own_site',[(True,True),(True,False),(False,True),(False,False)])
def test_record_actions_group_only_real_public_destinations_without_losing_status(public,own_site):
    name='Fictional Name & <Untrusted Text>'
    row={'directory_id':'fictional-row','name':name,'directory_name':'Fictional Original Name',
         'registry_crosswalk':{'status':'confirmed','registry_id':'fictional-profile'}}
    if own_site:row['official_url']='https://nation.example.test/'
    b=SimpleNamespace(brand=SimpleNamespace(serif_ok=lambda value:False),m=SimpleNamespace(by_id={'fictional-profile':{}} if public else {}))
    doc=tree(D.entry(b,row))
    groups=[n for n in doc.walk() if n.attrs.get('role')=='group']
    links=[n for n in doc.walk() if n.tag=='a']
    expected=({'/nations/fictional-profile'} if public else set())|({'https://nation.example.test/'} if own_site else set())
    assert {n.attrs.get('href') for n in links}==expected
    if expected:
        assert len(groups)==1,'Real reading destinations form one labelled action area.'
        group=groups[0]
        label=group.attrs.get('aria-label','')
        assert name in label and any(word in label.lower() for word in ['explore','read','visit','source','action'])
        assert all(n in list(group.walk()) for n in links)
    else:assert not groups
    assert (not public)==('Profile Link Pending' in doc.text)
    assert name in doc.text and 'Fictional Original Name' in doc.text
    assert not [n for n in doc.walk() if n.tag in {'button','form','input','script','iframe','img','untrusted'} or any(k.startswith('on') for k in n.attrs)]
    for link in links:
        if link.attrs['href'].startswith('https:'):
            assert {'noopener','noreferrer'}<=set(link.attrs.get('rel','').split())
