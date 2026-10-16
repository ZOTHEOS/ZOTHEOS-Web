#!/usr/bin/env python3
"""Validate the cited catalogue and render the static Theater.

No source, image or video is fetched at build time. --check writes nothing.
--root isolates catalogue input/output; --source-root optionally selects shared templates.
"""
import argparse
from datetime import date, datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True
SOURCE = Path(__file__).resolve().parents[1]
KINDS = {'excerpt': 'Official Excerpt', 'trailer': 'Official Trailer', 'full-film': 'Full Film',
         'official-page': 'Official Page', 'short': 'Short Film'}
THUMBNAIL_HOSTS = {'i.ytimg.com', 'i.vimeocdn.com', 'image.pbs.org', 'assets.nfbcdn.ca'}
POLICY = ("default-src 'none'; base-uri 'none'; object-src 'none'; script-src 'none'; script-src-attr 'none'; "
          "style-src 'self' 'unsafe-inline'; font-src 'self'; "
          "img-src 'self' data: https://i.ytimg.com https://i.vimeocdn.com https://image.pbs.org https://assets.nfbcdn.ca; "
          "media-src 'none'; connect-src 'none'; form-action 'none'; "
          "frame-src https://www.youtube-nocookie.com https://player.pbs.org https://player.vimeo.com https://www.nfb.ca; "
          "worker-src 'none'; frame-ancestors 'none'")


