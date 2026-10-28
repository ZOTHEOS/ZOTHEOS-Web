"""Real game-builder regression: early prepaint/style blocks must not replace the engine.

The CLI tests copy the actual builder into a tiny fictional private page and use the installed
real minifier/Acorn. They do not modify or run the production game and do not fetch dependencies.
"""
from pathlib import Path
from html.parser import HTMLParser
import json,os,re,shutil,subprocess,sys
import pytest

R=Path(os.environ.get('ZOTHEOS_TEST_REPO',str(Path(__file__).resolve().parents[2])))
PREPAINT="window.__fixtureBefore = 'PREPAINT_SENTINEL';"
EXTRA_STYLE='.fixture-sky { color: #123456; }'
TAIL="window.ZOTHEOSFixtureEngine.after = 'AFTER_SENTINEL';"
SOURCE='''<!doctype html><html><head>
<script id="site-theme-prepaint">'''+PREPAINT+'''</script>
<style id="site-appearance-game">'''+EXTRA_STYLE+'''</style>
<style>
  .fixture-ground { background: #010203; }
</style>
</head><body><p>Fictional builder fixture, never published.</p>
<script>
(function (global) {
  'use strict';
  var CSS = '.fixture-overlay { color: #abcdef; }';
  global.ZOTHEOSFixtureEngine = {ready: 'ENGINE_SENTINEL', css: CSS};
  /*T*/global.__fixtureTestHook = 'HOOK_SENTINEL';/*T*/
})(window);
</script>
<script id="fixture-after">'''+TAIL+'''</script>
</body></html>'''

class Scripts(HTMLParser):
    def __init__(self,s):
        super().__init__();self.rows=[];self.active=None;self.feed(s)
    def handle_starttag(self,t,attrs):
        if t=='script':self.active={'attrs':dict(attrs),'body':''}
    def handle_data(self,s):
        if self.active is not None:self.active['body']+=s
    def handle_endtag(self,t):
        if t=='script'and self.active is not None:self.rows.append(self.active);self.active=None

def dependencies():
    node=shutil.which('node')
    ug=Path(os.environ.get('ZOTHEOS_UGLIFYJS',str(Path.home()/'AppData/Roaming/npm/node_modules/n8n/node_modules/uglify-js/bin/uglifyjs')))
    acorn=ug.parent.parent.parent/'acorn'
    if not node or not ug.is_file() or not acorn.is_dir():pytest.skip('Installed Node/Uglify/Acorn required for real isolated game-builder fixture; no dependency download.')
    return node,ug

@pytest.mark.parametrize('dev',[False,True])
def test_real_builder_preserves_prepaint_and_selects_nonempty_engine_after_earlier_script_and_style(tmp_path,dev):
    node,ug=dependencies();shutil.copyfile(R/'game/build.py',tmp_path/'build.py');(tmp_path/'index.src.html').write_text(SOURCE,encoding='utf8')
    env=os.environ.copy();env['PATH']=str(Path(node).parent)+os.pathsep+env.get('PATH','')
    run=subprocess.run([sys.executable,'-B',str(tmp_path/'build.py'),str(ug),*(['--dev']if dev else[])],cwd=tmp_path,env=env,capture_output=True,text=True,timeout=30)
    assert run.returncode==0,run.stdout+run.stderr
    output=(tmp_path/('index.dev.html'if dev else'index.html')).read_text(encoding='utf8')
    scripts=Scripts(output).rows
    assert len(scripts)==3
    assert scripts[0]['attrs'].get('id')=='site-theme-prepaint'and scripts[0]['body']==PREPAINT
    assert '<style id="site-appearance-game">'+EXTRA_STYLE+'</style>'in output
    assert scripts[2]['attrs'].get('id')=='fixture-after'and scripts[2]['body']==TAIL
    engine=scripts[1]['body'].strip();assert engine and'ENGINE_SENTINEL'in engine
    assert 0<len(engine.encode('utf8'))<=100000
    assert ('HOOK_SENTINEL'in engine)==dev
    assert 'PREPAINT_SENTINEL'not in engine and'AFTER_SENTINEL'not in engine
    assert 'ES5 ok'in run.stdout
    executor="const vm=require('node:vm'),fs=require('node:fs'),rows=JSON.parse(fs.readFileSync(0,'utf8'));const w={};for(const code of rows)vm.runInNewContext(code,{window:w},{timeout:1000});console.log(JSON.stringify(w));"
    executed=subprocess.run([node,'-e',executor],input=json.dumps([r['body']for r in scripts]),capture_output=True,text=True,timeout=10)
    assert executed.returncode==0,executed.stdout+executed.stderr
    state=json.loads(executed.stdout)
    assert state['__fixtureBefore']=='PREPAINT_SENTINEL'
    assert state['ZOTHEOSFixtureEngine']=={'ready':'ENGINE_SENTINEL','css':'.fixture-overlay { color: #abcdef; }','after':'AFTER_SENTINEL'}
    assert ('__fixtureTestHook'in state)==dev

def test_generated_production_page_has_a_real_engine_within_unchanged_js_ceiling():
    rows=Scripts((R/'game/index.html').read_text(encoding='utf8')).rows
    engines=[r['body']for r in rows if re.search(r'\bZTH_GAME\s*=',r['body'])]
    assert len(engines)==1,'Exactly one compiled game API owner must remain in the generated page'
    engine=engines[0].strip();assert engine and'ZTH_GAME'in engine
    assert 0<len(engine.encode('utf8'))<=100000,'Do not confuse an empty/prepaint script with the game or waive its JS ceiling'
    assert 'zotheos_landing_theme'not in engine,'Appearance adapter belongs outside the minified game engine'
