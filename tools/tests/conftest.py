"""Shared fixtures for the /nations tests (py -3.10 -m pytest tools/tests). Builds run in scratch copies, never in
the tree."""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
sys.dont_write_bytecode = True


def run(root, *args):
    p = subprocess.run([sys.executable, *args], cwd=root, capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


@pytest.fixture()
def scratch():
    import nations_build
    tmp = nations_build.scratch_copy(ROOT)
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def herald_js(root=ROOT):
    hub = open(os.path.join(root, "nations.html"), encoding="utf-8").read()
    return next(s for s in re.findall(r"<script>(.*?)</script>", hub, re.S) if "ZN_TEST" in s)


def node_eval(body, data):
    """Run herald.js in node (no document, so it exports its pure functions as ZN_TEST) and then body, which reads
    DATA and prints JSON."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        js, dp = os.path.join(td, "t.js"), os.path.join(td, "d.json")
        with open(dp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        with open(js, "w", encoding="utf-8") as f:
            f.write(herald_js() + "\nconst DATA = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));\n"
                    "const ZN = globalThis.ZN_TEST;\n" + body)
        p = subprocess.run([node, js, dp], capture_output=True, text=True, encoding="utf-8")
        assert p.returncode == 0, p.stderr
        return json.loads(p.stdout)
