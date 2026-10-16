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
KINDS = {"recorded-program": "Recorded Program", 'excerpt': 'Official Excerpt', 'trailer': 'Official Trailer', 'full-film': 'Full Film',
         'official-page': 'Official Page', 'short': 'Short Film'}
REGIONS = {'north-america':'North America', 'central-america-caribbean':'Central America And Caribbean', 'south-america':'South America', 'arctic':'Arctic', 'africa':'Africa', 'europe':'Europe', 'asia':'Asia', 'oceania':'Oceania', 'global':'Across Regions', 'unindexed':'Location Not Yet Indexed'}
FORMS = {'documentary':'Documentary', 'animation':'Animation', 'drama':'Drama', 'talk':'Recorded Talk', 'news':'News And Reporting', 'other':'Other Format'}
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
            r'/(?:vi|vi_webp)/[A-Za-z0-9_-]{11}/(?:default|mqdefault|hqdefault|hq720|sddefault|maxresdefault|maxres2|[0-3])\.(?:jpg|webp)', p.path):
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
    if not isinstance(films, list) or not 1 <= len(films) <= 500:
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
        if 'region' in film and film['region'] not in REGIONS:
            raise ValueError('Invalid story region')
        if 'form' in film and film['form'] not in FORMS:
            raise ValueError('Invalid film form')
        if 'location' in film:
            text(film['location'], 'story location', 180)
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
                     ('vimeo_id', r'[0-9]{6,12}'), ('nfb_slug', r'[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*')]
        present = []
        for key, pattern in providers:
            value = film.get(key)
            if value is not None:
                if not isinstance(value, str) or not re.fullmatch(pattern, value) or (key == 'nfb_slug' and len(value) > 100):
                    raise ValueError('Invalid ' + key)
                present.append(key)
        if film.get('nfb_preview_slug') is not None:
            text(film['nfb_preview_slug'], 'NFB preview slug', 100)
            if not film.get('nfb_slug') or not re.fullmatch(r'[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*', film['nfb_preview_slug']) or film.get('nfb_preview_type') not in ('trailer','promo_clip') or film['viewing'] not in ('trailer','excerpt'):
                raise ValueError('Invalid NFB trailer selection')
        if film.get('nfb_preview_type') is not None and not film.get('nfb_preview_slug'):
            raise ValueError('An NFB preview type requires its supplied clip slug')
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
        trailer = film['nfb_preview_type'] + '/' + film['nfb_preview_slug'] + '/' if film.get('nfb_preview_slug') else ''
        return 'nfb', film['nfb_slug'], 'https://www.nfb.ca/film/' + film['nfb_slug'] + '/' + trailer + 'embed/player/?auto_play=false&autoplay=0'
    return '', '', ''


CATALOGUE_ROOT = None
PREVIEW_AUTOPLAY = True
POSTER_SIZES = '(max-width: 359px) 132px, (max-width: 719px) calc(50vw - 23px), (max-width: 1179px) calc(33vw - 30px), (max-width: 1439px) calc(25vw - 32px), 330px'
RAIL_SIZES = '(max-width: 719px) 168px, 200px'
# Preview gate (DA-M1). A story the page may start by itself must carry no hold. These Before Watching terms hold a
# story until the visitor presses Play: violence, abuse, death and grief, sexual harm, trauma, school and family
# removal, slavery, racism and discrimination, incarceration, addiction. Everything in the family subject is held too.
# Threats, conflict and dispossession alone do not hold. A curated `preview: "hold"` or `"allow"` in the record wins.
HOLD_TERMS = re.compile(r'\b(violen\w*|abus\w*|massacre\w*|murder\w*|death\w*|killing\w*|killed|sexual|trauma\w*|'
                        r'boarding schools?|residential schools?|removal|separation|slave\w*|forced labou?r|racis\w*|'
                        r'transphobia|incarcerat\w*|bereavement|grief|addiction|drugs|coercion|discrimination|genocide)\b', re.I)
