"""Run the portable intro lifecycle acceptance checks without a browser or media decoding."""
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import ROOT


def test_intro_lifecycle_acceptance():
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    script = Path(__file__).with_suffix(".cjs")
    result = subprocess.run(
        [node, str(script), str(Path(ROOT) / "index.html")],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