def text(value, name, limit=1000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(name + ': a bounded, nonempty string is required')
    if any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise ValueError(name + ': control characters are forbidden')
    return value


def url(value):
    text(value, 'source URL', 2000)
    p = urlsplit(value)
    port = p.port
    if port == 0 or p.netloc.endswith(':'):
        raise ValueError('Invalid HTTPS port')
    if (p.scheme != 'https' or not p.hostname or p.username is not None or p.password is not None
            or '\\' in value or any(c.isspace() for c in value)):
        raise ValueError('Only absolute HTTPS publisher URLs without credentials are allowed')
    return value


def thumbnail_url(value):
    url(value)
    p = urlsplit(value)
    if p.hostname not in THUMBNAIL_HOSTS or p.port not in (None, 443) or p.fragment:
        raise ValueError('Thumbnail origin is not approved')
    if any(c in value for c in '<>"\'`') or re.search(r'%(?![0-9A-Fa-f]{2})', value):
        raise ValueError('Invalid thumbnail URL text')
    decoded = p.path
    for _ in range(len(decoded) + 1):
        next_path = unquote(decoded)
        if next_path == decoded:
            break
        decoded = next_path
    if ('\\' in decoded or any(ord(c) < 32 for c in decoded)
            or any(part in ('.', '..') for part in decoded.split('/'))):
        raise ValueError('Thumbnail traversal is forbidden')
    if p.hostname == 'i.ytimg.com' and not re.fullmatch(
            r'/(?:vi|vi_webp)/[A-Za-z0-9_-]{11}/(?:default|mqdefault|hqdefault|hq720|sddefault|maxresdefault|[0-3])\.(?:jpg|webp)', p.path):
        raise ValueError('Invalid YouTube thumbnail path or video ID')
    return value


def checked(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Source check requires an ISO calendar date')
    if date.fromisoformat(value) > datetime.now(timezone.utc).date():
        raise ValueError('A source check cannot be in the future')


def validate(data):
    if not isinstance(data, dict) or type(data.get('version')) is not int or data['version'] != 1:
        raise ValueError('Unsupported catalogue version')
    checked(data['updated'])
    films, topics = data['films'], data['topics']
    if not isinstance(films, list) or not 1 <= len(films) <= 150:
        raise ValueError('Catalogue size is outside the reviewed bound')
    if not isinstance(topics, list) or not 1 <= len(topics) <= 40:
        raise ValueError('Topic list is outside the reviewed bound')
    topic_ids, film_ids = set(), set()
    for topic in topics:
        ident = text(topic['id'], 'topic ID', 80)
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,79}', ident) or ident in topic_ids:
            raise ValueError('Invalid or duplicate topic')
        topic_ids.add(ident)
        text(topic['name'], 'topic name', 100)
    for film in films:
        ident = text(film['id'], 'film ID', 100)
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,99}', ident) or ident in film_ids:
            raise ValueError('Invalid or duplicate film ID')
        film_ids.add(ident)
        for key, limit in [('title', 180), ('credits', 500), ('publisher', 200), ('synopsis', 220),
                           ('availability', 650), ('content_note', 400)]:
            text(film[key], key, limit)
        if 'cover_title' in film:
            text(film['cover_title'], 'cover title', 100)
        if film['viewing'] not in KINDS:
            raise ValueError('Unknown viewing scope')
        if not isinstance(film['topics'], list) or not film['topics'] or not set(film['topics']) <= topic_ids:
            raise ValueError('Unknown topic in film')
        url(film['watch_url'])
        year = film.get('year')
        if year is not None and (type(year) is not int or not 1880 <= year <= datetime.now(timezone.utc).year):
            raise ValueError('Invalid film year')
        if film.get('runtime') is not None:
            text(film['runtime'], 'runtime', 100)
        providers = [('youtube_id', r'[A-Za-z0-9_-]{11}'), ('pbs_id', r'[0-9]{10}'),
                     ('vimeo_id', r'[0-9]{6,12}'), ('nfb_slug', r'[a-z0-9]+(?:_[a-z0-9]+)*')]
        present = []
        for key, pattern in providers:
            value = film.get(key)
            if value is not None:
                if not isinstance(value, str) or not re.fullmatch(pattern, value) or (key == 'nfb_slug' and len(value) > 100):
                    raise ValueError('Invalid ' + key)
                present.append(key)
        if len(present) > 1:
            raise ValueError('Only one player provider per selection')
        if 'pbs_route' in film and film['pbs_route'] not in ('stationplayer', 'viralplayer'):
            raise ValueError('Invalid PBS route')
        if 'thumbnail_url' in film and film['thumbnail_url'] is not None:
            thumbnail_url(film['thumbnail_url'])
        if 'thumbnail_credit' in film and film['thumbnail_credit'] is not None:
            text(film['thumbnail_credit'], 'thumbnail credit', 500)
        if 'thumbnail_source' in film and film['thumbnail_source'] is not None:
            url(film['thumbnail_source'])
        if not isinstance(film['sources'], list) or not film['sources']:
            raise ValueError('Every title requires a source')
        for source in film['sources']:
            url(source['url']); checked(source['checked'])
            text(source['title'], 'source title', 250); text(source['publisher'], 'source publisher', 200)
    for resource in data.get('resources', []):
        url(resource['url']); checked(resource['checked'])
        text(resource['title'], 'resource title', 180); text(resource['text'], 'resource text', 650)
        text(resource['publisher'], 'resource publisher', 200)
    if data['featured'] not in film_ids:
        raise ValueError('Featured film is missing')
    return data


def read(rel):
    return (SOURCE / rel).read_text(encoding='utf-8')


def player(film):
    if film.get('youtube_id'):
        return 'youtube', film['youtube_id'], 'https://www.youtube-nocookie.com/embed/' + film['youtube_id'] + '?autoplay=0&playsinline=1&rel=0'
    if film.get('pbs_id'):
        route = film.get('pbs_route', 'stationplayer')
        return 'pbs', film['pbs_id'], 'https://player.pbs.org/' + route + '/' + film['pbs_id'] + '/?autoPlay=false&autoplay=0'
    if film.get('vimeo_id'):
        return 'vimeo', film['vimeo_id'], 'https://player.vimeo.com/video/' + film['vimeo_id'] + '?autoplay=0&dnt=1&title=0&byline=0&portrait=0'
    if film.get('nfb_slug'):
        return 'nfb', film['nfb_slug'], 'https://www.nfb.ca/film/' + film['nfb_slug'] + '/embed/player/?autoplay=0'
    return '', '', ''


