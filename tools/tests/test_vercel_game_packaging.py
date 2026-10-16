"""Deployment packaging for real game manifests, shards and private sources.

Uses Git's ignore engine in scratch because Vercel documents .vercelignore as
gitignore-like: https://vercel.com/docs/deployments/vercel-ignore
No project files, generated claims or source receipts are changed by this test.
"""
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys

import pytest

ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT / 'tools'))
import game_nations as game


def ignored_paths(tmp_path, paths):
    """Apply the actual deployment exclusion bytes with an independent matcher."""
    git = shutil.which('git')
    assert git, 'Git is required for the deployment packaging acceptance test.'
    paths = sorted(set(paths))
    scratch = tmp_path / 'deployment-package'
    scratch.mkdir()
    for relative in paths:
        path = PurePosixPath(relative)
        assert not path.is_absolute() and '..' not in path.parts
        target = scratch.joinpath(*path.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'')
    (scratch / '.gitignore').write_bytes((ROOT / '.vercelignore').read_bytes())
    env = {key: value for key, value in os.environ.items()
           if key.upper() in {'PATH', 'SYSTEMROOT', 'WINDIR', 'TMP', 'TEMP', 'COMSPEC',
                              'PATHEXT', 'SYSTEMDRIVE', 'PROGRAMFILES', 'PROGRAMFILES(X86)'}}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS='0')
    metadata = tmp_path / 'ignore-engine'
    subprocess.run([git, '-c', 'init.defaultBranch=main', 'init', '--bare', '-q', str(metadata)],
                   check=True, capture_output=True, env=env)
    result = subprocess.run([git, '--git-dir=' + str(metadata), '--work-tree=' + str(scratch),
                             '-c', 'core.bare=false', '-c', 'core.excludesFile=' + os.devnull,
                             'check-ignore', '--no-index', '--stdin', '-z'],
                            input=('\x00'.join(paths) + '\x00').encode('utf8'),
                            capture_output=True, env=env)
    assert result.returncode in (0, 1), result.stderr.decode('utf8', errors='replace')
    return {path.decode('utf8') for path in result.stdout.split(b'\x00') if path}


def manifest_assets(root):
    paths = {'game/index.html'}
    for name, prefix in [('nations', 'n'), ('history', 'h')]:
        relative = 'game/' + name + '.json'
        paths.add(relative)
        doc = json.loads((root / relative).read_text(encoding='utf8'))
        for entry in doc.get('shards', []):
            assert re.fullmatch(prefix + r'-[a-f0-9]{32}\.json', entry[0])
            path = 'game/data/' + entry[0]
            assert (root / path).is_file(), 'A manifest references a missing generated asset: ' + path
            paths.add(path)
    return paths


def test_every_current_game_manifest_and_referenced_shard_is_packaged(tmp_path):
    assets = manifest_assets(ROOT)
    excluded = ignored_paths(tmp_path, assets)
    assert not excluded, 'Deployment excludes live game assets: ' + ', '.join(sorted(excluded))


def test_real_exporter_quick_and_history_shards_remain_packaged(tmp_path, monkeypatch):
    # Exercise both real partition branches even while history still fits one file.
    monkeypatch.setattr(game, 'LIMIT', 50000)
    monkeypatch.setattr(game, 'HISTORY_LIMIT', 12000)
    outputs, _, skipped = game.build(str(ROOT))
    assert not skipped
    for name in ('nations', 'history'):
        assert json.loads(outputs['game/' + name + '.json'])['shards']
    excluded = ignored_paths(tmp_path, set(outputs) | {'game/index.html'})
    assert not excluded, 'Deployment excludes real generated quick/history assets: ' + ', '.join(sorted(excluded))


def test_all_root_private_sources_and_game_development_files_stay_excluded(tmp_path):
    private = {path.relative_to(ROOT).as_posix()
               for folder in ('data', 'tools', 'docs', '.github')
               for path in (ROOT / folder).rglob('*') if path.is_file()}
    private.update(path.relative_to(ROOT).as_posix() for path in ROOT.rglob('*.md')
                   if '.git' not in path.parts)
    private.update(relative for relative in ('game/index.dev.html', 'game/index.src.html', 'game/build.py')
                   if (ROOT / relative).is_file())
    assert any(path.startswith('data/nations/research/') for path in private)
    assert 'data/nations/nations.json' in private and 'game/index.src.html' in private
    exposed = private - ignored_paths(tmp_path, private)
    assert not exposed, 'Deployment exposes private source or development files: ' + ', '.join(sorted(exposed))
