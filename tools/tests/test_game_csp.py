"""A game rebuild cannot silently leave blocking script or overlay-style policies."""
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from conftest import ROOT


def test_game_build_drift_is_detected_and_every_route_keeps_strict_hashes(tmp_path):
    game = tmp_path/'game'
    game.mkdir()
    script, page_css, overlay = 'window.game=true;', 'body{background:#000}', '.overlay{color:#fff}'
    page = game/'index.html'
    source = game/'index.src.html'
    page.write_text(f'<style>{page_css}</style><script>{script}</script>', encoding='utf-8')
    source.write_text("var CSS = '" + overlay + "';", encoding='utf-8')
    aliases = ['/game', '/game/', '/game/index', '/game/index.html']
    policy = "default-src 'none'; script-src 'none'; style-src 'none'; connect-src 'self'; frame-ancestors 'none'"
    config = tmp_path/'vercel.json'
    config.write_text(json.dumps({'headers': [{'source': a, 'headers': [{'key': 'Content-Security-Policy', 'value': policy}]} for a in aliases]}), encoding='utf-8')

    def run(check=False):
        args = [sys.executable, str(Path(ROOT)/'tools/csp_sync.py'), '--root', str(tmp_path)]
        return subprocess.run(args + (['--check'] if check else []), capture_output=True, text=True)

    assert run().returncode == 0
    assert run(True).returncode == 0
    changed = page.read_text(encoding='utf-8').replace(script, 'window.game=false;')
    page.write_text(changed, encoding='utf-8')
    source.write_text("var CSS = '.overlay{color:#eee}';", encoding='utf-8')
    before = config.read_bytes()
    check = run(True)
    assert check.returncode == 1 and 'hashes are stale' in check.stdout
    assert config.read_bytes() == before
    assert run().returncode == 0 and run(True).returncode == 0
    expected = ["'sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode() + "'"
                for body in ['window.game=false;', page_css, '.overlay{color:#eee}']]
    entries = json.loads(config.read_text(encoding='utf-8'))['headers']
    assert {e['source'] for e in entries} == set(aliases)
    for entry in entries:
        current = entry['headers'][0]['value']
        assert all(h in current for h in expected)
        assert "connect-src 'self'" in current and "frame-ancestors 'none'" in current
        assert "'unsafe-inline'" not in current
