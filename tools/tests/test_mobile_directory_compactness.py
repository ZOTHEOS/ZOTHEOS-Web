"""User acceptance: search first, labelled controls, optional native method explanation.

These parse the built public HTML. They do not prescribe viewport pixels, generated
class ordering or a visual implementation. Build before running this module.
"""
from html.parser import HTMLParser
import os
from pathlib import Path


ROOT = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}


class Node:
    def __init__(self, tag, attrs=(), parent=None, order=0):
        self.tag, self.attrs, self.parent, self.order = tag, dict(attrs), parent, order
        self.children, self.parts = [], []

    def has_class(self, name):
        return name in self.attrs.get('class', '').split()

    def text(self):
        return ' '.join(''.join(self.parts).split())

    def ancestors(self):
        node = self.parent
        while node:
            yield node
            node = node.parent


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.root = Node('document')
        self.stack, self.nodes = [self.root], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1], len(self.nodes))
        self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data):
        for node in self.stack:
            node.parts.append(data)

    def one(self, predicate):
        found = [node for node in self.nodes if predicate(node)]
        assert len(found) == 1, 'Expected one matching public element, found ' + str(len(found))
        return found[0]

    def by_id(self, key):
        return self.one(lambda node: node.attrs.get('id') == key)


def page():
    return Document((ROOT / 'nations/directory.html').read_text(encoding='utf-8'))


def test_find_name_is_the_first_action_after_the_directory_introduction():
    doc = page()
    wrapper = doc.one(lambda node: node.has_class('directory-page'))
    lede = doc.one(lambda node: node.has_class('lede') and node.parent is wrapper)
    tools = doc.by_id('directoryTools')
    siblings = wrapper.children
    assert siblings[siblings.index(lede) + 1] is tools, (
        'Find A Name must immediately follow the brief introduction; explanatory cards must not push it down.'
    )
    paths = doc.one(lambda node: node.has_class('directory-paths'))
    pending = doc.one(lambda node: node.has_class('directory-key'))
    chooser = doc.one(lambda node: node.tag == 'h2' and node.text() == 'Choose a source inventory')
    assert tools.order < min(paths.order, pending.order, doc.by_id('us-inclusion').order, chooser.order)


def test_name_query_precedes_the_optional_inventory_filter_and_keeps_accessible_labels():
    doc = page()
    query, inventory = doc.by_id('directoryQuery'), doc.by_id('directoryInventory')
    assert query.order < inventory.order, 'People must encounter the name query before the optional source filter.'
    assert query.tag == 'input' and query.attrs.get('type') == 'search'
    assert inventory.tag == 'select'
    for control in (query, inventory):
        label = doc.one(lambda node: node.tag == 'label' and node.attrs.get('for') == control.attrs['id'])
        assert label.text(), 'Each search control needs a visible label independent of its placeholder.'
        assert control.attrs.get('aria-controls') == 'directoryNames'
    status = doc.by_id('directoryResult')
    assert status.attrs.get('role') == 'status' and status.attrs.get('aria-live') == 'polite'
    assert 'directoryResult' in query.attrs.get('aria-describedby', '').split()


def test_complete_scope_and_profile_explanation_is_optional_native_disclosure():
    doc = page()
    pending = doc.one(lambda node: node.has_class('directory-key'))
    paths = doc.one(lambda node: node.has_class('directory-paths'))
    details = [node for node in pending.ancestors() if node.tag == 'details']
    assert details, 'The full Pending explanation must remain available in native details instead of occupying the first screen.'
    disclosure = details[0]
    assert disclosure in list(paths.ancestors()), 'Keep the complete scope/profile distinction in the same disclosure.'
    assert 'open' not in disclosure.attrs and 'hidden' not in disclosure.attrs
    assert disclosure.children and disclosure.children[0].tag == 'summary'
    assert disclosure.children[0].text(), 'The disclosure needs its native, named keyboard toggle.'
    assert 'A profile may already exist under another name' in pending.text()
    assert 'identity review comes first' in pending.text()
    assert 'A directory entry is not a researched profile' in paths.text()
    assert 'cannot be added together as a count of Indigenous nations' in paths.text()
    assert 'profiles of peoples, communities and governing bodies' in paths.text()
    profile_links = [node.attrs.get('href') for node in doc.nodes if node.tag == 'a' and paths in list(node.ancestors())]
    assert '/nations#find' in profile_links and '/nations/resources' in profile_links
