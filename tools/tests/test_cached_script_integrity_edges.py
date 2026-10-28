"""Independent parser and realpath edge cases, fictional files only."""
from pathlib import Path
import re,json
import pytest
from test_cached_script_integrity import fixture,run,REL,HASH,BODY,POLICY

@pytest.mark.parametrize('tag',[
    f'<script src="https://untrusted.example/asset.js" src="{REL}" integrity="{HASH}"></script>',
    f'<script src="{REL}" integrity="sha256-AAAA" integrity="{HASH}"></script>'
])
def test_duplicate_source_or_integrity_cannot_diverge_from_browser_first_attribute(tmp_path,tag):
    fixture(tmp_path)
    p=tmp_path/'index.html';s=p.read_text(encoding='utf8');p.write_text(re.sub(r'<script\b[^>]*></script>',lambda _:tag,s),encoding='utf8')
    before={p:p.read_bytes()for p in [tmp_path/'index.html',tmp_path/'vercel.json']}
    r=run(tmp_path);assert r.returncode!=0,'Ambiguous duplicate attributes must be rejected, not last-value accepted'
    assert all(p.read_bytes()==b for p,b in before.items()),'Parser rejection must precede policy rewrites'

@pytest.mark.parametrize('where',['inside-site-data','outside-site'])
def test_symlink_does_not_expand_the_declared_static_asset_boundary(tmp_path,where):
    fixture(tmp_path,src='/static/link.js')
    if where=='inside-site-data':
        target=tmp_path/'data/private-source.js';target.parent.mkdir()
    else:target=tmp_path.parent/(tmp_path.name+'-outside-script.js')
    target.write_bytes(BODY)
    try:(tmp_path/'static/link.js').symlink_to(target)
    except OSError as e:pytest.skip('This test host cannot create an owned fixture symlink: '+str(e))
    before={p:p.read_bytes()for p in [tmp_path/'index.html',tmp_path/'vercel.json']}
    r=run(tmp_path);assert r.returncode!=0,'Resolved asset must stay in real /static and the real site root'
    assert all(p.read_bytes()==b for p,b in before.items())

def test_static_directory_cannot_redirect_the_allowed_boundary_into_site_data(tmp_path):
    data=tmp_path/'data';data.mkdir();(data/'example.js').write_bytes(BODY)
    try:(tmp_path/'static').symlink_to(data,target_is_directory=True)
    except OSError as e:pytest.skip('This test host cannot create an owned fixture directory symlink: '+str(e))
    page=f'<html><head><meta http-equiv="Content-Security-Policy" content="{POLICY}"><script src="/static/example.js" integrity="{HASH}"></script></head><body>Fictional fixture only.</body></html>'
    (tmp_path/'index.html').write_text(page,encoding='utf8')
    (tmp_path/'vercel.json').write_text(json.dumps({'headers':[{'source':'/','headers':[{'key':'Content-Security-Policy','value':POLICY}]}]},indent=2)+'\n',encoding='utf8')
    before={p:p.read_bytes()for p in [tmp_path/'index.html',tmp_path/'vercel.json']}
    r=run(tmp_path);assert r.returncode!=0,'A static-directory link must not redefine the asset boundary as private site data'
    assert all(p.read_bytes()==b for p,b in before.items())

@pytest.mark.parametrize('src',[
    'https:https://untrusted.example/theme.js',
    '/static/%5c%5cuntrusted.example%5casset.js',
    '/static/theme.js%00',
    '/static/%252e%252e/outside.js'
])
def test_malformed_double_scheme_and_noncanonical_paths_fail_without_rewrite(tmp_path,src):
    fixture(tmp_path,src=src)
    before={p:p.read_bytes()for p in [tmp_path/'index.html',tmp_path/'vercel.json']}
    r=run(tmp_path);assert r.returncode!=0
    assert all(p.read_bytes()==b for p,b in before.items())
