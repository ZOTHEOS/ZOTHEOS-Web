"""Independent follow-up failure cases; publisher URLs and names are fictional."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from test_theater_acceptance import fixture_build, fictional_catalog

@pytest.mark.parametrize('field', ['watch_url','source_url'])
@pytest.mark.parametrize('destination,accepted', [
    ('https://publisher.example.test:notaport/film',False),
    ('https://publisher.example.test:65536/film',False),
    ('https://publisher.example.test:99999/film',False),
    ('https://publisher.example.test:-1/film',False),
    ('https://publisher.example.test:0/film',False),
    ('https://publisher.example.test/film',True),
    ('https://publisher.example.test:443/film',True),
    ('https://publisher.example.test:8443/film',True),
    ('https://publisher.example.test:65535/film',True),
])
def test_port_boundaries_use_the_real_renderer(tmp_path,fictional_catalog,field,destination,accepted):
    film=fictional_catalog['films'][0]
    if field=='watch_url': film[field]=destination
    else: film['sources'][0]['url']=destination
    result=fixture_build(tmp_path,fictional_catalog)
    published=(tmp_path/'theater.html').is_file()
    assert (result.returncode==0 and published)==accepted,result.stdout+result.stderr
    if not accepted: assert not published

def test_accent_search_preserves_original_names_and_respects_other_filters():
    node=shutil.which('node')
    if not node: pytest.skip('Node unavailable')
    root=Path(os.environ.get('ZOTHEOS_TEST_REPO',Path(__file__).resolve().parents[2]))
    script=Path(__file__).with_name('theater-accent-search-regressions.cjs')
    result=subprocess.run([node,str(script),str(root/'static/theater/theater.js')],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
    focus=Path(__file__).with_name('theater-focus-regressions.cjs')
    result=subprocess.run([node,str(focus),str(root/'static/theater/theater.js')],capture_output=True,text=True,encoding='utf-8')
    assert result.returncode==0,result.stdout+result.stderr