def render(data):
    e = lambda value: escape(str(value), quote=True)
    topics = {t['id']: t['name'] for t in data['topics']}
    feature = next(f for f in data['films'] if f['id'] == data['featured'])

    def sources(film):
        return ''.join('<li><a href="' + e(s['url']) + '" target="_blank" rel="noopener noreferrer">' + e(s['title']) +
                       '</a><span>' + e(s['publisher']) + ' · Checked <time datetime="' + e(s['checked']) + '">' +
                       e(s['checked']) + '</time></span></li>' for s in film['sources'])

    cards = []
    for i, film in enumerate(data['films'], 1):
        provider, ident, _ = player(film)
        attrs = {'theater-film': film['id'], 'featured': str(film['id'] == data['featured']).lower(),
                 'title': film['title'], 'search': ' '.join([film['title'], film['synopsis'], film['credits'],
                                                           film['publisher'], *[topics[t] for t in film['topics']]]),
                 'topic': ' '.join(film['topics']), 'provider': provider, 'video-id': ident,
                 'pbs-route': film.get('pbs_route', 'stationplayer'), 'watch-url': film['watch_url'],
                 'kind': KINDS[film['viewing']], 'availability': film['availability'], 'summary': film['synopsis'],
                 'content-note': film['content_note'], 'credits': film['credits'], 'runtime': film.get('runtime') or ''}
        at = ' '.join('data-' + k + '="' + e(v) + '"' for k, v in attrs.items())
        if film.get('thumbnail_url'):
            visual = '<img src="' + e(film['thumbnail_url']) + '" alt="' + e('Preview for ' + film['title']) + '" width="1280" height="720" loading="lazy" decoding="async" referrerpolicy="no-referrer">'
        else:
            visual = '<span class="th-art th-cover" aria-hidden="true"><span class="th-cover-number">' + str(i).zfill(2) + '</span><span class="th-cover-title">' + e(film.get('cover_title', film['title'])) + '</span></span>'
        facts = [KINDS[film['viewing']]]
        if film.get('runtime'):
            facts.append(film['runtime'])
        if film.get('year'):
            facts.append(str(film['year']) + (' premiere' if 'premiere' in film.get('year_scope', '').lower() else ''))
        thumb_note = ''
        if film.get('thumbnail_credit'):
            thumb_note = '<p class="th-thumbnail-credit">' + e(film['thumbnail_credit'])
            if film.get('thumbnail_source'):
                thumb_note += ' <a href="' + e(film['thumbnail_source']) + '" target="_blank" rel="noopener noreferrer">Thumbnail Source</a>'
            thumb_note += '</p>'
        cards.append(f'''<article class="th-film" id="film-{e(film['id'])}" {at}>
<a class="th-poster-button" href="{e(film['watch_url'])}" target="_blank" rel="noopener noreferrer" data-theater-select="{e(film['id'])}" aria-label="View {e(film['title'])} In Theater">{visual}</a>
<h3 class="th-film-title" id="title-{e(film['id'])}">{e(film['title'])}</h3>
<p class="th-card-meta">{e(' · '.join(facts))}</p>
<details class="th-card-details th-sources"><summary>Details And Official Source</summary><div class="th-cinema-details-body">
<p class="th-description">{e(film['synopsis'])}</p><p class="th-film-credits">{e(film['credits'])}</p>
<p class="th-film-access">{e(film['availability'])}</p><p class="th-content-note"><strong>Before Watching:</strong> {e(film['content_note'])}</p>
<a class="th-watch" href="{e(film['watch_url'])}" target="_blank" rel="noopener noreferrer">Open Official Source ↗</a>
<ul class="th-source-list">{sources(film)}</ul>{thumb_note}</div></details></article>''')

    provider, _, initial_url = player(feature)
    iframe = ('<iframe src="' + e(initial_url) + '" title="' + e(feature['title'] + ' | ' + provider + ' player') +
              '" referrerpolicy="strict-origin-when-cross-origin" allow="encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe>') if initial_url else ''
    slot_hidden = '' if iframe else ' hidden'
    close_hidden = '' if iframe else ' hidden'
    status = 'Player ready. Press Play in its controls. If unavailable, open the official source.' if iframe else 'This title is available from its official source. No unavailable player is substituted.'
    nav = '<a class="nh-link" href="#collection">Collection</a><a class="nh-link" href="/nations/directory">Nations</a>'
    sheet = ''.join('<li><a href="' + href + '">' + label + '</a></li>' for label, href in
                    [('The Screening Room', '#screening'), ('The Collection', '#collection'), ('How We Curate', '#curation'),
                     ('Nations Directory', '/nations/directory'), ('Mission', '/#mission')])
    header = read('tools/nations/partials/header.html').replace('{{{nav_links}}}', nav).replace('{{{sheet_links}}}', sheet).replace('aria-label="Nations"', 'aria-label="Theater"').replace('Indigenous nations today', 'ZOTHEOS Theater')
    options = ''.join('<option value="' + e(k) + '">' + e(v) + '</option>' for k, v in topics.items())
    companions = ''.join('<article><h3>' + e(r['title']) + '</h3><p>' + e(r['text']) + '</p><a class="th-watch" href="' + e(r['url']) + '" target="_blank" rel="noopener noreferrer">Read The Official Resource ↗</a><p class="th-art-credit">' + e(r['publisher']) + ' · Checked <time datetime="' + e(r['checked']) + '">' + e(r['checked']) + '</time></p></article>' for r in data.get('resources', []))
    companion_section = '<section class="th-companions" aria-labelledby="companion-heading"><div class="th-section-heading"><h2 id="companion-heading" class="th-section-title">Beyond The Screen</h2><p class="th-kicker">Research · Restoration · Education</p></div><div class="th-companion-grid">' + companions + '</div></section>' if companions else ''
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover"><meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="POLICY_PLACEHOLDER"><title>ZOTHEOS Theater | Stories That Stay With You</title>
<meta name="description" content="Documentaries and recorded presentations on Indigenous histories, sovereignty and renewal. Real previews, clear sources and ready players without autoplay.">
<link rel="canonical" href="https://zotheos.org/theater"><meta property="og:title" content="ZOTHEOS Theater"><meta property="og:type" content="website"><meta property="og:url" content="https://zotheos.org/theater"><meta name="theme-color" content="#000000" id="themeColorMeta"><link rel="icon" href="/zotheos_icon.ico?v=3">
<script>{read('tools/nations/partials/bootstrap.js')}</script><style id="zth-fonts">{read('tools/nations/partials/fonts-brand.css')}</style>{read('tools/nations/partials/fonts-names.css')}
<link rel="preload" as="font" type="font/woff2" href="/static/fonts/instrument-serif-latin.woff2" crossorigin><link rel="stylesheet" href="/static/theater/theater.css"></head>
<body>{header}<main id="main" class="th-page th-cinema">
<header class="th-cinema-heading"><p class="th-kicker">ZOTHEOS Theater · Indigenous Voices First</p><h1 id="theater-heading">Stories That Stay With You.</h1><p>Histories to face. Communities to listen to. Futures they are shaping.</p></header>
<section id="screening" class="th-screening-layout" aria-labelledby="theaterTitle"><div>
<div class="th-stage-shell"><svg class="th-stepped-frame" viewBox="0 0 1200 675" preserveAspectRatio="none" aria-hidden="true" focusable="false"><path class="th-frame-structure" d="M1 38H19V19H38V1H1162V19H1181V38H1199V637H1181V656H1162V674H38V656H19V637H1Z"/><path class="th-frame-glow" d="M1 38H19V19H38V1H1162V19H1181V38H1199V637H1181V656H1162V674H38V656H19V637H1Z"/></svg>
<div class="th-screen"><div class="th-stage-fallback"><p>Watch At Your Pace.</p><p>Use the player controls or open the official source. Viewing restrictions can vary.</p></div><div id="theaterPlayer" class="th-player"{slot_hidden}>{iframe}</div></div></div>
<p id="theaterConsent" class="th-provider-line">Thumbnails and the selected ready player connect automatically to their providers on opening this page. They receive your IP address and request information. Playback begins only when you press Play.</p>
<div class="th-player-controls th-provider-actions"><button id="theaterLoad" type="button" class="th-watch" aria-describedby="theaterTitle theaterConsent" hidden>Load Player</button><button id="theaterClose" type="button" class="th-select"{close_hidden}>Unload Player</button><button id="theaterMotion" type="button" class="th-select" aria-pressed="false">Still Frame</button><a class="th-watch" id="theaterWatch" href="{e(feature['watch_url'])}" target="_blank" rel="noopener noreferrer">Open Official Source ↗</a></div>
<p id="theaterPlayerStatus" class="th-provider-line" role="status">{e(status)}</p></div>
<div class="th-now-watching"><p class="th-kicker">Now In The Screening Room</p><h2 id="theaterTitle" class="th-feature-title" tabindex="-1">{e(feature['title'])}</h2>
<p class="th-now-meta"><span id="theaterKind">{e(KINDS[feature['viewing']])}</span><span id="theaterRuntime">{e(feature.get('runtime') or '')}</span></p><p id="theaterDescription" class="th-description">{e(feature['synopsis'])}</p>
<details class="th-cinema-details"><summary>Viewing Notes, Content And Sources</summary><div class="th-cinema-details-body"><p id="theaterAvailability">{e(feature['availability'])}</p><div><strong>Before Watching</strong><p id="theaterContentNote">{e(feature['content_note'])}</p></div><p id="theaterCredits">{e(feature['credits'])}</p><ul id="theaterSources" class="th-source-list">{sources(feature)}</ul></div></details></div></section>
<section id="collection" class="th-catalogue" aria-labelledby="collection-heading"><div class="th-section-heading"><h2 id="collection-heading" class="th-section-title">Explore The Collection</h2><p class="th-kicker">Distinct Stories · Cited Sources</p></div>
<div id="theaterTools" class="th-tools" hidden><div><label for="theaterSearch">Search Titles, People And Subjects</label><input id="theaterSearch" type="search" placeholder="Try land, language or family" autocomplete="off"></div><div><label for="theaterTopic">Explore A Subject</label><select id="theaterTopic"><option value="all">All Subjects</option>{options}</select></div><button id="theaterClear" class="th-select" type="button">Clear Filters</button><p id="theaterStatus" role="status"></p></div>
<div id="theaterEmpty" class="th-empty" hidden><h3>No Matching Stories</h3><p>Try a broader search or choose Clear Filters above to see the whole collection.</p></div><div class="th-film-grid">{''.join(cards)}</div></section>
{companion_section}
<section id="curation" class="th-method" aria-labelledby="curation-heading"><div><p class="th-kicker">How We Curate</p><h2 id="curation-heading" class="th-section-title">Attention With Responsibility.</h2></div><div><p>Distinct stories, official sources and honest viewing notes. No film stands for every Nation.</p><details class="th-cinema-details"><summary>Read Our Curation And Historical Context</summary><div class="th-cinema-details-body"><p>We read official filmmaker, publisher and community sources before adding a title. Credits, source-check dates and viewing limits remain with each story. Inclusion is not an endorsement by a Nation, independent verification of every statement or a claim that the full recording was watched for this collection.</p><p>Trailers, excerpts and recorded presentations are labeled. Official viewing pages may require payment, an account or access from a particular country. Availability can change. Videos remain with their authorized providers; ZOTHEOS does not copy or host them.</p><h3>History In Context</h3><p>The collection includes the official <em>Daughter of a Lost Bird</em> excerpt on Indigenous adoption. Its child-removal percentage is historical testimony about research before the Indian Child Welfare Act, not a present-day removal rate. <a href="https://www.nicwa.org/what-is-icwa/" target="_blank" rel="noopener noreferrer">Read NICWA’s Historical Context</a>.</p><p>This growing collection is incomplete. Corrections, living cultures, community-led restoration and careful source review guide its growth.</p></div></details><a class="th-watch" href="/nations/resources">Continue With Histories And Resources ↗</a></div></section>
</main><footer class="ft"><div class="ft-in"><div class="ft-top"><div><a class="ft-brand" href="/" aria-label="ZOTHEOS home"><img src="/static/zotheos_logo.png" width="133" height="28" alt=""></a><p class="ft-tag">Truth. Dignity. Sovereignty.</p><p class="ft-founder">Founded by <strong>David Garcia</strong><br>ZOTHEOS LLC</p></div><nav class="ft-links" aria-label="Footer"><div class="ft-col"><span class="ft-col-l">Explore</span><a href="/">Home</a><a href="/#mission">Mission</a><a href="/theater" aria-current="page">Theater</a><a href="/nations">Indigenous Nations Today</a><a href="/nations/directory">Nations Directory</a><a href="/nations/resources">Histories And Resources</a><a href="/game">Play And Learn</a></div><div class="ft-col"><span class="ft-col-l">Your Choice</span><a href="#theater-privacy">Theater Privacy</a><a href="/#site-privacy">Website Privacy</a><a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">YouTube Provider Privacy</a><a href="https://www.pbs.org/about/about-pbs/privacy-policy/" target="_blank" rel="noopener noreferrer">PBS Provider Privacy</a></div></nav><p class="ft-meta">© {datetime.now(timezone.utc).year} ZOTHEOS LLC<br>Film and preview rights remain with their owners.</p></div><div class="ft-block" id="theater-privacy"><p class="lbl">Theater Privacy</p><div><p>Fonts and page code load from this site. Theme and motion preferences stay in your browser. The Theater does not save searches or film selections.</p><p>Official thumbnails load automatically from their listed image providers. The selected YouTube, PBS, Vimeo or National Film Board player also loads automatically, ready for its Play control. These providers receive your IP address and request information when contacted; their own privacy policies apply. No autoplay permission is granted.</p><p>YouTube uses its privacy-enhanced player domain and Vimeo requests its do-not-track mode. Neither makes playback anonymous or guarantees that a provider collects no data. Unload Player removes the frame. Loading or selecting another available player contacts its provider again.</p><p>Source links contact their destinations when followed. Publishers can restrict or remove a title. If playback fails, use the official source. <a href="mailto:contact@zotheos.org">Report A Correction</a>.</p></div></div></div></footer>
<script>{read('tools/nations/partials/appearance.js')}</script><script>{read('static/theater/theater.js')}</script></body></html>
'''


def main():
    global SOURCE
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=SOURCE)
    ap.add_argument('--source-root', type=Path, default=None)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    if args.source_root:
        SOURCE = args.source_root
    elif not (SOURCE / 'tools/nations/partials/header.html').is_file() and (args.root / 'tools/nations/partials/header.html').is_file():
        SOURCE = args.root
    sys.path.insert(0, str(SOURCE / 'tools'))
    try:
        data = validate(json.loads((args.root / 'data/theater/films.json').read_text(encoding='utf-8')))
        body = render(data)
        from csp_sync import page_hashes, fix_policy, meta_policy
        body = body.replace('POLICY_PLACEHOLDER', meta_policy(fix_policy(POLICY, page_hashes(body))))
        output = args.root / 'theater.html'
        if args.check:
            if not output.is_file() or output.read_text(encoding='utf-8') != body:
                raise ValueError('Theater output is stale; run tools/theater_build.py')
        else:
            output.write_text(body, encoding='utf-8', newline='\n')
        print(f"Theater: {len(data['films'])} cited titles; " + ('output current' if args.check else 'rendered'))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print('Theater: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
