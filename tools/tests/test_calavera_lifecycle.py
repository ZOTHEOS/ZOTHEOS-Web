"""Independent event-boundary regression; browser geometry is checked separately."""
import json,os,shutil,subprocess
from pathlib import Path
R=Path(os.environ.get('ZOTHEOS_TEST_REPO',str(Path(__file__).resolve().parents[2])))

def test_decorative_motion_has_bounded_work_and_stops_when_unwanted(tmp_path):
    node=shutil.which('node');assert node,'Node.js is required'
    result=tmp_path/'lifecycle.json'
    run=subprocess.run([node,str(R/'tools/tests/calavera-lifecycle.cjs'),str(R/'static/appearance/calavera.js'),str(result)],capture_output=True,text=True,timeout=15)
    assert run.returncode==0,run.stdout+run.stderr
    report=json.loads(result.read_text(encoding='utf-8'))
    assert report['passed']==34 and report['failed']==0
    assert report['stats']['peak']<=1
