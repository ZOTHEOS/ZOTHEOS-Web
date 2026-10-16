#!/usr/bin/env python3
"""Validate the cited catalogue and deterministically render the static Theater.

No metadata or video is fetched at build time. --check writes nothing.
--root isolates catalogue input and output; shared templates come from this tool's repository.
"""
import argparse
from datetime import date, datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

SOURCE = Path(__file__).resolve().parents[1]
KINDS = {'excerpt':'Official Excerpt', 'trailer':'Official Trailer', 'full-film':'Full Film',
         'official-page':'Official Page', 'short':'Short Film'}
POLICY = "default-src 'none'; base-uri 'none'; object-src 'none'; script-src 'none'; script-src-attr 'none'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; media-src 'none'; connect-src 'none'; form-action 'none'; frame-src https://www.youtube-nocookie.com https://player.pbs.org; worker-src 'none'; frame-ancestors 'none'"


def text(value, name, limit=1000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(name + ': a bounded, nonempty string is required')
    if any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise ValueError(name + ': control characters are forbidden')
    return value


def url(value):
    text(value, 'source URL', 2000)
    p = urlsplit(value)
    port = p.port  # Evaluating the property also rejects nonnumeric/out-of-range ports.
    if port == 0 or p.netloc.endswith(':'):
        raise ValueError('Invalid HTTPS port')
    if p.scheme != 'https' or not p.hostname or p.username or p.password or '\\' in value or any(c.isspace() for c in value):
        raise ValueError('Only absolute HTTPS publisher URLs without credentials are allowed')
    return value


def checked(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('Source check requires an ISO calendar date')
    if date.fromisoformat(value) > datetime.now(timezone.utc).date():
        raise ValueError('A source check cannot be in the future')


def validate(data):
    if data.get('version') != 1: raise ValueError('Unsupported catalogue version')
    checked(data['updated'])
    films, topics = data['films'], data['topics']
    if not isinstance(films, list) or not 1 <= len(films) <= 150: raise ValueError('Catalogue size is outside the reviewed bound')
    topic_ids, film_ids = set(), set()
    for topic in topics:
        ident = topic['id']
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,79}', ident) or ident in topic_ids: raise ValueError('Invalid or duplicate topic')
        topic_ids.add(ident); text(topic['name'], 'topic name', 100)
    for film in films:
        ident = film['id']
        if not re.fullmatch(r'[a-z][a-z0-9-]{0,99}', ident) or ident in film_ids: raise ValueError('Invalid or duplicate film ID')
        film_ids.add(ident)
        for key, limit in [('title',180),('credits',500),('publisher',200),('synopsis',220),('availability',650),('content_note',400)]:
            text(film[key], key, limit)
        if film['viewing'] not in KINDS: raise ValueError('Unknown viewing scope')
        if not film['topics'] or not set(film['topics']) <= topic_ids: raise ValueError('Unknown topic in film')
        url(film['watch_url'])
        year = film.get('year')
        if year is not None and (type(year) is not int or not 1880 <= year <= datetime.now(timezone.utc).year): raise ValueError('Invalid film year')
        if film.get('runtime') is not None: text(film['runtime'], 'runtime', 100)
        yt, pbs = film.get('youtube_id'), film.get('pbs_id')
        if yt and pbs: raise ValueError('Only one player provider per selection')
        if yt is not None and not re.fullmatch(r'[A-Za-z0-9_-]{11}', yt): raise ValueError('Invalid YouTube ID')
        if pbs is not None and not re.fullmatch(r'\d{10}', pbs): raise ValueError('Invalid PBS ID')
        if not film['sources']: raise ValueError('Every title requires a source')
        for source in film['sources']:
            url(source['url']); checked(source['checked'])
            text(source['title'], 'source title', 250); text(source['publisher'], 'source publisher', 200)
    for resource in data.get('resources', []):
        url(resource['url']); checked(resource['checked'])
        text(resource['title'], 'resource title', 180); text(resource['text'], 'resource text', 650)
        text(resource['publisher'], 'resource publisher', 200)
    if data['featured'] not in film_ids: raise ValueError('Featured film is missing')
    return data


def read(rel):
    return (SOURCE / rel).read_text(encoding='utf-8')


def render(data):
    from csp_sync import page_hashes, fix_policy, meta_policy
    e = lambda value: escape(str(value), quote=True)
    topics = {t['id']:t['name'] for t in data['topics']}
    cards = []
    for i, film in enumerate(data['films'], 1):
        provider = 'youtube' if film.get('youtube_id') else 'pbs' if film.get('pbs_id') else ''
        attrs = {'theater-film':film['id'], 'featured':str(film['id']==data['featured']).lower(),
            'title':film['title'], 'search':' '.join([film['title'],film['synopsis'],film['credits'],*[topics[t] for t in film['topics']]]),
            'topic':' '.join(film['topics']), 'provider':provider, 'video-id':film.get('youtube_id') or film.get('pbs_id') or '',
            'watch-url':film['watch_url'], 'kind':KINDS[film['viewing']], 'availability':film['availability'],
            'summary':film['synopsis'], 'content-note':film['content_note'], 'credits':film['credits']}
        at = ' '.join('data-'+k+'="'+e(v)+'"' for k,v in attrs.items())
        art = 'memory' if 'family' in film['topics'] else 'language' if 'language' in film['topics'] else 'earth' if 'environment' in film['topics'] else 'river'
        facts = [KINDS[film['viewing']]]
        if film.get('year'): facts.append(str(film['year']) + (' premiere' if 'premiere' in film.get('year_scope','').lower() else ''))
        if film.get('runtime'): facts.append(film['runtime'])
        source_html = ''.join('<li><a href="'+e(s['url'])+'" target="_blank" rel="noopener noreferrer">'+e(s['title'])+'</a><span> '+e(s['publisher'])+' · Checked <time datetime="'+s['checked']+'">'+s['checked']+'</time></span></li>' for s in film['sources'])
        card = f'''<article class="th-film" id="film-{e(film['id'])}" {at}>
          <div class="th-art th-art--{art} th-cover" aria-hidden="true"><span class="th-cover-number">{i:02d}</span><span class="th-cover-title">{e(film['title'])}</span><span class="th-cover-scope">{e(KINDS[film['viewing']])}</span></div>
          <div class="th-film-body"><p class="th-film-meta">{e(' · '.join(facts))}</p><h3 class="th-film-title">{e(film['title'])}</h3>
          <p class="th-description">{e(film['synopsis'])}</p><p class="th-film-credits">{e(film['credits'])}</p>
          <p class="th-film-access">{e(film['availability'])}</p><p class="th-content-note"><strong>Before Watching:</strong> {e(film['content_note'])}</p>
          <div class="th-actions"><a class="th-watch" href="{e(film['watch_url'])}" target="_blank" rel="noopener noreferrer">Open Official Source <span aria-hidden="true">↗</span></a><button type="button" class="th-select" data-theater-select="{e(film['id'])}" aria-label="View {e(film['title'])} In Theater" hidden>View In Theater</button></div>
          <details class="th-sources"><summary>Sources And Viewing Notes</summary><ul>{source_html}</ul></details></div></article>'''
        cards.append(card)
    companions = ''.join('<article><h3>'+e(r['title'])+'</h3><p>'+e(r['text'])+'</p><a class="th-watch" href="'+e(r['url'])+'" target="_blank" rel="noopener noreferrer">Read The Official Resource ↗</a><p class="th-art-credit">'+e(r['publisher'])+' · Checked <time datetime="'+r['checked']+'">'+r['checked']+'</time></p></article>' for r in data.get('resources', []))
    companion_section = '<section class="th-companions" aria-labelledby="companion-heading"><div class="th-section-heading"><h2 id="companion-heading" class="th-section-title">Beyond The Screen</h2><p class="th-kicker">Research · Restoration · Education</p></div><div class="th-companion-grid">'+companions+'</div></section>' if companions else ''
    feature = next(f for f in data['films'] if f['id']==data['featured'])
    nav = '<a class="nh-link" href="#collection">Collection</a><a class="nh-link" href="/nations/directory">Nations</a>'
    sheet = ''.join('<li><a href="'+href+'">'+label+'</a></li>' for label,href in [('The Screening Room','#screening'),('The Collection','#collection'),('How We Curate','#curation'),('Nations Directory','/nations/directory'),('Mission','/#mission')])
    header = read('tools/nations/partials/header.html').replace('{{{nav_links}}}',nav).replace('{{{sheet_links}}}',sheet).replace('aria-label="Nations"','aria-label="Theater"').replace('Indigenous nations today','ZOTHEOS Theater')
    options = ''.join('<option value="'+e(k)+'">'+e(v)+'</option>' for k,v in topics.items())
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover"><meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="POLICY_PLACEHOLDER"><title>ZOTHEOS Theater | Stories That Deserve An Audience</title>
<meta name="description" content="Documentaries and recorded conversations on Indigenous histories, sovereignty and renewal. Official sources, clear viewing notes and players you choose to load.">
<link rel="canonical" href="https://zotheos.org/theater"><meta property="og:title" content="ZOTHEOS Theater"><meta property="og:type" content="website"><meta property="og:url" content="https://zotheos.org/theater"><meta name="theme-color" content="#000000" id="themeColorMeta"><link rel="icon" href="/zotheos_icon.ico?v=3">
<script>{read('tools/nations/partials/bootstrap.js')}</script><style id="zth-fonts">{read('tools/nations/partials/fonts-brand.css')}</style>{read('tools/nations/partials/fonts-names.css')}
<link rel="preload" as="font" type="font/woff2" href="/static/fonts/instrument-serif-latin.woff2" crossorigin><link rel="stylesheet" href="/static/theater/theater.css"></head>
<body>{header}<main id="main" class="th-page">
<section class="th-hero" aria-labelledby="theater-heading"><p class="th-kicker">ZOTHEOS Theater · Indigenous Voices First</p><div class="th-hero-copy"><h1 id="theater-heading" class="th-title">Truth Deserves<br><em>An Audience.</em></h1><div class="th-lede"><p>History that must be faced. Life that continues. Futures shaped by the people living them.</p><p>Documentaries, short films and recorded conversations, beginning with Native Nations and Indigenous peoples. Choose a story. Stay with its people. Follow the sources.</p><a class="th-watch" href="#collection">Explore The Collection <span aria-hidden="true">↓</span></a></div></div></section>
<section class="th-feature" id="screening" aria-labelledby="screening-heading"><div class="th-section-heading"><h2 id="screening-heading" class="th-section-title">The Screening Room</h2><p class="th-kicker">Recorded Stories · Watch At Your Pace</p></div>
<div class="th-screen th-art th-art--memory"><div class="th-screen-intro"><span class="th-play" aria-hidden="true"></span><p>Make Room For The Story.</p><span>No video loads until you choose.</span></div><div id="theaterPlayer" class="th-player" hidden></div></div>
<div class="th-player-controls"><button id="theaterLoad" type="button" aria-describedby="theaterTitle theaterConsent" class="th-watch" hidden>Load PBS Player</button><button id="theaterClose" type="button" class="th-select" hidden>Close Player</button><p id="theaterPlayerStatus" role="status">The official source below is available without an embedded player.</p></div>
<p id="theaterConsent" class="th-consent">Loading a player connects your browser to YouTube or PBS. The selected provider receives your IP address and request information; its privacy policies and controls apply. Close Player removes the player. You can always use the official source instead.</p>
<div class="th-feature-caption"><div><p class="th-film-meta" id="theaterKind">{e(KINDS[feature['viewing']])}</p><h3 id="theaterTitle" class="th-feature-title" tabindex="-1">{e(feature['title'])}</h3><p class="th-film-credits" id="theaterCredits">{e(feature['credits'])}</p></div><div><p id="theaterDescription" class="th-description">{e(feature['synopsis'])}</p><p id="theaterAvailability" class="th-film-access">{e(feature['availability'])}</p><p id="theaterContentNote" class="th-content-note">{e(feature['content_note'])}</p><a class="th-watch" id="theaterWatch" href="{e(feature['watch_url'])}" target="_blank" rel="noopener noreferrer">Open Official Source <span aria-hidden="true">↗</span></a></div></div>
<aside class="th-context"><h3>History In Context</h3><p>The collection includes the official <em>Daughter of a Lost Bird</em> excerpt on Indigenous adoption. It examines the Indian Adoption Project through historical narration and testimony.</p><p>The child-removal percentage heard in the archival testimony describes historical research before the Indian Child Welfare Act. It is not a present-day removal rate. <a href="https://www.nicwa.org/what-is-icwa/" target="_blank" rel="noopener noreferrer">Read NICWA’s historical context</a>.</p></aside>
<p class="th-art-credit">Original ZOTHEOS abstract title artwork. These are not film stills, official posters or depictions of ceremonies.</p></section>
<section id="collection" class="th-catalogue" aria-labelledby="collection-heading"><div class="th-section-heading"><h2 id="collection-heading" class="th-section-title">Stories To Stay With</h2><p class="th-kicker">A Growing, Cited Collection</p></div><p class="th-collection-intro">Face what happened. Listen to what people are protecting. Look for the work of renewal. These stories are distinct; no film stands for every Nation.</p>
<div id="theaterTools" class="th-tools" hidden><div><label for="theaterSearch">Search Titles, People And Subjects</label><input id="theaterSearch" type="search" placeholder="Try land, language or family" autocomplete="off"></div><div><label for="theaterTopic">Explore A Subject</label><select id="theaterTopic"><option value="all">All Subjects</option>{options}</select></div><button id="theaterClear" class="th-select" type="button">Clear Filters</button><p id="theaterStatus" role="status"></p></div>
<div id="theaterEmpty" class="th-empty" hidden><h3>No Matching Stories</h3><p>Try a broader search or choose Clear Filters above to see the whole collection.</p></div><div class="th-film-grid">{''.join(cards)}</div></section>
{companion_section}<section id="curation" class="th-method" aria-labelledby="curation-heading"><div><p class="th-kicker">How We Curate</p><h2 id="curation-heading" class="th-section-title">Attention With<br>Responsibility.</h2></div><div><p>We read official filmmaker, publisher and community sources before adding a title. Credits, source-check dates and viewing limits stay beside it. Inclusion is not an endorsement by a Nation, an independent verification of every statement in a film or a claim that the full film has been watched for this collection.</p><p>Trailers and excerpts are labeled. Official pages may require payment, a library account or access in a particular country. Availability can change. Full films remain with their authorized providers; ZOTHEOS does not copy or host them.</p><p>Difficult histories belong beside living cultures, relationships, resistance and community-led restoration. This starter collection is incomplete. Sources and corrections guide its growth.</p><a class="th-watch" href="/nations/resources">Continue With Histories And Resources <span aria-hidden="true">↗</span></a></div></section>
</main><footer class="ft"><div class="ft-in"><div class="ft-top"><div><a class="ft-brand" href="/" aria-label="ZOTHEOS home"><img src="/static/zotheos_logo.png" width="133" height="28" alt=""></a><p class="ft-tag">Truth. Dignity. Sovereignty.</p><p class="ft-founder">Founded by <strong>David Garcia</strong><br>ZOTHEOS LLC</p></div><nav class="ft-links" aria-label="Footer"><div class="ft-col"><span class="ft-col-l">Explore</span><a href="/">Home</a><a href="/#mission">Mission</a><a href="/theater" aria-current="page">Theater</a><a href="/nations">Indigenous Nations Today</a><a href="/nations/directory">Nations Directory</a><a href="/nations/resources">Histories And Resources</a><a href="/game">Play And Learn</a></div><div class="ft-col"><span class="ft-col-l">Your Choice</span><a href="#theater-privacy">Theater Privacy</a><a href="/#site-privacy">Website Privacy</a><a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">YouTube Provider Privacy</a><a href="https://www.pbs.org/about/about-pbs/privacy-policy/" target="_blank" rel="noopener noreferrer">PBS Provider Privacy</a></div></nav><p class="ft-meta">© {datetime.now(timezone.utc).year} ZOTHEOS LLC<br>Film rights remain with their owners.</p></div><div class="ft-block" id="theater-privacy"><p class="lbl">Theater Privacy</p><div><p>The page loads its artwork, fonts and code from this site. Theme and motion preferences stay in your browser. Search and film selection are not saved by the Theater.</p><p>A video provider is contacted only after you press Load Player for a selected title. Loading shares connection and request information with that provider. YouTube uses its privacy-enhanced embed domain; this does not make playback anonymous or eliminate provider data collection. PBS uses its own player. No player is loaded automatically and no autoplay permission is granted.</p><p>External source and provider-policy links contact their destinations when followed. A publisher can restrict or remove a video. If a player does not work, use its official source. <a href="mailto:contact@zotheos.org">Report A Correction</a>.</p></div></div></div></footer>
<script>{read('tools/nations/partials/appearance.js')}</script><script>{read('static/theater/theater.js')}</script></body></html>
'''


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=SOURCE); ap.add_argument('--check',action='store_true')
    args=ap.parse_args()
    try:
        data=validate(json.loads((args.root/'data/theater/films.json').read_text(encoding='utf-8')))
        body=render(data)
        from csp_sync import page_hashes,fix_policy,meta_policy
        body=body.replace('POLICY_PLACEHOLDER',meta_policy(fix_policy(POLICY,page_hashes(body))))
        output=args.root/'theater.html'
        if args.check:
            if not output.is_file() or output.read_text(encoding='utf-8')!=body:
                raise ValueError('Theater output is stale; run tools/theater_build.py')
        else: output.write_text(body,encoding='utf-8',newline='\n')
        print(f"Theater: {len(data['films'])} cited titles; " + ('output current' if args.check else 'rendered'))
    except (ValueError,KeyError,TypeError,OSError) as exc:
        print('Theater: '+str(exc),file=sys.stderr); return 1
    return 0


if __name__=='__main__': sys.exit(main())
