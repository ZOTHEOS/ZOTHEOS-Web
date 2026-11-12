"""Link To This Search: static enhancement markup and URL behavior against the actual directory script.

The script check uses fictional records in a DOM fixture. Browser, device and assistive-technology review
is separate and is not claimed here.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import pytest

ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/tests'))
import nations_directory as D
from test_indigenous_pathways import tree


def page():
    import nations_build as B
    b = B.Builder(str(ROOT))
    b.sp = lambda key, body, description: body
    return tree(D.page(b))


def ancestors(node):
    parent = node.parent
    while parent is not None:
        yield parent
        parent = parent.parent


def built():
    return tree((ROOT / 'nations/directory.html').read_text(encoding='utf-8'))


@pytest.mark.parametrize('load', [page, built], ids=['renderer', 'built-page'])
def test_link_is_an_enhancement_only_native_anchor_with_a_privacy_note(load):
    doc = load()
    links = [n for n in doc.walk() if n.attrs.get('id') == 'directoryShareLink']
    assert len(links) == 1
    link = links[0]
    assert link.tag == 'a' and link.text.strip() == 'Link To This Search'
    assert link.attrs.get('href') == '/nations/directory#directoryNames'
    assert 'directoryTools' in [a.attrs.get('id') for a in ancestors(link)], 'The link must stay hidden without JavaScript'
    assert not any(a.tag == 'noscript' for a in ancestors(link))
    tools = next(n for n in doc.walk() if n.attrs.get('id') == 'directoryTools')
    assert 'hidden' in tools.attrs
    note = next(n for n in doc.walk() if n.attrs.get('id') == link.attrs.get('aria-describedby'))
    assert 'Shared links contain the search text you entered.' in note.text
    assert tools in list(ancestors(note))
    query = next(n for n in doc.walk() if n.attrs.get('id') == 'directoryQuery')
    assert query.attrs.get('maxlength') == '200', 'Typed queries must fit the restored-parameter limit'
    assert any(n.tag == 'noscript' and 'All names remain visible without JavaScript' in n.text for n in doc.walk())


def test_link_writing_restoration_precedence_and_unsafe_parameters():
    node = os.environ.get('ZOTHEOS_TEST_NODE') or shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    result = subprocess.run([node, str(Path(__file__).with_name('directory-share-acceptance.cjs')),
                             str(ROOT / 'tools/nations/partials/appearance.js')],
                            capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr
