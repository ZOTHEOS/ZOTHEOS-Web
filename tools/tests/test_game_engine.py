"""Acceptance of real ring passes, catch/return behavior and fair Drop hazards."""
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import ROOT


@pytest.mark.parametrize('runner', ['echo-acceptance.js', 'test_drop_challenge.js'])
def test_game_engine_acceptance(runner):
    node = shutil.which('node')
    if not node:
        pytest.skip('node is not installed')
    result = subprocess.run([node, str(Path(__file__).with_name(runner)),
                             str(Path(ROOT)/'game/index.src.html')],
                            capture_output=True, text=True, encoding='utf-8', timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr
