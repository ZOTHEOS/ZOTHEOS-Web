"""Theater v2: actual thumbnails and ready players, never autoplay.

Explicit user revision supersedes v1's separate consent and no-remote-image
requirements. The older contract and its results remain immutable evidence.
Fictional inputs exercise the actual builder; no external requests are made.
"""
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import urlsplit

import pytest

import theater_acceptance_v1_helpers as v1
from theater_acceptance_v1_helpers import DOM, fixture_build, fictional_catalog

ROOT = v1.ROOT
ART = Path(__file__).resolve().parent
THUMBNAIL_HOSTS = {'i.ytimg.com', 'i.vimeocdn.com', 'image.pbs.org', 'assets.nfbcdn.ca'}
FRAMES = {'https://www.youtube-nocookie.com', 'https://player.pbs.org', 'https://player.vimeo.com', 'https://www.nfb.ca'}

# Requirements that the explicit visual/player revision did not supersede.
test_semantics_and_site_navigation = v1.test_theater_is_a_real_semantic_page_with_local_navigation_and_footer
test_source_credits_dates_and_scope = v1.test_curated_catalog_is_not_fixture_data_and_has_sources_credits_dates_and_viewing_scope
test_static_cards_and_official_watch_links = v1.test_every_film_is_statically_present_with_truthful_scope_and_official_watch_fallback
test_filter_labels_and_recovery = v1.test_filter_controls_and_empty_recovery_have_labels_and_one_announcement
test_non_theater_frame_permissions_preserved = v1.test_existing_non_theater_frame_policies_are_not_widened
test_strict_script_policy_is_synchronized = v1.test_theater_is_in_csp_sync_and_its_meta_matches_response_policy
test_unsafe_watch_links_rejected = v1.test_builder_rejects_unsafe_watch_urls_before_publishing
test_invalid_provider_ids_rejected = v1.test_builder_rejects_invalid_provider_identifiers
test_dual_provider_rejected = v1.test_builder_rejects_two_providers_for_one_selection
test_future_source_check_rejected = v1.test_builder_rejects_fabricated_future_source_check


def test_exact_reviewed_image_and_frame_hosts_apply_only_to_theater():
    policies = v1.header_policies()
    for route in ['/theater', '/theater.html']:
        policy = v1.directives(policies[route])
        assert set(policy.get('frame-src', [])) == FRAMES
        assert {'https://' + host for host in THUMBNAIL_HOSTS} <= set(policy.get('img-src', []))
        assert set(policy.get('img-src', [])) <= {"'self'", 'data:', *['https://' + host for host in THUMBNAIL_HOSTS]}
        assert policy.get('script-src-attr') == ["'none'"]
        assert not set(policy.get('script-src', [])) & {"'unsafe-inline'", "'unsafe-eval'", '*', 'https:'}
    for route, value in policies.items():
        if route not in ['/theater', '/theater.html']:
            assert not (set(v1.directives(value).get('frame-src', [])) & FRAMES)


def test_real_curated_thumbnail_urls_render_as_images_with_useful_alternative_text():
    data = v1.catalog()
    html, dom = v1.page()
    thumbnails = [film for film in data['films'] if film.get('thumbnail_url')]
    assert thumbnails, 'V2 requires actual reviewed thumbnails, not only decorative title art'
    for film in thumbnails:
        url = urlsplit(film['thumbnail_url'])
        assert url.scheme == 'https' and url.hostname in THUMBNAIL_HOSTS
        assert not url.username and not url.password and url.port in (None, 443)
        card = next(el for el in dom.elements if el.attrs.get('data-theater-film') == film['id'])
        images = [el for el in card.descendants() if el.tag == 'img' and el.attrs.get('src') == film['thumbnail_url']]
        assert images, film['id']
        assert images[0].attrs.get('alt', '').strip(), 'A meaningful actual thumbnail is not unexplained ornament'
        assert images[0].attrs.get('referrerpolicy') == 'no-referrer'


