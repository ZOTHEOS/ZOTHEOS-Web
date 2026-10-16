"""Independent actual-builder acceptance for an optional short poster label."""
from pathlib import Path
import pytest

from theater_acceptance_v1_helpers import DOM, fixture_build, fictional_catalog


def test_short_cover_is_escaped_and_never_replaces_full_identifying_title(tmp_path, fictional_catalog):
    film = fictional_catalog['films'][0]
    film['title'] = 'The Full Identifying Recorded Presentation Title'
    film['cover_title'] = 'Short <img src=x onerror=bad()> & Clear'
    result = fixture_build(tmp_path, fictional_catalog)
    assert result.returncode == 0, result.stdout + result.stderr
    html = (tmp_path/'theater.html').read_text(encoding='utf-8')
    dom = DOM(html)
    covers = [el for el in dom.elements if 'th-cover-title' in el.attrs.get('class', '').split()]
    assert len(covers) == 1 and covers[0].text == film['cover_title']
    assert '&lt;img' in html
    assert not any(el.tag == 'img' and el.attrs.get('src') == 'x' for el in dom.elements)
    card = next(el for el in dom.elements if el.attrs.get('data-theater-film') == film['id'])
    assert card.attrs['data-title'] == film['title']
    assert any(el.tag == 'h3' and el.text == film['title'] for el in card.descendants())
    assert any(el.attrs.get('id') == 'theaterTitle' and el.text == film['title'] for el in dom.elements)


@pytest.mark.parametrize('bad', ['', '   ', 'x' * 101, None, 17])
def test_optional_cover_label_when_present_is_bounded_nonempty_text(tmp_path, fictional_catalog, bad):
    fictional_catalog['films'][0]['cover_title'] = bad
    result = fixture_build(tmp_path, fictional_catalog)
    assert result.returncode != 0 and not (tmp_path/'theater.html').exists()


def test_absent_cover_label_retains_full_title(tmp_path, fictional_catalog):
    result = fixture_build(tmp_path, fictional_catalog)
    assert result.returncode == 0, result.stdout + result.stderr
    dom = DOM((tmp_path/'theater.html').read_text(encoding='utf-8'))
    covers = [el for el in dom.elements if 'th-cover-title' in el.attrs.get('class', '').split()]
    assert len(covers) == 1 and covers[0].text == fictional_catalog['films'][0]['title']
