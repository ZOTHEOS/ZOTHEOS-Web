"""Security regression contract for content-checked same-origin cached appearance scripts.

Tests use fictional private files only. No source fetch, real site change or broad CSP permission.
"""
from pathlib import Path
import base64,hashlib,json,os,subprocess,sys
import pytest

R=Path(os.environ.get('ZOTHEOS_TEST_REPO',str(Path(__file__).resolve().parents[2])))
BODY=b"/* Fictional test asset, never published. */\nwindow.exampleTheme = 'calavera';\n"
HASH='sha256-'+base64.b64encode(hashlib.sha256(BODY).digest()).decode('ascii')
REL='/static/theme.'+hashlib.sha256(BODY).hexdigest()[:8]+'.js'
POLICY="default-src 'none'; script-src 'none'; script-src-attr 'none'; connect-src 'none'; object-src 'none'; frame-ancestors 'none'"

def fixture(tmp_path,src=REL,integrity=HASH,body=BODY):
    asset=tmp_path/REL.lstrip('/');asset.parent.mkdir(parents=True,exist_ok=True);asset.write_bytes(body)
    attrs=f' src="{src}"'+(''if integrity is None else f' integrity="{integrity}"')
    page=f'<!doctype html><html><head><meta http-equiv="Content-Security-Policy" content="{POLICY}"><script{attrs}></script></head><body>Fictional test only.</body></html>'
    (tmp_path/'index.html').write_text(page,encoding='utf-8')
    conf={'headers':[{'source':'/','headers':[{'key':'Content-Security-Policy','value':POLICY}]}]}
    (tmp_path/'vercel.json').write_text(json.dumps(conf,indent=2)+'\n',encoding='utf-8')
    return asset

def run(root,check=False):
    return subprocess.run([sys.executable,'-B',str(R/'tools/csp_sync.py'),'--root',str(root),*(['--check']if check else[])],capture_output=True,text=True,timeout=10)

def policy(root):
    return json.loads((root/'vercel.json').read_text(encoding='utf-8'))['headers'][0]['headers'][0]['value']

def directives(pol):return {p.split()[0]:p.split()[1:]for p in pol.split(';')if p.strip()}

def test_valid_same_origin_asset_is_hash_authorized_without_broader_origins(tmp_path):
    fixture(tmp_path);r=run(tmp_path);assert r.returncode==0,r.stdout+r.stderr
    parsed=directives(policy(tmp_path));assert parsed['script-src']==["'"+HASH+"'"]
    assert parsed['connect-src']==["'none'"] and parsed['object-src']==["'none'"]
    assert "'self'" not in parsed['script-src'] and "'unsafe-inline'" not in parsed['script-src']
    assert HASH in (tmp_path/'index.html').read_text(encoding='utf-8')
    assert run(tmp_path,True).returncode==0

def test_modified_cached_asset_fails_before_any_write(tmp_path):
    asset=fixture(tmp_path);r=run(tmp_path);assert r.returncode==0,r.stdout+r.stderr
    asset.write_bytes(BODY+b'/* changed */')
    pins={p:p.read_bytes()for p in [tmp_path/'index.html',tmp_path/'vercel.json']}
    rejected=run(tmp_path);assert rejected.returncode!=0,'Changed bytes must not be accepted under stale integrity'
    assert all(p.read_bytes()==value for p,value in pins.items()),'Invalid external integrity must not rewrite policy'

@pytest.mark.parametrize('src,integrity',[
    (REL,None),(REL,'sha256-AAAA'),(REL,'sha256-'+base64.b64encode(b'X'*32).decode()),
    ('https://untrusted.example/theme.js',HASH),('//untrusted.example/theme.js',HASH),
    ('/static/../../outside.js',HASH),('/static/%2e%2e/outside.js',HASH),('/missing.js',HASH)
])
def test_invalid_integrity_or_out_of_root_asset_is_rejected_without_policy_rewrite(tmp_path,src,integrity):
    fixture(tmp_path,src,integrity)
    pins={p:p.read_bytes()for p in [tmp_path/'index.html',tmp_path/'vercel.json']}
    rejected=run(tmp_path);assert rejected.returncode!=0,'Do not silently accept or ignore invalid cached-script authorization'
    assert all(p.read_bytes()==value for p,value in pins.items())