def test_default_output_permits_only_reviewed_images_and_players_with_no_autoplay_or_outside_scripts():
    html, dom = v1.page()
    for el in dom.elements:
        assert 'autoplay' not in el.attrs
        if el.tag == 'iframe':
            url = urlsplit(el.attrs.get('src', ''))
            assert url.scheme + '://' + url.netloc in FRAMES
            assert 'autoplay=0' in url.query
            assert el.attrs.get('title', '').strip()
            assert not re.search(r'(^|;)\s*autoplay\b', el.attrs.get('allow', ''))
        if el.tag in {'script', 'source', 'audio', 'video'}:
            assert not el.attrs.get('src', '').startswith(('https:', 'http:', '//'))
        if el.tag == 'img' and el.attrs.get('src', '').startswith(('https:', 'http:', '//')):
            url = urlsplit(el.attrs['src'])
            assert url.scheme == 'https' and url.hostname in THUMBNAIL_HOSTS
        if el.tag == 'link' and set(el.attrs.get('rel', '').split()) & {'stylesheet', 'preload'}:
            assert not el.attrs.get('href', '').startswith(('https:', 'http:', '//'))
    assert not re.search(r'url\(\s*["\']?(?:https?:)?//', html, re.I), 'CSS must not hide outside asset requests'


def test_motion_control_is_explicit_and_css_honors_still_and_os_reduced_motion():
    html, dom = v1.page()
    button, = dom.by_id('theaterMotion')
    assert button.tag == 'button' and button.attrs.get('type') == 'button'
    assert button.attrs.get('aria-pressed') in {'true', 'false'}
    assert 'still' in button.text.casefold() or 'motion' in button.text.casefold()
    css = (ROOT/'static/theater/theater.css').read_text(encoding='utf-8')
    assert 'prefers-reduced-motion' in css
    assert 'data-theater-motion' in css and 'still' in css
    assert re.search(r'animation(?:-name)?\s*:\s*none', css), 'Still/reduced state must actually remove animation'
    assert re.search(r'min-(?:height|block-size)\s*:\s*(?:44|4[5-9]|[5-9]\d)px', css), 'Theater controls declare at least a 44px touch target; actual layout remains a browser gate'


def test_privacy_copy_discloses_automatic_images_and_ready_players_in_plain_language():
    html, dom = v1.page()
    text = dom.root.text.casefold()
    assert 'thumbnail' in text
    assert ('automatically' in text or 'on opening' in text or 'on entry' in text or 'on page load' in text)
    assert 'ip address' in text or 'request information' in text or 'device information' in text
    for obsolete in ['no video loads until you choose', 'choosing this title does not contact a video provider',
                     'every request goes to zotheos.org', 'this site makes no request to any other site']:
        assert obsolete not in text
    for rel in ['index.html', 'nations/about.html']:
        copy = DOM((ROOT/rel).read_text(encoding='utf-8')).root.text.casefold()
        assert 'thumbnail' in copy and ('theater' in copy)
        assert 'this site makes no request to any other site' not in copy


def test_fictional_actual_provider_thumbnail_is_preserved_as_data_not_markup(tmp_path, fictional_catalog):
    film = fictional_catalog['films'][0]
    film['thumbnail_url'] = 'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg'
    result = fixture_build(tmp_path, fictional_catalog)
    assert result.returncode == 0, result.stdout + result.stderr
    dom = DOM((tmp_path/'theater.html').read_text(encoding='utf-8'))
    image = next((el for el in dom.elements if el.tag == 'img' and el.attrs.get('src') == film['thumbnail_url']), None)
    assert image is not None
    assert image.attrs.get('alt', '').strip()
    assert not any(el.tag == 'img' and el.attrs.get('src') == 'x' for el in dom.elements)


