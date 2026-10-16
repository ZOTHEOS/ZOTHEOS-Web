"""Story selection browses a bounded silent preview; actual Play/Sound takes control.

These cases were written independently after root's real-browser observation
found a navigation gesture incorrectly classified as deliberate playback.
"""
import os
from pathlib import Path
import subprocess
import shutil

import pytest

ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', str(Path(__file__).resolve().parents[2])))


@pytest.mark.parametrize('scenario', [
    'poster-desktop-cap', 'poster-phone-cap', 'poster-offview-pause',
    'poster-hidden-tab-pause', 'next-story-remains-capped',
    'new-poster-preview-is-muted-after-earlier-sound',
    'actual-play-takeover-is-deliberate', 'actual-sound-takeover-is-deliberate',
    'native-play-takeover-is-deliberate',
])
def test_story_navigation_and_deliberate_playback_have_distinct_boundaries(scenario):
    node = shutil.which('node')
    assert node, 'Node.js is required for the actual Theater preview-boundary gate'
    script = Path(__file__).with_name('theater-story-preview-boundaries.cjs')
    run = subprocess.run([str(node), str(script), str(ROOT), scenario],
                         capture_output=True, text=True, encoding='utf-8')
    assert run.returncode == 0, run.stdout + run.stderr
