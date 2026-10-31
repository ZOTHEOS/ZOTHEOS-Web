"""Theater filter clarity and recovery (UI-THEATER-FILTERS-002). Fictional records only; no browser certification."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

R = Path(os.environ.get('ZOTHEOS_TEST_REPO', str(Path(__file__).resolve().parents[2])))
sys.path.insert(0, str(R / 'tools/tests'))
from theater_acceptance_v1_helpers import DOM, fictional_catalog, fixture_build  # noqa: E402,F401


def rendered(tmp_path, catalog):
    run = fixture_build(tmp_path, catalog)
    assert run.returncode == 0, run.stdout + run.stderr
    return DOM((tmp_path / 'theater.html').read_text(encoding='utf-8'))


def inside(el, key):
    node = el.parent
    while node is not None:
        if node.attrs.get('id') == key:
            return True
        node = node.parent
    return False


def test_selected_filter_row_sits_outside_the_folded_phone_panel_and_needs_script(tmp_path, fictional_catalog):
    d = rendered(tmp_path, fictional_catalog)
    row, = d.by_id('theaterActive')
    lst, = d.by_id('theaterActiveList')
    assert 'hidden' in row.attrs, 'No choice is selected at first paint'
    assert inside(row, 'theaterTools') and not inside(row, 'theaterFilterPanel')
    assert lst.tag == 'ul' and lst.attrs.get('aria-labelledby') == 'theaterActiveLabel'
    label, = d.by_id('theaterActiveLabel')
    assert label.text.strip() == 'Selected Filters'
    tools, = d.by_id('theaterTools')
    assert 'data-needs-js' in tools.attrs, 'Without JavaScript the row and its controls stay out of the reading page'


def test_empty_state_offers_native_contextual_recovery_and_an_explicit_full_reset(tmp_path, fictional_catalog):
    d = rendered(tmp_path, fictional_catalog)
    empty, = d.by_id('theaterEmpty')
    assert 'hidden' in empty.attrs
    labels = {}
    for key in ('theaterClearSearch', 'theaterClearFacets', 'theaterReset'):
        b, = d.by_id(key)
        assert b.tag == 'button' and b.attrs.get('type') == 'button' and 'hidden' in b.attrs and inside(b, 'theaterEmpty')
        labels[key] = b.text.strip()
    assert labels == {'theaterClearSearch': 'Clear Search', 'theaterClearFacets': 'Clear Selected Filters',
                      'theaterReset': 'Reset Search And Filters'}
    toolbar, = d.by_id('theaterClear')
    assert 'search' in toolbar.text.casefold() and 'filters' in toolbar.text.casefold(), \
        'The toolbar control clears the search too, so its accessible name says so'


def test_catalogue_keeps_its_single_status_announcement(tmp_path, fictional_catalog):
    d = rendered(tmp_path, fictional_catalog)
    live = [el.attrs.get('id') for el in d.elements if el.attrs.get('role') in ('status', 'alert') or el.attrs.get('aria-live')]
    assert sorted(live) == ['theaterAnnounce', 'theaterStatus'], 'No duplicate live region is added for filtering'


def test_static_catalogue_is_unchanged_without_javascript(tmp_path, fictional_catalog):
    d = rendered(tmp_path, fictional_catalog)
    cards = [el for el in d.elements if 'data-theater-film' in el.attrs]
    assert len(cards) == len(fictional_catalog['films']) and not any('hidden' in c.attrs for c in cards)


def test_actual_script_filter_removal_recovery_focus_and_player_identity():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    script = Path(__file__).with_name('theater-filter-recovery-acceptance.cjs')
    run = subprocess.run([node, str(script), str(R / 'static/theater/theater.js')], capture_output=True, text=True, encoding='utf-8')
    assert run.returncode == 0, run.stdout + run.stderr