@pytest.mark.parametrize('bad', [
    'javascript:alert(1)',
    'http://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg',
    '//i.ytimg.com/vi/abcdefghijk/hqdefault.jpg',
    'https://i.ytimg.com.evil.example/vi/abcdefghijk/hqdefault.jpg',
    'https://user:password@i.ytimg.com/vi/abcdefghijk/hqdefault.jpg',
    'https://i.ytimg.com:444/vi/abcdefghijk/hqdefault.jpg',
    'https://unreviewed.example.test/poster.jpg',
    'https://i.ytimg.com/vi/bad-id/hqdefault.jpg',
    'https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg" onerror="bad()',
])
def test_thumbnail_validation_fails_closed_before_output(tmp_path, fictional_catalog, bad):
    fictional_catalog['films'][0]['thumbnail_url'] = bad
    result = fixture_build(tmp_path, fictional_catalog)
    assert result.returncode != 0 and not (tmp_path/'theater.html').exists()


def test_actual_script_satisfies_v2_ready_player_and_motion_behavior():
    node = Path(r'C:\nvm4w\nodejs\node.exe')
    assert node.is_file(), 'Pinned Node runtime is required for this acceptance gate'
    result = subprocess.run([str(node), str(ART/'theater-interaction-acceptance-v2.cjs'),
                             str(ROOT/'static/theater/theater.js')], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('field,value', [
    ('vimeo_id', '141218300?autoplay=1'), ('vimeo_id', 'abc123'),
    ('vimeo_id', '12345'), ('vimeo_id', '1' * 13),
    ('nfb_slug', '../birth_of_a_family'), ('nfb_slug', 'birth_of_a_family?autoplay=1'),
    ('nfb_slug', 'javascript:alert(1)'), ('pbs_route', 'unapproved/path'),
])
def test_additional_provider_identifier_and_route_validation_fails_closed(tmp_path, fictional_catalog, field, value):
    film = fictional_catalog['films'][0]
    film['youtube_id'] = None
    if field == 'pbs_route':
        film['pbs_id'] = '3109669877'
    film[field] = value
    result = fixture_build(tmp_path, fictional_catalog)
    assert result.returncode != 0 and not (tmp_path/'theater.html').exists()


@pytest.mark.parametrize('extra', [{'vimeo_id':'141218300'}, {'nfb_slug':'birth_of_a_family'}])
def test_new_provider_cannot_stack_with_existing_youtube_provider(tmp_path, fictional_catalog, extra):
    fictional_catalog['films'][0].update(extra)
    result = fixture_build(tmp_path, fictional_catalog)
    assert result.returncode != 0 and not (tmp_path/'theater.html').exists()


@pytest.mark.parametrize('fields,provider,ident,route', [
    ({'vimeo_id':'123456789'}, 'vimeo', '123456789', None),
    ({'nfb_slug':'fictional_river'}, 'nfb', 'fictional_river', None),
    ({'pbs_id':'1234567890','pbs_route':'viralplayer'}, 'pbs', '1234567890', 'viralplayer'),
    ({'pbs_id':'1234567890'}, 'pbs', '1234567890', 'stationplayer'),
])
def test_real_builder_accepts_and_escapes_valid_reviewed_provider_fields(tmp_path, fictional_catalog, fields, provider, ident, route):
    film = fictional_catalog['films'][0]
    film['youtube_id'] = None
    film.update(fields)
    result = fixture_build(tmp_path, fictional_catalog)
    assert result.returncode == 0, result.stdout + result.stderr
    dom = DOM((tmp_path/'theater.html').read_text(encoding='utf-8'))
    card = next(el for el in dom.elements if el.attrs.get('data-theater-film') == film['id'])
    assert card.attrs.get('data-provider') == provider
    assert card.attrs.get('data-video-id') == ident
    if route:
        assert card.attrs.get('data-pbs-route') == route
    assert any(el.tag == 'a' and el.attrs.get('href') == film['watch_url'] for el in card.descendants())