AUDIO_TERMS = re.compile(r'\baudio-led\b|\bsoundscape\b', re.I)
NEW_TAB = ' <span aria-hidden="true">↗</span><span class="th-sr"> (opens a new tab)</span>'
NEW_TAB_PLAIN = '<span class="th-sr"> (opens a new tab)</span>'
ICONS = {
    'play': '<svg class="i i-play" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M8 5.5v13l10.5-6.5z"/></svg>',
    'pause': '<svg class="i i-pause" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M7 5.5h3.5v13H7zM13.5 5.5H17v13h-3.5z"/></svg>',
    'sound': '<svg class="i i-sound" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3.5 9.5h4l5-4v13l-5-4h-4z"/><path class="s" d="M15.5 9.5c1.3 1.4 1.3 3.6 0 5M18 7c2.7 2.8 2.7 7.2 0 10"/></svg>',
    'muted': '<svg class="i i-muted" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3.5 9.5h4l5-4v13l-5-4h-4z"/><path class="s" d="M15.5 9.5l5 5M20.5 9.5l-5 5"/></svg>',
    # the CC mark: a box with two squared letters C (outline: off; filled: a confirmed track is showing)
    'cc': '<svg class="i i-cc" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path class="s" d="M3.5 6.5h17v11h-17z"/><path class="s" d="M10.5 9.5H7.5v5h3M16.5 9.5h-3v5h3"/></svg>',
    'cc-on': '<svg class="i i-cc-on" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 6h18v12H3z"/><path class="k" d="M10.5 9.5H7.5v5h3M16.5 9.5h-3v5h3"/></svg>',
    'next': '<svg class="i i-next" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M6 6v12l8.5-6z"/><path d="M16 6h2.5v12H16z"/></svg>',
    'back': '<svg class="i i-back" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 5h7v6H4zM13 5h7v6h-7zM4 13h7v6H4zM13 13h7v6h-7z"/></svg>',
    'screen': '<svg class="i i-screen" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path class="s" d="M3.5 5.5h17v11h-17z"/><path d="M8 19h8v1.5H8z"/></svg>',
    'light': '<svg class="i i-light" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path class="s" d="M3.5 19.5h5v-4h4v-4h4v-4h4"/></svg>',
    'light-off': '<svg class="i i-light-off" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path class="s" d="M3.5 19.5h5v-4h4v-4h4v-4h4"/><path d="M15 15.5h2v4h-2zM19 15.5h2v4h-2z"/></svg>',
    'link': '<svg class="i" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path class="s" d="M10 14l4-4M8.5 11.5l-2 2a3 3 0 0 0 4.2 4.2l2-2M15.5 12.5l2-2a3 3 0 0 0-4.2-4.2l-2 2"/></svg>',
}


def compact_js(src):
    """Conservative size pass for the inline scripts: drops /* */ comments and indentation. The sources use no
    template literals or multi-line strings, and no string or regex contains a comment opener (asserted)."""
    if '`' in src:
        raise ValueError('Inline scripts must not use template literals')
    out, i = [], 0
    while True:
        j = src.find('/' + '*', i)
        if j < 0:
            out.append(src[i:])
            break
        out.append(src[i:j])
        i = src.index('*' + '/', j) + 2
    lines = [ln.strip() for ln in ''.join(out).splitlines()]
    return chr(10).join(ln for ln in lines if ln)


def optional(rel):
    path = SOURCE / rel
    return path.read_text(encoding='utf-8') if path.is_file() else ''


def optional_json(rel):
    raw = optional(rel)
    return json.loads(raw) if raw else {}


def caption_tracks(catalogue):
    """{record id or trailer id: (kind, language)}: kind is supplied, automatic, none or open (in the picture)."""
    path = (CATALOGUE_ROOT or SOURCE) / 'data/theater/caption_tracks.json'
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if set(data) != {'version', 'checked', 'method', 'trailers', 'records'} or type(data['version']) is not int or data['version'] != 1:
        raise ValueError('Invalid caption snapshot schema')
    if not isinstance(data['method'], str) or not data['method'].strip():
        raise ValueError('Caption snapshot method is required')
    if not isinstance(data['checked'], list) or not data['checked']:
        raise ValueError('Caption snapshot check timestamps are required')
    for stamp in data['checked']:
        parsed = datetime.fromisoformat(stamp)
        if parsed.tzinfo is None or parsed > datetime.now(timezone.utc):
            raise ValueError('Caption snapshot timestamp must be actual and timezone-aware')
    films = {f['id']: f for f in catalogue['films']}
    trailer_ids = {f.get('trailer_youtube_id') for f in catalogue['films'] if f.get('trailer_youtube_id')}
    for group, allowed in (('records', set(films)), ('trailers', trailer_ids)):
        if not isinstance(data[group], dict) or not set(data[group]).issubset(allowed):
            raise ValueError('Caption snapshot contains an unknown record or trailer')
        for ident, row in data[group].items():
            if not isinstance(row, dict) or set(row) - {'kind', 'lang', 'watch_page'} or not {'kind', 'lang'}.issubset(row):
                raise ValueError('Caption snapshot fields are invalid for ' + ident)
            if 'watch_page' in row:
                if group != 'trailers' or not isinstance(row['watch_page'], dict) or set(row['watch_page']) != {'kind', 'lang'}:
                    raise ValueError('Caption watch-page observation is invalid')
                observed = row['watch_page']
                if observed['kind'] not in ('supplied', 'automatic', 'none') or not isinstance(observed['lang'], str) or not re.fullmatch(r'(?:[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?)?', observed['lang']):
                    raise ValueError('Caption watch-page observation is invalid')
    out = {}
    for group in ('records', 'trailers'):
        for ident, row in data.get(group, {}).items():
            if not isinstance(row['lang'], str):
                raise ValueError('Caption language must be text')
            kind, lang = row['kind'], row['lang']
            if kind not in ('supplied', 'automatic', 'none', 'open') or not re.fullmatch(r'(?:[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?)?', lang):
                raise ValueError('Invalid caption data for ' + ident)
            out[ident] = (kind, lang)
    return out


def preview_policy(catalogue):
    path = (CATALOGUE_ROOT or SOURCE) / 'data/theater/preview_policy.json'
    if not path.is_file():
        return {}
    policy = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(policy, dict) or set(policy) != {'version', 'records'} or type(policy['version']) is not int or policy['version'] != 1:
        raise ValueError('Invalid automatic-preview policy schema')
    records = policy['records']
    ids = {f['id'] for f in catalogue['films']}
    if not isinstance(records, dict) or not set(records).issubset(ids):
        raise ValueError('Automatic-preview policy contains an unknown record')
    for ident, row in records.items():
        if not isinstance(row, dict) or set(row) != {'state', 'reason'} or row['state'] != 'hold':
            raise ValueError('Only explicit automatic-preview holds are supported')
        text(row['reason'], 'Automatic-preview hold reason', 500)
        if any(ord(c) < 32 for c in row['reason']):
            raise ValueError('Automatic-preview reason contains a control character')
    return records


