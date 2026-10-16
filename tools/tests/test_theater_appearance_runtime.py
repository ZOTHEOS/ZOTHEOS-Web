"""Optional Appearance DOM contract. No browser, provider or network execution."""
import json
import os
from pathlib import Path
import shutil
import subprocess

R=Path(os.environ.get('ZOTHEOS_TEST_REPO',str(Path(__file__).resolve().parents[2])))

def test_scoped_appearance_runtime_preserves_shared_preferences_native_focus_and_public_text():
    node=shutil.which('node')
    assert node,'Node.js is required for the website interaction contract.'
    script=Path(__file__).with_name('theater-appearance-runtime.cjs')
    run=subprocess.run([node,str(script),str(R)],capture_output=True,text=True,timeout=20)
    assert run.returncode==0,run.stdout+run.stderr
    result=json.loads(run.stdout)
    assert result['scopedScriptPresent'] and result['passed']==22 and result['failed']==0
