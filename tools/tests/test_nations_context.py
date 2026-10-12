"""Portable stdlib tests: python tools/tests/test_nations_context.py [tools-dir] [model-root]."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.dont_write_bytecode = True
TOOLS = (Path(__file__).resolve().parents[1] if __name__ != "__main__" else Path(sys.argv[1] if len(sys.argv) > 1 else "tools").resolve())
MODEL_ROOT = Path(sys.argv[2]).resolve() if __name__ == "__main__" and len(sys.argv) > 2 else TOOLS.parent
sys.path.insert(0, str(TOOLS))
from nations_context import Context, MAX_BYTES  # noqa: E402
import nations_lib as L  # noqa: E402

spec = importlib.util.spec_from_file_location("context_builder_test", TOOLS / "nations_build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def model():
    alpha = {"id": "test-alpha", "name": 'Alpha <&"', "facts": [{"id": "alpha-ok"}]}
    beta = {"id": "test-beta", "name": "Beta", "facts": []}
    return SimpleNamespace(build_date="2026-10-12", nations=[alpha, beta],
                           by_id={alpha["id"]: alpha, beta["id"]: beta},
                           raw={"nations": [{"id": "test-alpha", "facts": [{"id": "alpha-ok"}, {"id": "alpha-held"}]},
                                            {"id": "test-beta", "facts": []}, {"id": "test-gone", "facts": []}]})


def payload():
    return {"reviewed": "2026-10-12", "public_notes": [{"nation": "test-alpha", "text": "A dated scope note."}],
            "official_resources": [{"nation": "test-alpha", "label": "Official guide", "url": "https://alpha.example/guide", "purpose": "Read the publisher's explanation."}],
            "relationships": [{"from": "test-alpha", "to": ["test-beta", "test-gone"], "relationship": "Separate records, not aliases"}],
            "integration_cautions": ["PRIVATE INTERNAL NOTE"]}


def allow():
    return {"version": 1, "links": [{"nation": "test-alpha", "url": "https://alpha.example/guide", "publisher": "Alpha", "reviewed": "2026-10-12"}]}


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="zotheos-context-tests-")
        self.root = Path(self.tmp.name)
        self.folder = self.root / "data" / "nations"
        self.sources = self.folder / "sources"
        self.sources.mkdir(parents=True)
        self.m = model()

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, doc=None, catalog=None, name="test.context.json"):
        (self.sources / name).write_text(json.dumps(doc if doc is not None else payload()), encoding="utf-8")
        (self.folder / "context_links.json").write_text(json.dumps(catalog if catalog is not None else allow()), encoding="utf-8")

    def test_public_links_and_context_have_honest_review_dates(self):
        self.write(); page = Context(self.root, self.m).page("test-alpha")
        self.assertIn('datetime="2026-10-12"', page)
        self.assertIn("with AI assistance", page)
        self.assertIn("separate from the fact checks", page)
        self.assertNotIn("human verified", page.lower())
        self.assertNotIn("PRIVATE INTERNAL NOTE", page)

    def test_escaped_text_and_names_never_become_markup(self):
        doc = payload(); doc["public_notes"][0]["text"] = '<script>bad()</script> & "text"'
        doc["official_resources"][0]["label"] = '<img src=x onerror=bad()>'
        self.write(doc); page = Context(self.root, self.m).page("test-beta") + Context(self.root, self.m).page("test-alpha")
        self.assertNotIn("<script>", page); self.assertNotIn("<img ", page)
        self.assertIn("&lt;script&gt;", page); self.assertIn("Alpha &lt;&amp;&quot;", page)

    def test_exact_allowlist_rejects_same_host_different_path(self):
        doc = payload(); doc["official_resources"][0]["url"] += "?unreviewed=1"
        self.write(doc)
        with self.assertRaisesRegex(ValueError, "exact nation/link allowlist"):
            Context(self.root, self.m)

    def test_allowlist_is_bound_to_the_nation(self):
        doc = payload(); doc["official_resources"][0]["nation"] = "test-beta"
        self.write(doc)
        with self.assertRaisesRegex(ValueError, "exact nation/link allowlist"):
            Context(self.root, self.m)

    def test_future_and_invalid_review_dates_fail(self):
        for value in ["2026-10-13", "2026-02-30", "today"]:
            doc = payload(); doc["reviewed"] = value; self.write(doc)
            with self.assertRaises(ValueError): Context(self.root, self.m)

    def test_hidden_nations_are_neither_linked_nor_resurrected(self):
        doc = payload(); doc["public_notes"].append({"nation": "test-gone", "text": "REMOVED NATION"})
        self.write(doc); c = Context(self.root, self.m)
        self.assertEqual(c.page("test-gone"), "")
        self.assertNotIn("test-gone", c.page("test-alpha"))
        self.assertNotIn("REMOVED NATION", c.page("test-alpha"))

    def test_held_facts_suppress_associated_context_and_resources(self):
        doc = payload(); doc["public_notes"][0]["fact_ids"] = ["alpha-held"]
        doc["official_resources"][0]["fact_ids"] = ["alpha-held"]
        self.write(doc); page = Context(self.root, self.m).page("test-alpha")
        self.assertNotIn("A dated scope note", page); self.assertNotIn("alpha.example/guide", page)

    def test_unknown_fact_or_nation_reference_fails(self):
        doc = payload(); doc["public_notes"][0]["fact_ids"] = ["typo"]
        self.write(doc)
        with self.assertRaisesRegex(ValueError, "unknown fact reference"): Context(self.root, self.m)
        doc = payload(); doc["public_notes"][0]["nation"] = "unknown"
        self.write(doc)
        with self.assertRaisesRegex(ValueError, "nation id"): Context(self.root, self.m)

    def test_no_context_and_unrelated_nation_add_no_section(self):
        self.assertEqual(Context(self.root, self.m).page("test-alpha"), "")
        doc = payload(); doc["relationships"] = []; self.write(doc)
        self.assertEqual(Context(self.root, self.m).page("test-beta"), "")

    def test_new_context_files_load_in_a_stable_order(self):
        first = payload(); first["public_notes"][0]["text"] = "FIRST"
        second = {"reviewed": "2026-10-12", "public_notes": [{"nation": "test-alpha", "text": "SECOND"}]}
        self.write(second, name="z.context.json"); self.write(first, name="a.context.json")
        page = Context(self.root, self.m).page("test-alpha")
        self.assertLess(page.index("FIRST"), page.index("SECOND"))

    def test_files_and_per_nation_items_are_bounded(self):
        self.write(); (self.sources / "test.context.json").write_text(" " * (MAX_BYTES + 1), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "128 KiB"): Context(self.root, self.m)
        doc = payload(); doc["public_notes"] = [{"nation": "test-alpha", "text": str(i)} for i in range(17)]
        self.write(doc)
        with self.assertRaisesRegex(ValueError, "16 items"): Context(self.root, self.m)

    def test_nation_template_integration_preserves_fact_count_and_correction_link(self):
        self.write(); b = build.Builder.__new__(build.Builder); b.root = str(self.root); b.m = self.m
        n = self.m.by_id["test-alpha"]
        n.update(region="test-region", also=[], pronounce=None, official_url=None, countries=["US"],
                 sz="md", fc="brand", sc="latn", lf="brand", lands="Test lands", rechecking=0, review=0)
        n["facts"][0].update(kind="history", text="Published fact", fc="brand")
        self.m.region_by_key = {"test-region": {"key": "test-region", "display": "Test region"}}
        self.m.countries = {"US": "United States"}; b.contact = "corrections@example.test"
        b.face_attr = lambda v: ""; b.receipt = lambda *args: "Fact phrase-match receipt"
        b.tpl = lambda name: (TOOLS / "nations" / "templates" / (name + ".html")).read_text(encoding="utf-8")
        b.page = lambda *args: args[-1]
        result = b.nation_page(n)
        self.assertIn("Published fact", result); self.assertIn('class="fcount">1</span>', result)
        self.assertIn("Suggest a correction", result); self.assertIn("Context and resources", result)
        self.assertNotIn("{{{context}}}", result)

    @unittest.skipUnless(MODEL_ROOT, "Provide model-root for the real registry test")
    def test_real_registry_links_and_existing_holds(self):
        m = L.Model(str(MODEL_ROOT))
        self.assertEqual(m.errors, [])
        c = Context(TOOLS.parent, m)
        expected = ["fort-sill-apache-us-ok-nm", "southern-ute-indian-tribe-us-co", "ute-mountain-ute-tribe-us-co-ut-nm",
                    "ute-indian-tribe-uintah-ouray-us-ut", "lipan-apache-tribe-us-tx", "chiricahua-apache-nation-us-nm"]
        for nid in expected:
            page = c.page(nid); self.assertIn("noopener noreferrer", page); self.assertIn("AI assistance", page)
        held = {v["fact"] for v in m.overrides.get("hide_fact", [])}
        shown = {f["id"] for n in m.nations for f in n["facts"]}
        self.assertFalse(held & shown)
        for nid in m.blocked_ids:
            self.assertEqual(c.page(nid), "")
        ute = c.page("ute-indian-tribe-uintah-ouray-us-ut")
        self.assertIn("intention to appeal", ute); self.assertIn("does not establish an appeal filing or outcome", ute)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
