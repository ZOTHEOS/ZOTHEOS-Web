"""Independent fifth-appearance semantic and early-paint contract. No browser geometry claim."""
from pathlib import Path
from html.parser import HTMLParser
import json,os,shutil,subprocess
import pytest

R=Path(os.environ.get('ZOTHEOS_TEST_REPO',str(Path(__file__).resolve().parents[2])))
A=Path(__file__).parent
EXPECTED=[('', 'Sovereign Skeleton'),('maya','Maya Radiance'),('codex','Living Codex'),('skeleton','Obsidian Ember'),('calavera','Calavera Nocturne')]

class Markup(HTMLParser):
    def __init__(self,s):
        super().__init__();self.els=[];self.scripts=[];self.active=None;self.ordinal=0;self.first_style=None;self.feed(s)
    def handle_starttag(self,tag,attrs):
        self.ordinal+=1;attrs=dict(attrs);self.els.append((tag,attrs))
        if tag=='script':self.active={'attrs':attrs,'text':'','ordinal':self.ordinal}
        if (tag=='style' or tag=='link' and attrs.get('rel')=='stylesheet') and self.first_style is None:self.first_style=self.ordinal
    def handle_data(self,data):
        if self.active is not None:self.active['text']+=data
    def handle_endtag(self,tag):
        if tag=='script' and self.active is not None:self.scripts.append(self.active);self.active=None

@pytest.mark.parametrize('rel',['index.html','tools/nations/partials/header.html','theater.html'])
def test_fifth_theme_is_a_labelled_native_radio_without_losing_existing_choices(rel):
    dom=Markup((R/rel).read_text(encoding='utf-8'))
    radios=[(tag,a) for tag,a in dom.els if a.get('role')=='radio' and 'data-set'in a]
    assert [(a['data-set'],a.get('aria-label'))for _,a in radios]==EXPECTED
    assert all(tag=='button' and a.get('type')=='button' and a.get('title') for tag,a in radios)
    assert sum(a.get('aria-checked')=='true' for _,a in radios)==1
    assert sum(a.get('tabindex')=='0' for _,a in radios)==1

def _early_script(rel,tmp_path):
    path=R/rel;dom=Markup(path.read_text(encoding='utf-8'));options=[]
    for script in dom.scripts:
        code=script['text'];src=script['attrs'].get('src')
        if src and src.startswith('/') and not src.startswith('//'):
            p=R/src.lstrip('/').split('?')[0]
            if p.is_file():code=p.read_text(encoding='utf-8')
        if 'zotheos_landing_theme' in code:options.append((script,code))
    assert options,'Each page must adopt the shared saved appearance before first paint'
    script,code=options[0]
    assert dom.first_style is None or script['ordinal']<dom.first_style,'Apply saved theme before visible stylesheet content'
    target=tmp_path/'early-script.js';target.write_text(code,encoding='utf-8');return target

@pytest.mark.parametrize('rel',['index.html','theater.html','nations/coushatta-tribe-of-louisiana-us-la.html','download.html','game/index.html'])
@pytest.mark.parametrize('reduced',[False,True])
def test_saved_fifth_theme_is_applied_before_paint_without_overriding_reduced_motion(rel,reduced,tmp_path):
    node=shutil.which('node');assert node,'Node.js required'
    script=_early_script(rel,tmp_path)
    run=subprocess.run([node,str(A/'prepaint-runtime.cjs'),str(script),'calavera','reduce'if reduced else'normal'],capture_output=True,text=True,timeout=5)
    assert run.returncode==0,run.stdout+run.stderr
    attrs=json.loads(run.stdout)['attrs']
    assert attrs.get('data-theme')=='calavera'
    assert attrs.get('data-motion')==('still'if reduced else'living')

def test_fifth_shared_theme_behavior_and_legacy_preferences():
    node=shutil.which('node');assert node,'Node.js required'
    run=subprocess.run([node,str(A/'calavera-theme-runtime.cjs'),str(R)],capture_output=True,text=True,timeout=20)
    assert run.returncode==0,run.stdout+run.stderr
    result=json.loads(run.stdout);assert result['passed']==8 and result['failed']==0
