"""Actual generated Theater markup in a neutral DOM, with no provider execution.

The existing independently reviewed Appearance event fixture is frozen inside
the companion helper. Only the shared/scoped first-party Appearance scripts run.
This does not certify browser layout, downloaded files or provider playback.
"""
import json
import os
from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest

ROOT = Path(os.environ.get("ZOTHEOS_TEST_REPO", str(Path(__file__).resolve().parents[2])))
VOID = set("area base br col embed hr img input link meta param source track wbr".split())
CASES = (
    "actual generated layout has nested masthead and separate stage/action columns",
    "introduction includes actual heading, lede and library scope",
    "selected story retains exact visible maker, perspective and Before Watching text",
    "selected story keeps Publisher, Year and Runtime legible with term/value separators",
    "selected story retains source titles, check dates and thumbnail credit",
    "selected story excludes all stage, status, Up Next, privacy and story-action text",
    "existing private-input, hidden, controls, editable, script and provider boundaries survive",
    "explicit link activation refreshes current public story without restoring excluded UI",
    "all actual output translation parts are bounded, explicit, public and inert",
)


class _Tree(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = {"tag": "root", "attrs": {}, "children": []}
        self.stack = [self.root]
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        node = {"tag": tag, "attrs": dict(attrs), "children": []}
        self.stack[-1]["children"].append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index]["tag"] == tag:
                del self.stack[index:]
                break

    def handle_data(self, value):
        self.stack[-1]["children"].append(value)


def _walk(node):
    if isinstance(node, dict):
        yield node
        for child in node["children"]:
            yield from _walk(child)


def _text(node):
    return node if isinstance(node, str) else "".join(_text(child) for child in node["children"])


@pytest.fixture(scope="module")
def actual_translation_results():
    node = shutil.which("node")
    assert node, "Node.js is required for the website interaction contract."
    html = (ROOT / "theater.html").read_text(encoding="utf-8")
    nodes = list(_walk(_Tree(html).root))
    by_id = {item["attrs"]["id"]: item for item in nodes if "id" in item["attrs"]}
    intro = next(item for item in nodes if "th-cinema-heading" in item["attrs"].get("class", "").split())
    fragments = [intro] + [by_id[key] for key in ("screening", "curation", "site-translation")]
    public_ids = ("theaterTitle", "theaterDescription", "theaterCredits", "theaterPerspective", "theaterContentNote", "theaterPublisher", "theaterYear", "theaterRuntime", "theaterSources", "theaterThumbCredit")
    intro_blocks = [" ".join(_text(item).split()) for item in _walk(intro) if item["tag"] in ("h1", "p")]
    source_titles = [" ".join(_text(item).split()) for item in _walk(by_id["theaterSources"]) if item["tag"] == "a"]
    source_dates = [item["attrs"]["datetime"] for item in _walk(by_id["theaterSources"]) if item["tag"] == "time"]
    payload = {"fragments": fragments, "expected": {key: " ".join(_text(by_id[key]).split()) for key in public_ids}, "introBlocks": intro_blocks, "sourceTitles": source_titles, "sourceDates": source_dates}
    helper = Path(__file__).with_name("theater-translation-layout-runtime.cjs")
    scoped = ROOT / "static/theater/appearance.js"
    with tempfile.TemporaryDirectory(prefix="zotheos-translation-layout-") as task_dir:
        snapshot = Path(task_dir) / "actual-output-dom.json"
        snapshot.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        run = subprocess.run([node, str(helper), str(ROOT), str(scoped), str(snapshot)], capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert run.returncode in (0, 1), run.stdout + run.stderr
    result = json.loads(run.stdout)
    assert len(result["cases"]) == len(CASES)
    assert {case["name"] for case in result["cases"]} == set(CASES)
    return {case["name"]: case for case in result["cases"]}


@pytest.mark.parametrize("case_name", CASES)
def test_actual_theater_translation_layout(case_name, actual_translation_results):
    case = actual_translation_results[case_name]
    assert case["pass"], case.get("error", case_name)