def render(data):
    e = lambda value: escape(str(value) if str(value).startswith("https://") else str(value).replace("–", "-").replace("—", ", "), quote=True)
    topics = {t['id']: t['name'] for t in data['topics']}
    feature = next(f for f in data['films'] if f['id'] == data['featured'])
    variants, crops, captions, langs = {}, {}, caption_tracks(data), {}
    preview_holds = preview_policy(data)
    hidden = lambda cond: '' if cond else ' hidden'

    def year_text(film):
        if not film.get('year'):
            return ''
        return str(film['year']) + (' premiere' if 'premiere' in film.get('year_scope', '').lower() else '')

    def shown_title(film):
        return langs[film['id']]['original'] if film['id'] in langs else film['title']

    def title_html(film):
        """The title as published by its maker, in its own language; an English rendering follows as a translation."""
        tl = langs.get(film['id'])
        if not tl:
            return e(film['title']), ''
        inner = e(tl['original'])
        if tl['english']:
            inner += ' <span class="th-title-en" lang="en">(English: ' + e(tl['english']) + ')</span>'
        return inner, ' lang="' + tl['lang'] + '"'

    def trailer(film):
        tid = film.get('trailer_youtube_id') or ''
        return tid if film['viewing'] == 'full-film' and re.fullmatch(r'[A-Za-z0-9_-]{11}', tid) else ''

    def preview_state(film, provider):
        """ok: the page may start a muted preview of this story. Otherwise the reason it waits for Play."""
        if provider not in ('youtube', 'vimeo'):
            return ''
        if film['id'] in preview_holds:
            return 'hold-captions'
        curated = film.get('preview')
        if HOLD_TERMS.search(film['content_note']) or 'family' in film['topics']:
            return 'hold-note'
        if AUDIO_TERMS.search(film['content_note']):
            return 'hold-audio'
        if curated == 'hold':
            return 'hold-note'
        if curated != 'allow':
            if HOLD_TERMS.search(film['content_note']) or 'family' in film['topics']:
                return 'hold-note'
            if AUDIO_TERMS.search(film['content_note']):
                return 'hold-audio'
        if film['viewing'] == 'full-film':
            # a full film previews only through its own trailer, and only if that trailer offers captions here
            if not trailer(film) or captions.get(trailer(film), ('', ''))[0] not in ('supplied', 'automatic', 'open'):
                return 'hold-full'
        elif provider == 'youtube' and captions.get(film['id'], ('', ''))[0] not in ('supplied', 'automatic', 'open'):
            return 'hold-captions'
        return 'ok'                          # Vimeo: the script also waits for the provider to list a caption track

    def access_mark(film, provider):
        if not provider:
            return 'Official Site Only'
        if re.search(r'\bregistration\b', film['availability'], re.I):
            return 'Registration At Source'
        return ''

    def sources(film):
        return ''.join('<li><a href="' + e(s['url']) + '" target="_blank" rel="noopener noreferrer">' + e(s['title']) + NEW_TAB_PLAIN +
                       '</a><span>' + e(s['publisher']) + ' · Checked <time datetime="' + e(s['checked']) + '">' +
                       e(s['checked']) + '</time></span></li>' for s in film['sources'])

    def thumb_note(film):
        if not film.get('thumbnail_credit'):
            return ''
        out = '<p class="th-thumbnail-credit">' + e(film['thumbnail_credit'])
        if film.get('thumbnail_source'):
            out += ' <a href="' + e(film['thumbnail_source']) + '" target="_blank" rel="noopener noreferrer">Thumbnail Source' + NEW_TAB_PLAIN + '</a>'
        return out + '</p>'

    def crop_attrs(film):
        c = crops.get(film['id'])
        if not c:
            return ''
        mode, left, right, k = c
        if mode == 'fill':
            return f' data-crop="fill" style="--th-crop:{k:.4f}"'
        return f' data-crop="inset" style="--th-crop-l:{left * 100:.2f}%;--th-crop-r:{right * 100:.2f}%"'

    def card(film, i):
        provider, ident, _ = player(film)
        attrs = {'theater-film': film['id']}
        if film['id'] == data['featured']:
            attrs['featured'] = 'true'
        attrs.update({'search': ' '.join([film['title'], film['synopsis'], film['credits'], film['publisher'], film.get('location',''), FORMS.get(film.get('form'),''), *[topics[t] for t in film['topics']]]), 'summary': film['synopsis'], 'credits': film['credits'], 'publisher': film['publisher'], 'perspective': film.get('perspective') or '', 'availability': film['availability'], 'content-note': film['content_note'], 'location': film.get('location') or ''})
        attrs['title'] = film['title']     # the published contract: the card names its full identifying title
        attrs.update({'topic': ' '.join(film['topics']), 'provider': provider, 'video-id': ident, 'watch-url': film['watch_url'],
                      'kind': KINDS[film['viewing']], 'form': FORMS.get(film.get('form'), ''), 'runtime': film.get('runtime') or '',
                      'year': year_text(film), 'region': film.get('region', 'unindexed'), 'viewing': film['viewing']})
        if provider == 'pbs':
            attrs['pbs-route'] = film.get('pbs_route', 'stationplayer')
        if film.get('nfb_preview_slug'):
            attrs['nfb-preview'] = film['nfb_preview_slug']
            attrs['nfb-preview-type'] = film['nfb_preview_type']
        tid = trailer(film) if provider == 'youtube' else ''
        cap = captions.get(film['id'])
        if provider in ('youtube', 'vimeo'):
            attrs['preview'] = preview_state(film, provider)
            if cap:
                attrs['captions'], attrs['cap-lang'] = cap
            if tid:
                attrs['trailer-id'] = tid
                tcap = captions.get(tid)
                if tcap:
                    attrs['trailer-captions'], attrs['trailer-cap-lang'] = tcap
        at = ' '.join('data-' + k + '="' + e(v) + '"' for k, v in attrs.items() if v != '' or k in ('provider', 'video-id'))
        shown = shown_title(film)
        th, tlang = title_html(film)
        if film.get('thumbnail_url'):
            ss = ', '.join(e(u) + ' ' + str(w) + 'w' for u, w in variants.get(film['id'], []))
            visual = ('<img src="' + e(film['thumbnail_url']) + '"' + (' srcset="' + ss + '" sizes="' + POSTER_SIZES + '"' if ss else '') +
                      ' alt="' + e('Preview for ' + shown) + '" width="1280" height="720" loading="lazy" decoding="async" referrerpolicy="no-referrer">')
        else:
            visual = '<span class="th-art th-cover" aria-hidden="true"><span class="th-cover-number">' + str(i).zfill(2) + '</span><span class="th-cover-title">' + e(film.get('cover_title', film['title'])) + '</span></span>'
        facts = [KINDS[film['viewing']]]
        if film.get('form'):
            facts.append(FORMS[film['form']])
        if film.get('runtime'):
            facts.append(film['runtime'])
        if film.get('year'):
            facts.append(year_text(film))
        meta = '&nbsp;· '.join('<span class="th-nw">' + e(part) + '</span>' for fact in facts for part in fact.split(' · '))
        where = '' if provider else '<span class="th-poster-where" aria-hidden="true">Official Site ↗</span>'
        mark = access_mark(film, provider)
        persp = ('<p class="th-film-perspective"><strong>Whose Story<span class="th-sr">:</span></strong> <span>' + e(film['perspective']) + '</span></p>') if film.get('perspective') else ''
        return (f'<article class="th-film" id="film-{e(film["id"])}" {at}>\n'
                f'<a class="th-poster-button" href="{e(film["watch_url"])}" target="_blank" rel="noopener noreferrer" data-theater-select="{e(film["id"])}" aria-label="Explore {e(shown)}"{crop_attrs(film)}>{visual}<span class="th-poster-kind" aria-hidden="true">{e(KINDS[film["viewing"]])}</span>{where}</a>\n'
                f'<h3 class="th-film-title" id="title-{e(film["id"])}"{tlang}>{th}</h3>\n'
                f'<p class="th-card-meta">{meta}</p><p class="th-film-credits">{e(film["credits"])}</p><p class="th-card-byline"><span class="th-card-publisher">{e(film["publisher"])}</span><span class="th-card-place">{e(film.get("location", ""))}</span></p>'
                + (f'<p class="th-card-access">{e(mark)}</p>' if mark else '') + '\n'
                f'<details class="th-card-details th-sources"><summary>Details And Official Source</summary><div class="th-cinema-details-body">\n'
                f'<p class="th-description">{e(film["synopsis"])}</p>{persp}\n'
                f'<p class="th-film-access">{e(film["availability"])}</p><p class="th-content-note"><strong>Before Watching<span class="th-sr">:</span></strong> <span>{e(film["content_note"])}</span></p>\n'
                f'<p class="th-card-links"><a class="th-watch" href="{e(film["watch_url"])}" target="_blank" rel="noopener noreferrer">Open Official Source{NEW_TAB}</a> <a class="th-watch th-story-link" href="/theater#film-{e(film["id"])}">Link To This Story</a></p>\n'
                f'<ul class="th-source-list">{sources(film)}</ul>{thumb_note(film)}</div></details></article>')

    def tbtn(ident, label, icons, extra='', short=None, state=None, pre=None, post=None):
        """A transport button. A toggle keeps one constant name (its pressed state is aria-pressed); the visible
        state word beside the name is for sight only (aria-hidden)."""
        lab = f'<span class="th-tlabel">{label}</span>' if short is None else \
              f'<span class="th-tlabel-long">{label}</span><span class="th-tlabel-short">{short}</span>'
        if pre or post:   # one text run, so the invitation reads as one phrase
            lab = (f'<span class="th-tname"><span class="th-tpre" aria-hidden="true">{pre}</span>' + lab +
                   f'<span class="th-tpost" aria-hidden="true">{post}</span></span>')
        if state is not None:
            lab += f'<span class="th-tstate" aria-hidden="true">{state}</span>'
        return (f'<button class="th-tbtn" id="{ident}" type="button" data-icon="{icons[0]}"{extra}>' +
                ''.join(ICONS[i] for i in icons) + lab + '</button>')

    cards = [card(f, i) for i, f in enumerate(data['films'], 1)]
    provider, _, base_url = player(feature)
    fshown = shown_title(feature)
    fth, ftlang = title_html(feature)
    # The featured iframe is noscript-only: it serves visitors without JavaScript and never contacts a provider before
    # an incoming story link is resolved. With JavaScript the script mounts the selected player.
    iframe = ('<noscript><iframe src="' + e(base_url) + '" title="' + e(fshown + ', ' + {'youtube': 'YouTube', 'vimeo': 'Vimeo', 'pbs': 'PBS', 'nfb': 'National Film Board'}.get(provider, provider) + ' player') +
              '" referrerpolicy="strict-origin-when-cross-origin" allow="encrypted-media; picture-in-picture; fullscreen" allowfullscreen></iframe></noscript>') if base_url else ''
    status = ('Use Play in the player, or open the official source. Viewing restrictions can vary.' if iframe else
              'This title is available from its official source. No unavailable player is substituted.')
    nav = '<a class="nh-link" href="#collection">Collection</a><a class="nh-link" href="/nations/directory">Nations</a><a class="nh-link" href="/">Home</a>'
    sheet = ''.join('<li><a href="' + href + '">' + label + '</a></li>' for label, href in
                    [('The Screening Room', '#screening'), ('The Collection', '#collection'), ('How Titles Are Selected', '#curation'),
                     ('Nations Directory', '/nations/directory'), ('Mission', '/#mission')])
    header = read('tools/nations/partials/header.html').replace('{{{nav_links}}}', nav).replace('{{{sheet_links}}}', sheet) \
        .replace('aria-label="Nations"', 'aria-label="Theater"').replace('Indigenous nations today', 'ZOTHEOS Theater')
    appearance_end = '\n</div>\n<nav class="nav-sheet"'
    if appearance_end not in header:
        raise ValueError('Shared Appearance insertion point is missing')
    header = header.replace(appearance_end, '\n' + read('tools/theater/appearance_rows.html') + appearance_end, 1)
    options = ''.join('<option value="' + e(k) + '">' + e(v) + '</option>' for k, v in topics.items())
    companions = ''.join('<article><h3>' + e(r['title']) + '</h3><p>' + e(r['text']) + '</p><a class="th-watch" href="' + e(r['url']) + '" target="_blank" rel="noopener noreferrer">Read The Official Resource' + NEW_TAB + '</a><p class="th-art-credit">' + e(r['publisher']) + ' · Checked <time datetime="' + e(r['checked']) + '">' + e(r['checked']) + '</time></p></article>' for r in data.get('resources', []))
    companion_section = '<details id="regional-resources" class="th-cinema-details th-regional"><summary>Regional Companion Resources</summary><section class="th-companions" aria-labelledby="companion-heading"><div class="th-section-heading"><h2 id="companion-heading" class="th-section-title">Beyond The Screen</h2><p class="th-kicker">Research · Restoration · Education</p></div><div class="th-companion-grid">' + companions + '</div></section></details>' if companions else ''
    region_options = ''.join('<option value="' + key + '">' + e(label) + '</option>' for key, label in REGIONS.items() if any(f.get('region', 'unindexed') == key for f in data['films']))
    viewing_options = ''.join('<option value="' + key + '">' + e(label) + '</option>' for key, label in KINDS.items())
    amb_attrs = ''
    composed = ''
    fyear = year_text(feature)
    fp = feature.get('location', '')
    fform = FORMS.get(feature.get('form'), '')
    fpersp = feature.get('perspective', '')
    switch = 'on' if PREVIEW_AUTOPLAY else 'off'
    desc = ('Documentaries and recorded presentations on Indigenous histories, sovereignty and renewal. Real previews, clear sources and players you control.' if PREVIEW_AUTOPLAY else
            'Documentaries and recorded presentations on Indigenous histories, sovereignty and renewal. Real previews, clear sources and ready players without autoplay.')
    # Sound and CC exist only with the switch on and for providers with a supported message interface. They are
    # reserved from first paint when the featured player has one (no layout shift), hidden without JavaScript.
    api_vis = '' if PREVIEW_AUTOPLAY and provider in ('youtube', 'vimeo') else ' hidden'
    transport = (tbtn('theaterPlay', 'Play', ['play', 'pause'], ' data-next="play" aria-describedby="theaterContentNote"' + api_vis) +
                 tbtn('theaterSound', 'Sound', ['muted', 'sound'], ' aria-pressed="false"' + api_vis, state='Off' if PREVIEW_AUTOPLAY else '', pre='Turn ', post=' On') +
                 tbtn('theaterCC', 'Captions', ['cc-on', 'cc'], ' aria-pressed="false"' + api_vis, short='CC', state='') +
                 tbtn('theaterNext', 'Next Story', ['next'], ' hidden') +
                 '<p class="th-native-note" id="theaterNativeNote" hidden></p>' +
                 tbtn('theaterMotion', 'Pause Light<span class="th-sr"> (ambient motion)</span>', ['light', 'light-off'], ' hidden aria-pressed="false" aria-label="Pause ambient light"', state=''))
    privacy_on = ('Thumbnails and the selected player connect to their providers when this page opens. They receive your IP address and request information. '
                  'Eligible YouTube and Vimeo previews start without sound when the screen and controls are in view, except in Still or when the device requests reduced motion. '
                  'A preview pauses outside the screen or when this tab is hidden. Your Pause holds until you choose Play. '
                  'Stories with difficult-content holds, audio-led programs and unconfirmed captions wait for Play. Native National Film Board and PBS controls remain available. '
                  'Provider playback reports and provider privacy policies apply. Sound starts only when you choose it.')
    privacy_off = ('Thumbnails and the selected ready player connect automatically to their providers. They receive your IP address and request information. Playback begins when you press Play.')
    return f'''<!DOCTYPE html>
<html lang="en" data-preview-autoplay="{switch}"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover"><meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="POLICY_PLACEHOLDER"><title>ZOTHEOS Theater | Stories That Stay With You</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="https://zotheos.org/theater"><meta property="og:title" content="ZOTHEOS Theater"><meta property="og:type" content="website"><meta property="og:url" content="https://zotheos.org/theater"><meta name="theme-color" content="#000000" id="themeColorMeta"><link rel="icon" href="/zotheos_icon.ico?v=3">
<script>{read('tools/nations/partials/bootstrap.js').rstrip()}
document.documentElement.setAttribute('data-js', '');</script><style id="zth-fonts">{read('tools/nations/partials/fonts-brand.css')}</style>{read('tools/nations/partials/fonts-names.css')}
<link rel="preload" as="font" type="font/woff2" href="/static/fonts/instrument-serif-latin.woff2" crossorigin><link rel="preload" as="font" type="font/woff2" href="/static/fonts/dm-sans-var-latin.woff2" crossorigin><link rel="stylesheet" href="/static/theater/theater.css"></head>
<body>{header}<main id="main" class="th-page th-cinema">
<header class="th-cinema-heading"><div class="th-masthead-title"><p class="th-kicker">ZOTHEOS Theater · Indigenous Voices First</p><h1 id="theater-heading">Stories That Stay With You.</h1></div><div class="th-masthead-note"><p>Indigenous histories and living communities, across Nations and borders. Stories of truth, dignity and renewal.</p><p class="th-library-scope">{len(data['films'])} Sourced Stories · Growing Worldwide</p></div></header>
<section id="screening" class="th-screening-layout" aria-label="{e('Screening room: ' + fshown)}" data-stage-state="{'ready' if iframe else 'source-only'}" data-provider="{provider or 'none'}">
<div class="th-now-head" id="theaterNow"><p class="th-kicker">Now In The Screening Room</p>
<h2 id="theaterTitle" class="th-feature-title" tabindex="-1"{ftlang}>{fth}</h2>
<p id="theaterCredits" class="th-creators">{e(feature['credits'])}</p>
<p class="th-perspective" id="theaterPerspectiveRow"{hidden(fpersp)}><span class="th-note-k">Whose Story<span class="th-sr">:</span></span> <span id="theaterPerspective">{e(fpersp)}</span></p>
<p class="th-now-tags"><span class="th-tag th-tag-kind" id="theaterKind">{e(KINDS[feature['viewing']])}</span><span class="th-tag" id="theaterForm"{hidden(fform)}>{e(fform)}</span></p>
<p class="th-before" id="theaterBefore"><span class="th-note-k">Before Watching<span class="th-sr">:</span></span> <span id="theaterContentNote">{e(feature['content_note'])}</span></p></div>
<div class="th-stage-col">
<div class="th-transport" id="theaterTransport" role="group" aria-label="Screening controls" data-needs-js>{transport}</div>
<div class="th-stage-shell" id="theaterStage"{amb_attrs}><div class="th-ambient" id="theaterAmbient" aria-hidden="true"></div>{composed}
<div class="th-screen" id="theaterScreen"><div class="th-stage-fallback"><p>Watch At Your Pace.</p><p>Use the player controls or open the official source. Viewing restrictions can vary.</p></div><div id="theaterPlayer" class="th-player"{hidden(iframe)}>{iframe}</div><div class="th-curtain" id="theaterCurtain" data-mode="loading" hidden><img id="theaterCurtainImg" alt="" decoding="async" referrerpolicy="no-referrer"><div class="th-curtain-note"><p id="theaterCurtainText"></p><p class="th-curtain-short">Review the Before Watching note, then press Play when you are ready.</p><button class="th-btn th-btn-solid th-curtain-play" id="theaterCurtainPlay" type="button" aria-describedby="theaterContentNote">Play</button><a class="th-btn th-btn-solid" id="theaterCurtainSource" href="{e(feature['watch_url'])}" target="_blank" rel="noopener noreferrer">Open Official Source{NEW_TAB}</a></div></div></div></div>
<p id="theaterPlayerStatus" class="th-status-line">{e(status)}</p><p id="theaterAnnounce" class="th-sr" role="status" aria-live="polite"></p>
<div class="th-upnext" id="theaterUpNext" role="region" aria-labelledby="theaterUpNextTitle" data-needs-js><div class="th-upnext-head"><p class="th-kicker" id="theaterUpNextTitle">Next In This Selection</p></div><ol class="th-upnext-list" id="theaterUpNextList"></ol></div>
<p id="theaterConsent" class="th-provider-line"><span data-when-autoplay="on">{e(privacy_on)}</span><span data-when-autoplay="off">{e(privacy_off)}</span></p>
</div>
<div class="th-now-rest">
<dl class="th-facts"><div><dt>Publisher</dt><dd id="theaterPublisher">{e(feature['publisher'])}</dd></div><div id="theaterYearRow"{hidden(fyear)}><dt>Year</dt><dd id="theaterYear">{e(fyear)}</dd></div><div id="theaterRuntimeRow"{hidden(feature.get('runtime'))}><dt>Runtime</dt><dd id="theaterRuntime">{e(feature.get('runtime') or '')}</dd></div><div id="theaterPlaceRow"{hidden(fp)}><dt>Place</dt><dd id="theaterLocation">{e(fp)}</dd></div></dl>
<div class="th-now-actions"><a class="th-btn th-btn-source" id="theaterWatch" href="{e(feature['watch_url'])}" target="_blank" rel="noopener noreferrer">Open Official Source{NEW_TAB}</a><a class="th-btn th-btn-quiet" id="theaterPermalink" href="/theater#film-{e(feature['id'])}">{ICONS['link']}<span>Link To This Story</span></a><a class="th-btn th-btn-quiet" id="theaterBack" href="#collection">{ICONS['back']}<span>Back To Collection</span></a></div>
<p id="theaterDescription" class="th-description">{e(feature['synopsis'])}</p>
<div class="th-notes"><p class="th-note"><span class="th-note-k">Viewing<span class="th-sr">:</span></span> <span id="theaterAvailability">{e(feature['availability'])}</span></p></div>
<details class="th-cinema-details th-now-sources"><summary>Sources And Checks</summary><div class="th-cinema-details-body"><ul id="theaterSources" class="th-source-list">{sources(feature)}</ul><div id="theaterThumbCredit">{thumb_note(feature)}</div></div></details></div></section>
<div class="th-dock" id="theaterDock" role="region" aria-label="Now playing" hidden data-needs-js><div class="th-dock-in"><span class="th-dock-thumb" id="theaterDockThumb"><img id="theaterDockImg" alt="" width="64" height="36" decoding="async" referrerpolicy="no-referrer"></span><p class="th-dock-title" id="theaterDockTitle"></p>{tbtn('theaterDockPlay', 'Pause', ['pause', 'play'], ' data-next="pause"')}{tbtn('theaterDockSound', 'Sound', ['muted', 'sound'], ' aria-pressed="false"', state='')}{tbtn('theaterDockBack', 'Back To Screen', ['screen'], '')}</div></div>
<section id="collection" class="th-catalogue" aria-labelledby="collection-heading"><div class="th-section-heading"><h2 id="collection-heading" class="th-section-title" tabindex="-1">Explore The Collection</h2><p class="th-kicker">Distinct Stories · Cited Sources</p></div>
<div id="theaterTools" class="th-tools" data-needs-js><div class="th-field th-field-search"><label for="theaterSearch">Search Titles, People And Subjects</label><input id="theaterSearch" type="search" placeholder="Try land, language or family" autocomplete="off"></div><button id="theaterFiltersToggle" class="th-btn th-filter-toggle" type="button" aria-expanded="false" aria-controls="theaterFilterPanel"><span>Filters</span><span class="th-filter-count" id="theaterFilterCount" hidden></span></button><div class="th-filter-panel" id="theaterFilterPanel"><div class="th-field"><label for="theaterTopic">Explore A Subject</label><select id="theaterTopic"><option value="all">All Subjects</option>{options}</select></div><div class="th-field"><label for="theaterRegion">Explore A Region</label><select id="theaterRegion"><option value="all">Worldwide</option>{region_options}</select></div><div class="th-field"><label for="theaterViewing">Choose A Viewing Type</label><select id="theaterViewing"><option value="all">Films, Shorts And More</option>{viewing_options}</select></div><div class="th-field"><label for="theaterAccess">Where To Watch</label><select id="theaterAccess"><option value="all">All Sources</option><option value="watch-here">Watch Here</option><option value="official-site">Official Site</option></select></div></div><button id="theaterClear" class="th-btn" type="button">Clear Filters</button><p id="theaterStatus" role="status"></p></div>
<div id="theaterEmpty" class="th-empty" hidden><h3>No Matching Stories</h3><p>Try a broader search or choose Clear Filters above to see the whole collection.</p></div><div class="th-film-grid">{''.join(cards)}</div><div class="th-library-more"><div class="th-progress" id="theaterProgress" aria-hidden="true" data-needs-js><span></span></div><button id="theaterMore" class="th-btn th-btn-solid" type="button" hidden>Show More Stories</button><a class="th-btn" href="#screening">Return To The Screening Room</a></div></section>
<section class="th-world-reading" aria-labelledby="world-reading-title"><p class="th-kicker">Across Nations And Borders</p><h2 id="world-reading-title" class="th-section-title">Keep Exploring.</h2><p>This collection is growing worldwide. Geographic labels help you browse; they do not define a people or limit their homelands. Coverage is uneven, and gaps stay visible.</p><div class="th-world-links"><a href="/nations/directory"><strong>Nations Worldwide</strong><span>Find distinct peoples, governments and their own sources.</span></a><a href="/nations/in/us"><strong>United States Nations</strong><span>Continue into the growing US directory and profiles.</span></a><a href="/nations/resources"><strong>Histories And Resources</strong><span>Follow the evidence beyond a film.</span></a><a href="/nations/coverage"><strong>Coverage And Gaps</strong><span>See what is represented and where work remains.</span></a></div></section>
{companion_section}
{read('tools/theater/translation.html')}
<section id="curation" class="th-method" aria-labelledby="curation-heading"><div><p class="th-kicker">How Titles Are Selected</p><h2 id="curation-heading" class="th-section-title">Attention With Responsibility.</h2></div><div><p>Distinct stories, official sources and honest viewing notes. No film stands for every Nation.</p><details class="th-cinema-details"><summary>Read The Selection Method And Historical Context</summary><div class="th-cinema-details-body"><p>Selection uses official filmmaker, publisher and community sources. Credits, source-check dates and viewing limits remain with each story. Inclusion is not an endorsement by a Nation, independent verification of every statement or a claim that the full recording was watched for this collection.</p><p>Trailers, excerpts and recorded presentations are labeled. Official viewing pages may require payment, an account or access from a particular country. Availability can change. Videos remain with their authorized providers; ZOTHEOS does not copy or host them.</p><h3>History In Context</h3><p>The collection includes the official <em>Daughter of a Lost Bird</em> excerpt on Indigenous adoption. Its child-removal percentage is historical testimony about research before the Indian Child Welfare Act, not a present-day removal rate. <a href="https://www.nicwa.org/what-is-icwa/" target="_blank" rel="noopener noreferrer">Read NICWA’s Historical Context</a>.</p><p>This growing collection is incomplete. Corrections, living cultures, community-led restoration and careful source review guide its growth.</p></div></details><a class="th-watch" href="/nations/resources">Continue With Histories And Resources ↗</a></div></section>
</main><footer class="ft"><div class="ft-in"><div class="ft-top"><div><a class="ft-brand" href="/" aria-label="ZOTHEOS home"><img src="/static/zotheos_logo.png" width="133" height="28" alt=""></a><p class="ft-tag">Truth. Dignity. Sovereignty.</p><p class="ft-founder">Built by <strong>David Garcia</strong><br>ZOTHEOS LLC</p></div><nav class="ft-links" aria-label="Footer"><div class="ft-col"><span class="ft-col-l">Explore</span><a href="/">Home</a><a href="/#mission">Mission</a><a href="/theater" aria-current="page">Theater</a><a href="/nations">Indigenous Nations Today</a><a href="/nations/directory">Nations Directory</a><a href="/nations/resources">Histories And Resources</a><a href="/game">Play And Learn</a></div><div class="ft-col"><span class="ft-col-l">Your Choice</span><a href="#theater-privacy">Theater Privacy</a><a href="/#site-privacy">Website Privacy</a><a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">YouTube Provider Privacy</a><a href="https://www.pbs.org/about/about-pbs/privacy-policy/" target="_blank" rel="noopener noreferrer">PBS Provider Privacy</a></div></nav><p class="ft-meta">© {datetime.now(timezone.utc).year} ZOTHEOS LLC<br>Film and preview rights remain with their owners.</p></div><div class="ft-block" id="theater-privacy"><p class="lbl">Theater Privacy</p><div><p>Fonts and page code load from this site. Theme, motion and effect intensity preferences stay in your browser. The Theater does not save searches or film selections. A story link carries its record ID in the URL fragment; choosing other stories does not rewrite your URL or search history.</p><p>Official thumbnails load automatically from their listed image providers. The selected YouTube, PBS, Vimeo or National Film Board player also loads automatically, ready for its Play control. These providers receive your IP address and request information when contacted; their own privacy policies apply. Eligible YouTube and Vimeo previews may start without sound when at least 60% of the screen and controls are visible, except in Still or when the device asks for reduced motion. They pause outside view or when the tab is hidden. Your Pause holds until Play. Playback uses data and sends playback reports to the provider. Previews stop after 45 seconds on desktop and 15 seconds on phones unless you deliberately take control. Sound starts only when you choose it.</p><p>YouTube uses its privacy-enhanced player domain and Vimeo requests its do-not-track mode. Neither makes playback anonymous or guarantees that a provider collects no data. Selecting another story replaces the current player and contacts that provider. This page sends play, pause, sound and caption commands to YouTube and Vimeo through their player interfaces. Caption availability is checked by the player; dated metadata is a starting point and can change. Use native National Film Board and PBS controls. Other provider controls remain available.</p><p>Source links contact their destinations when followed. Publishers can restrict or remove a title. If playback fails, use the official source. <a href="mailto:contact@zotheos.org">Report A Correction</a>.</p></div></div></div></footer>
<script>{read('tools/nations/partials/appearance.js')}</script><script>{read('static/theater/appearance.js')}</script><script>{read('static/theater/zt-frame.js')}</script><script>{read('static/theater/theater.js')}</script></body></html>
'''

def main():
    global SOURCE, CATALOGUE_ROOT
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=SOURCE)
    ap.add_argument('--source-root', type=Path, default=None)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    CATALOGUE_ROOT = args.root
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
