"""Independent provider-command ordering and replacement regressions.

Neutral browser/provider primitives and fixed fictional records exercise the real
runtime. These checks do not certify remote provider playback or browser layout.
The original sealed62-case presentation contract remains unchanged.
"""
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', str(Path(__file__).resolve().parents[2])))


@pytest.mark.parametrize('scenario', [
    'mute-before-play',
    'opposing-sound-intents',
    'replacement-resets-pending-command',
    'old-frame-message-after-replacement',
    'source-only-light-restoration',
    'native-pause-persists',
    'save-data-manual-fallback',
])
def test_real_provider_command_order_and_frame_replacement(scenario):
    node = Path(r'C:\nvm4w\nodejs\node.exe')
    assert node.is_file(), 'The real Node runtime is required for this gate'
    script = Path(__file__).with_name('theater-command-order-supplement.cjs')
    run = subprocess.run([str(node), str(script), str(ROOT), scenario],
                         capture_output=True, text=True, encoding='utf-8')
    assert run.returncode == 0, run.stdout + run.stderr
