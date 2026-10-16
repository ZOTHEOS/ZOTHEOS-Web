"""Publication boundaries and provenance for the game's two exported data files."""
import json
import shutil
from pathlib import Path

import pytest

import game_nations as G
import nations_lib as L
from conftest import ROOT
from test_game_shards import unpack


def exported(model=None):
    outputs, nations, skipped = G.build(ROOT, model=model)
    quick = unpack(outputs, "nations")
    history = unpack(outputs, "history")
    return outputs, {n["id"]: n for n in quick}, history, skipped


def test_existing_history_survives_quick_card_priorities_and_size_limits():
    model = L.Model(ROOT)
    outputs, quick, history, skipped = exported(model)
    assert not skipped
    assert set(quick) == {n["id"] for n in model.nations if n["facts"]}
    # These two entries were silently excluded by the old 200-character lands cap.
    for nid in ("evenki-siberia", "metis-nation-ca"):
        assert quick[nid]["name"] == model.by_id[nid]["name"]
        assert quick[nid]["lands"] == model.by_id[nid]["lands"]
    expected = {f["id"] for n in model.nations for f in n["facts"] if f["kind"] == "history"}
    actual = {f["id"] for n in history.values() for f in n["history"]}
    assert actual == expected and actual
    assert all(1 <= len(n["facts"]) <= 2 for n in quick.values())
    # Benet's history must remain available even though its two quick facts are other kinds.
    assert all(f["kind"] != "history" for f in quick["benet-uganda"]["facts"])
    assert history["benet-uganda"]["history"]
    raw = {f["id"]: f for n in model.raw["nations"] for f in n["facts"]}
    for n in history.values():
        for f in n["history"] + n["context"]:
            assert f["text"] == raw[f["id"]]["text"]
            assert f["source"] == raw[f["id"]]["source"]
    assert len(outputs["game/nations.json"].encode("utf-8")) < G.LIMIT
    assert len(outputs["game/history.json"].encode("utf-8")) < G.HISTORY_LIMIT
    assert "Bhuri Bai" not in "".join(outputs.values())


def test_canonical_corrections_removals_and_holds_reach_both_exports():
    model = L.Model(ROOT)
    nation = model.raw["nations"][0]
    nid = nation["id"]
    nation["also"] = ["Old spelling", "Retained spelling"]
    nation["pronounce"] = {"text": "Held pronunciation", "source_url": "https://example.org/name"}
    held = next(f for f in nation["facts"] if f["kind"] == "history")
    model.overrides["hide_fact"].append({"fact": held["id"]})
    model.overrides["rename"].append({"nation": nid, "name": "Corrected nation name"})
    model.overrides["drop_also"].append({"nation": nid, "also": "Old spelling"})
    model.overrides["drop_pronounce"].append({"nation": nid})
    model.overrides["hide_nation"].append({"nation": "benet-uganda"})
    model.overrides["takedown"].append({"nation": "griqua-south-africa"})
    model._apply()
    outputs, quick, history, _ = exported(model)
    assert quick[nid]["name"] == "Corrected nation name"
    assert quick[nid]["also"] == ["Retained spelling"]
    assert "pronounce" not in quick[nid]
    assert held["text"] not in "".join(outputs.values())
    assert nid not in history
    for removed in ("benet-uganda", "griqua-south-africa"):
        assert removed not in quick and removed not in history


def test_receipts_keep_access_verified_human_and_failed_attempt_dates_distinct():
    model = L.Model(ROOT, build_date="2026-10-20")
    facts = model.raw["nations"][0]["facts"]
    population = next(f for f in facts if f["kind"] == "population")
    history_fact = next(f for f in facts if f["kind"] == "history")
    governance = next(f for f in facts if f["kind"] == "governance")
    population.update(checked="2026-10-20", last_verified="2026-10-18")
    history_fact.update(status="unreachable", checked="2026-10-20", last_verified="2026-10-08")
    governance.update(status="unreachable", checked="2026-10-20", last_verified="2026-09-01")
    model.human[governance["id"]] = {"date": "2026-10-19", "by": "editor", "note": "read in browser"}
    model._apply()
    _, quick, histories, _ = exported(model)
    hf = histories["afar-horn-of-africa"]["history"][0]
    assert (hf["checked"], hf["state"], hf["note"]) == ("2026-10-08", "grace", "2026-10-20")
    by_kind = {f["kind"]: f for f in quick["afar-horn-of-africa"]["facts"]}
    assert (by_kind["population"]["checked"], by_kind["population"]["state"]) == ("2026-10-18", "ok")
    assert (by_kind["governance"]["checked"], by_kind["governance"]["state"]) == ("2026-10-19", "human")
    for f in [hf] + list(by_kind.values()):
        assert f["source"]["accessed"] == "2026-10-09"


@pytest.mark.parametrize("status", ["stale", "unreachable"])
def test_unpublishable_history_is_not_resurrected(status):
    model = L.Model(ROOT, build_date="2026-10-25")
    fact = next(f for f in model.raw["nations"][0]["facts"] if f["kind"] == "history")
    fact.update(status=status, checked="2026-10-25", last_verified="2026-10-08")
    model._apply()
    outputs, _, history, _ = exported(model)
    assert "afar-horn-of-africa" not in history
    assert fact["text"] not in "".join(outputs.values())


def test_payload_budget_counts_unicode_bytes():
    # This fits a 100-character limit, but exceeds a 100-byte network budget.
    with pytest.raises(ValueError, match="UTF-8 bytes"):
        G.encode({"text": "\u00e9" * 60}, 100, "fixture")


def test_check_detects_missing_or_changed_history_without_writing(tmp_path):
    shutil.copytree(Path(ROOT) / "data" / "nations", tmp_path / "data" / "nations",
                    ignore=shutil.ignore_patterns("sources", "tools", "*.md", "nations.min.json"))
    assert G.main(["--root", str(tmp_path)]) == 0
    assert G.main(["--root", str(tmp_path), "--check"]) == 0
    quick_path = tmp_path / "game" / "nations.json"
    quick_before = quick_path.read_bytes()
    history_path = tmp_path / "game" / "history.json"
    with history_path.open("a", encoding="utf-8") as f:
        f.write("\n")
    changed = history_path.read_bytes()
    assert G.main(["--root", str(tmp_path), "--check"]) == 1
    assert history_path.read_bytes() == changed
    history_path.unlink()
    assert G.main(["--root", str(tmp_path), "--check"]) == 1
    assert not history_path.exists() and quick_path.read_bytes() == quick_before
