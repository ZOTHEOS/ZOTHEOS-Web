"""Independent Theater release contract. Fictional fixtures are not film research.

Public output checks and isolated CLI fixture builds exercise the real renderer;
the companion Node fixture exercises the actual optional enhancement script.
No external requests, browser certification or publisher endorsement is implied.
"""
import copy
import datetime as dt
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

import pytest

ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
ART = Path(__file__).resolve().parent
PYTHON = sys.executable
DAY = (dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)).isoformat()
ALLOWED_FRAMES = {'https://www.youtube-nocookie.com', 'https://player.pbs.org'}
VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}


class El:
    def __init__(self, tag, attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children, self.parts = [], []

    @property
    def text(self):
        return ' '.join(' '.join(p.text if isinstance(p,El) else p for p in self.parts).split())

    def descendants(self):
        for child in self.children:
            yield child
            yield from child.descendants()


class DOM(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root=El('document'); self.stack=[self.root]
        self.feed(text); self.elements=list(self.root.descendants())

    def handle_starttag(self, tag, attrs):
        el=El(tag,attrs,self.stack[-1]); self.stack[-1].children.append(el); self.stack[-1].parts.append(el)
        if tag not in VOID: self.stack.append(el)

    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:
                self.stack=self.stack[:i]; return

    def handle_data(self,text): self.stack[-1].parts.append(text)
    def by_id(self,key): return [el for el in self.elements if el.attrs.get('id')==key]


def page():
    path=ROOT/'theater.html'
    assert path.is_file(), 'The real Theater page must be generated'
    text=path.read_text(encoding='utf-8')
    return text,DOM(text)


def catalog():
    path=ROOT/'data/theater/films.json'
    assert path.is_file(), 'Reviewed Theater catalogue must exist'
    return json.loads(path.read_text(encoding='utf-8'))


def directives(policy):
    return {part.split()[0]:part.split()[1:] for part in policy.split(';') if part.strip()}


def header_policies():
    conf=json.loads((ROOT/'vercel.json').read_text(encoding='utf-8'))
    return {entry['source']:header['value'] for entry in conf['headers'] for header in entry.get('headers',[])
            if header.get('key','').casefold()=='content-security-policy'}


def test_theater_is_a_real_semantic_page_with_local_navigation_and_footer():
    text,dom=page()
    assert len([el for el in dom.elements if el.tag=='main'])==1
    assert len([el for el in dom.elements if el.tag=='h1'])==1
    assert 'theater' in next(el.text for el in dom.elements if el.tag=='title').casefold()
    assert any(el.tag=='a' and el.attrs.get('href')=='/' for el in dom.elements)
    assert any(el.tag=='footer' for el in dom.elements)
    assert any(el.tag=='a' and el.attrs.get('href') in {'/nations','/nations/directory'} for el in dom.elements)


def test_curated_catalog_is_not_fixture_data_and_has_sources_credits_dates_and_viewing_scope():
    data=catalog(); assert data['version']==1 and data['films']
    ids=[f['id'] for f in data['films']]; assert len(ids)==len(set(ids)) and data['featured'] in ids
    for film in data['films']:
        assert not film['id'].startswith('fixture-')
        for key in ['title','credits','publisher','synopsis','availability','content_note']:
            assert isinstance(film[key],str) and film[key].strip()
        assert film['viewing'] in {'excerpt','trailer','full-film','official-page','short'}
        assert film['sources']
        for source in film['sources']:
            assert urlsplit(source['url']).scheme=='https' and source['title'] and source['publisher']
            assert dt.date.fromisoformat(source['checked']) <= dt.datetime.now(dt.timezone.utc).date()
        assert not (film.get('youtube_id') and film.get('pbs_id')), 'A selection has one verified player provider'


def test_every_film_is_statically_present_with_truthful_scope_and_official_watch_fallback():
    text,dom=page(); data=catalog()
    cards=[el for el in dom.elements if 'data-theater-film' in el.attrs]
    assert {el.attrs['data-theater-film'] for el in cards}=={f['id'] for f in data['films']}
    for film in data['films']:
        card=next(el for el in cards if el.attrs['data-theater-film']==film['id'])
        assert 'hidden' not in card.attrs and card.attrs.get('aria-hidden')!='true'
        assert all(phrase in card.text for phrase in [film['title'],film['credits'],film['availability'],film['content_note']])
        native=[el for el in card.descendants() if el.tag=='a' and el.attrs.get('href')==film['watch_url']]
        assert native, 'Official source remains usable without optional JavaScript'
        assert all({'noopener','noreferrer'} <= set(el.attrs.get('rel','').split()) for el in native)
        assert any(el.tag=='time' and el.attrs.get('datetime')==film['sources'][0]['checked'] for el in card.descendants())
        terms={'excerpt':['excerpt'],'trailer':['trailer'],'full-film':['full film','full-film'],
               'official-page':['official page','official-page','official source'], 'short':['short']}[film['viewing']]
        assert any(term in card.text.casefold() for term in terms), 'An excerpt or trailer must not be presented as a full film'


def test_initial_document_has_no_player_or_autoplay_and_only_local_loaded_resources():
    text,dom=page()
    assert not any(el.tag in {'iframe','object','embed'} or 'srcdoc' in el.attrs for el in dom.elements)
    assert not any('autoplay' in el.attrs for el in dom.elements)
    for el in dom.elements:
        if el.tag in {'script','img','audio','video','source','track'}:
            for key in ('src','poster'):
                value=el.attrs.get(key,'')
                assert not value.startswith(('http:','https:','//')), (el.tag,key,value)
        if el.tag=='link':
            rel=set(el.attrs.get('rel','').split())
            assert not rel & {'preconnect','dns-prefetch','prefetch','prerender'}
            if 'stylesheet' in rel or 'preload' in rel:
                assert not el.attrs.get('href','').startswith(('http:','https:','//'))
    assert not re.search(r'url\(\s*[\"\']?(?:https?:)?//',text,re.I)


def test_filter_controls_and_empty_recovery_have_labels_and_one_announcement():
    text,dom=page()
    for key,tag in [('theaterSearch','input'),('theaterTopic','select')]:
        node,=dom.by_id(key); assert node.tag==tag
        assert node.attrs.get('aria-label') or node.attrs.get('aria-labelledby') or any(el.tag=='label' and el.attrs.get('for')==key and el.text for el in dom.elements)
    empty,=dom.by_id('theaterEmpty'); assert 'hidden' in empty.attrs
    clear,=dom.by_id('theaterClear'); assert clear.tag=='button' and clear.attrs.get('type')=='button'
    status,=dom.by_id('theaterStatus'); assert status.attrs.get('role')=='status' or status.attrs.get('aria-live')=='polite'
    statuses=[el for el in dom.elements if el.attrs.get('role')=='status' or el.attrs.get('aria-live')]
    assert len([el for el in statuses if el.attrs.get('id')=='theaterStatus'])==1


def test_explicit_provider_consent_and_close_controls_exist_before_any_player():
    text,dom=page()
    load,=dom.by_id('theaterLoad'); close,=dom.by_id('theaterClose')
    assert load.tag==close.tag=='button' and load.attrs.get('type')==close.attrs.get('type')=='button'
    notice,=dom.by_id('theaterConsent')
    assert notice.text and any(term in notice.text.casefold() for term in ['ip address','browser','device','request'])
    assert 'privacy' in notice.text.casefold() or 'policies' in notice.text.casefold()
    assert not any(term in notice.text.casefold() for term in ['anonymous','no cookies','zero cookies','no data leaves'])
    assert dom.by_id('theaterPlayer') and dom.by_id('theaterPlayerStatus')


def test_embed_permissions_are_exact_and_only_on_theater_routes():
    policies=header_policies()
    for route in ['/theater','/theater.html']:
        assert route in policies, 'Theater needs explicit route-specific security policy'
        d=directives(policies[route])
        assert set(d.get('frame-src',[]))==ALLOWED_FRAMES
        assert d.get('object-src')==["'none'"] and d.get('base-uri')==["'none'"]
        assert d.get('script-src-attr')==["'none'"]
        assert not any(x in d.get('script-src',[]) for x in ["'unsafe-inline'","'unsafe-eval'",'*'])
        assert d.get('connect-src') in (["'none'"],["'self'"])
    for route,policy in policies.items():
        if route not in ['/theater','/theater.html']:
            assert not (ALLOWED_FRAMES & set(directives(policy).get('frame-src',[]))), route


def test_existing_non_theater_frame_policies_are_not_widened():
    baseline=json.loads((ART/'theater-baseline-security.json').read_text(encoding='utf-8'))
    current=header_policies()
    for route,expected in baseline['frame_directives'].items():
        assert route in current
        assert directives(current[route]).get('frame-src',[])==expected,route


def test_theater_is_in_csp_sync_and_its_meta_matches_response_policy():
    text,dom=page(); sys.path.insert(0,str(ROOT/'tools'))
    import csp_sync
    group=next((g for g in csp_sync.groups(str(ROOT)) if 'theater.html' in g['files']),None)
    assert group and set(group['sources'])=={'/theater','/theater.html'} and group['strict']
    meta=[el.attrs.get('content') for el in dom.elements if el.tag=='meta' and el.attrs.get('http-equiv','').casefold()=='content-security-policy']
    assert len(meta)==1 and meta[0]==csp_sync.meta_policy(header_policies()['/theater'])
    assert directives(meta[0])['script-src']==csp_sync.page_hashes(text)


def test_site_links_and_privacy_copy_acknowledge_opt_in_theater_providers():
    for rel in ['index.html','download.html','nations/about.html','nations/directory.html']:
        text=(ROOT/rel).read_text(encoding='utf-8'); dom=DOM(text)
        footers=[el for el in dom.elements if el.tag=='footer']
        assert footers and any(el.tag=='a' and el.attrs.get('href')=='/theater' for footer in footers for el in footer.descendants()),rel
    landing=(ROOT/'index.html').read_text(encoding='utf-8')
    assert re.search(r'href="/theater"',landing)
    assert 'YouTube' in landing and 'PBS' in landing, 'Site privacy explains optional providers'
    about=DOM((ROOT/'nations/about.html').read_text(encoding='utf-8')).root.text
    assert 'There are no analytics, no embeds' not in about
    assert 'on any page here: every request goes to zotheos.org' not in about
    assert 'This site makes no request to any other site.' not in about


@pytest.fixture
def fictional_catalog():
    return {'version':1,'updated':DAY,'featured':'fixture-river',
        'topics':[{'id':'land','name':'Land And Water'}],
        'films':[{'id':'fixture-river','title':'River Memory <img src=x onerror=bad()>','year':2022,'runtime':'20m',
                  'credits':'A Fictional Filmmaker & Friend','publisher':'Fictional Public Media',
                  'synopsis':'A fictional river account <script>bad()</script>.','topics':['land'],
                  'watch_url':'https://publisher.example.test/film','viewing':'excerpt',
                  'availability':'Official excerpt; full film availability is separate.',
                  'content_note':'Fictional historical discrimination.','youtube_id':'abcdefghijk','pbs_id':None,
                  'sources':[{'url':'https://publisher.example.test/film','title':'Official film page',
                              'publisher':'Fictional Public Media','checked':DAY}]}]}


def fixture_build(tmp_path,data):
    builder=ROOT/'tools/theater_build.py'
    assert builder.is_file(), 'The real Theater builder must exist before renderer acceptance can pass'
    folder=tmp_path/'data/theater'; folder.mkdir(parents=True,exist_ok=True)
    (folder/'films.json').write_text(json.dumps(data),encoding='utf-8')
    return subprocess.run([PYTHON,str(builder),'--root',str(tmp_path)],capture_output=True,text=True,
                          env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})


def test_real_fixture_builder_escapes_content_and_preserves_official_link_without_assets(tmp_path,fictional_catalog):
    result=fixture_build(tmp_path,fictional_catalog)
    assert result.returncode==0,result.stdout+result.stderr
    text=(tmp_path/'theater.html').read_text(encoding='utf-8'); dom=DOM(text)
    assert fictional_catalog['films'][0]['title'] in dom.root.text
    assert '&lt;img' in text and '&lt;script&gt;' in text
    assert not any(el.tag=='img' and el.attrs.get('src')=='x' for el in dom.elements)
    assert not any(el.tag=='script' and el.text=='bad()' for el in dom.elements)
    assert any(el.tag=='a' and el.attrs.get('href')=='https://publisher.example.test/film' for el in dom.elements)


@pytest.mark.parametrize('bad',['javascript:alert(1)','http://publisher.example.test/film','//publisher.example.test/film'])
def test_builder_rejects_unsafe_watch_urls_before_publishing(tmp_path,fictional_catalog,bad):
    fictional_catalog['films'][0]['watch_url']=bad
    result=fixture_build(tmp_path,fictional_catalog)
    assert result.returncode!=0 and not (tmp_path/'theater.html').exists()


@pytest.mark.parametrize('provider,value',[('youtube_id','bad-id<script>'),('pbs_id','3067357496/evil')])
def test_builder_rejects_invalid_provider_identifiers(tmp_path,fictional_catalog,provider,value):
    film=fictional_catalog['films'][0]; film['youtube_id']=None;film[provider]=value
    result=fixture_build(tmp_path,fictional_catalog)
    assert result.returncode!=0 and not (tmp_path/'theater.html').exists()


def test_builder_rejects_two_providers_for_one_selection(tmp_path,fictional_catalog):
    fictional_catalog['films'][0]['pbs_id']='3067357496'
    result=fixture_build(tmp_path,fictional_catalog)
    assert result.returncode!=0 and not (tmp_path/'theater.html').exists()


def test_builder_rejects_fabricated_future_source_check(tmp_path,fictional_catalog):
    fictional_catalog['films'][0]['sources'][0]['checked']=(dt.datetime.now(dt.timezone.utc).date()+dt.timedelta(days=1)).isoformat()
    result=fixture_build(tmp_path,fictional_catalog)
    assert result.returncode!=0 and not (tmp_path/'theater.html').exists()


def test_actual_optional_script_passes_independent_consent_and_filter_behavior():
    node=shutil.which('node')
    if not node: pytest.skip('Node unavailable')
    companion=ART/'theater-interaction-acceptance.cjs'
    result=subprocess.run([node,str(companion),str(ROOT/'static/theater/theater.js')],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
