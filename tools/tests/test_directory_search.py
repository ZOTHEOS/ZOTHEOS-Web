"""Name search must not conflate Ute with Paiute or interpret a query as a pattern."""
from pathlib import Path
import shutil
import subprocess

import pytest
from conftest import ROOT


def test_native_name_word_search_and_literal_queries():
    node = shutil.which('node')
    if not node:
        pytest.skip('node is not installed')
    source = (Path(ROOT) / 'tools/nations/partials/appearance.js').read_text(encoding='utf-8')
    function = source[source.index('  function directoryMatches('):source.index('  function filter()', source.index('  function directoryMatches('))]
    checks = """
const assert=require('assert');
assert(directoryMatches('southern ute indian tribe',['southern','ute']));
assert(!directoryMatches('san juan southern paiute tribe',['southern','ute']));
assert(directoryMatches('ute mountain ute tribe',['ute','tribe']));
assert(directoryMatches('fort sill-chiricahua-warm springs-apache tribe',['chiricahua','apache']));
assert(directoryMatches('yaqit ʔa·knuqⱡi\'it',['ʔa·knuq']));
assert(directoryMatches('every name',['']));
assert(!directoryMatches('southern ute indian tribe',['.*']));
assert(!directoryMatches('southern ute indian tribe',['[ute]']));
"""
    # The apostrophe in this name is intentionally passed as a literal JS string.
    checks = checks.replace("'yaqit ʔa·knuqⱡi'it'", '"yaqit ʔa·knuqⱡi\'it"')
    result = subprocess.run([node, '-e', function + checks], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr
