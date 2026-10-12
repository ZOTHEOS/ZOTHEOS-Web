"""Sourced directory names, separate from researched nation profiles."""
from collections import Counter
from datetime import date
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import nations_inventories as I


def esc(value):
    return html.escape(str(value), quote=True)


def https(value):
    try:
        p = urlsplit(value)
        if (p.scheme != 'https' or not p.hostname or p.username or p.password
                or p.port not in (None, 443) or re.search(r'[\s"<>]', value)):
            raise ValueError('Directory source must be a public HTTPS URL')
    except (TypeError, ValueError) as exc:
        raise ValueError('Directory source must be a public HTTPS URL') from exc
    return value


def source_link(value, text):
    return '<a href="' + esc(https(value)) + '" rel="noopener noreferrer" target="_blank">' + esc(text) + '<span class="sr-only"> (opens in a new tab)</span></a>'


def load(root):
    folder = Path(root) / 'data/nations/research'
    directory = json.loads((folder / 'us_federal_directory.json').read_text(encoding='utf-8'))
    sources = json.loads((folder / 'directory_sources.json').read_text(encoding='utf-8'))
    entities = directory['entities']
    if directory.get('schema_version') != 1 or sources.get('schema_version') != 1:
        raise ValueError('Unknown directory schema')
    if (not entities or len({e['directory_id'] for e in entities}) != len(entities)
            or directory['enumerated_count'] != len(entities)
            or dict(Counter(e['directory_group'] for e in entities)) != directory['group_counts']
            or set(directory['group_counts']) != {'contiguous', 'alaska'}):
        raise ValueError('Directory names, ids or group counts disagree')
    if (directory['stated_count'] != len(entities)
            and directory['count_discrepancy']['status'] != 'unresolved'):
        raise ValueError('Directory count discrepancy must remain disclosed')
    source = directory['source']
    https(source['url'])
    date.fromisoformat(source['publication_date'])
    if not re.fullmatch(r'[0-9a-f]{64}', source['sha256']):
        raise ValueError('Directory source receipt needs its SHA-256')
    for e in entities:
        if (not re.fullmatch(r'us-fed-[0-9a-f]{12}', e['directory_id'])
                or not isinstance(e['name'], str) or not e['name'].strip()
                or not isinstance(e['directory_name'], str) or not e['directory_name'].strip()
                or e['entity_type'] != 'federally_listed_tribal_entity'
                or e['countries'] != ['US'] or e['recognition_source'] != source['url']
                or e['recognition_as_of'] != source['publication_date']):
            raise ValueError('Directory record differs from its source scope')
        crosswalk = e['registry_crosswalk']
        if crosswalk['status'] not in ('unreviewed', 'confirmed', 'not_same_entity'):
            raise ValueError('Unknown directory identity review state')
        if crosswalk['status'] != 'confirmed' and crosswalk.get('registry_id'):
            raise ValueError('An unreviewed directory match cannot link a profile')
        if crosswalk['status'] == 'confirmed' and (not crosswalk.get('registry_id')
                or not crosswalk.get('reviewer') or not crosswalk.get('evidence_receipt')):
            raise ValueError('Confirmed directory match needs an identity receipt')
        if e.get('official_url'):
            https(e['official_url'])
            review = e.get('official_url_review', {})
            if review.get('status') != 'verified' or not review.get('reviewer') or not review.get('evidence_receipt'):
                raise ValueError('Directory website needs a source review receipt')
    ids = set()
    for s in sources['sources']:
        if s['source_id'] in ids or s['status'] not in ('source_retrieved', 'source_located', 'enumeration_pending'):
            raise ValueError('Duplicate source id or unknown research state')
        ids.add(s['source_id'])
        https(s['url'])
    return directory, sources


LANES = [
    ('us-fr-2026', 'United States', 'Federal list names are visible below. Independent and state-recognized communities need additional sources.'),
    ('ca-first-nation-profiles', 'Canada: First Nations', 'The dated administrative register names are listed here. Contemporary First Nation profiles still need separate identity review.'),
    ('ca-inuit-regions', 'Canada: Inuit', 'Land claim regions, communities and governments must be recorded separately.'),
    ('ca-metis-governments', 'Canada: Metis', 'Council membership is not an inventory of all Metis governments or rights-bearing communities.'),
    ('mx-inpi-catalogue', 'Mexico', 'Pueblos, communities and Afromexican communities need distinct entries.'),
    ('gt-almg', 'Guatemala', 'Maya linguistic communities, Xinka and Garifuna require distinct sources and identities.'),
    ('central-america-source-discovery', 'Other Central America', 'Country directories and Indigenous-led sources are still being identified.'),
    ('pe-bdpi', 'Peru', 'Peoples and local communities are separate inventories.'),
    ('br-ibge-census-2022', 'Brazil', 'Census self-identification categories must not be presented as governments.'),
    ('co-dane-census-2018', 'Colombia', 'Peoples, cabildos and resguardos are different units.'),
    ('ec-conaie', 'Ecuador', 'Nationalities, peoples, communities and associations keep their own identities.'),
    ('south-america-source-discovery', 'Other South America', 'More country and Indigenous-led directories are still needed.'),
    ('africa-ipacc', 'Africa', 'Representative organizations are starting points, not a complete inventory of Indigenous peoples.'),
    ('asia-source-discovery', 'Asia', 'Coverage must be researched country by country with Indigenous-led sources.'),
    ('arctic-icc', 'Circumpolar Inuit', 'Representative bodies are distinct from peoples, communities and governments.'),
    ('europe-source-discovery', 'Arctic And Europe', 'Sami and other peoples need their own sources and correctly identified governing bodies.'),
    ('oceania-source-discovery', 'Oceania', 'Peoples, iwi, hapu and communities need their own sources and names.')]


def inventories(root):
    return I.documents(root)


def work_lanes(sources, listed=()):
    by_id = {s['source_id']: s for s in sources['sources']}
    out = ['<section class="src-g" id="worldwide" aria-labelledby="worldwide-title"><h2 id="worldwide-title">The work beyond this directory</h2>',
           '<p>The researched profiles already span multiple regions. This source map shows where the next inventories must come from. Finding a source does not mean its names have been added or its claims checked. No worldwide completion percentage is claimed.</p><ul class="src-u">']
    for key, label, note in LANES:
        source = by_id[key]
        state = ('Names listed below; profiles incomplete' if key in {'us-fr-2026', *listed} else
                 'Source located; inventory pending' if source['status'] != 'enumeration_pending' else 'Further sources needed')
        out.append('<li><h3>' + esc(label) + '</h3><p>' + esc(state) + '. ' + esc(note) + '</p><p>'
                   + source_link(source['url'], 'Open the source') + '</p></li>')
    out.append('</ul></section>')
    return '\n'.join(out)


def load_canada(root):
    path = Path(root) / 'data/nations/research/ca_registry_groups_2024.json'
    doc = json.loads(path.read_text(encoding='utf-8'))
    entries, source = doc['entities'], doc['source']
    if (doc.get('schema_version') != 1 or doc['entity_unit'] != 'indian_register_group'
            or doc['enumerated_count'] != len(entries) or doc['stated_count'] != len(entries)
            or len({e['registry_group_code'] for e in entries}) != len(entries)):
        raise ValueError('Canada administrative group counts or codes disagree')
    https(source['url'])
    date.fromisoformat(source['as_of'])
    if not re.fullmatch(r'[0-9a-f]{64}', source['sha256']):
        raise ValueError('Canada source receipt needs its SHA-256')
    for e in entries:
        if (not re.fullmatch(r'[0-9]{3}', e['registry_group_code'])
                or e['directory_id'] != 'ca-register-' + e['registry_group_code']
                or not isinstance(e['name'], str) or not e['name'].strip()
                or not isinstance(e['directory_name'], str) or not e['directory_name'].strip()
                or e['name'].lower().startswith('general list')
                or e['entity_type'] != 'indian_register_group' or e['countries'] != ['CA']
                or e['as_of'] != source['as_of']):
            raise ValueError('Canada record differs from its administrative source scope')
        c = e['registry_crosswalk']
        if c['status'] not in ('unreviewed', 'confirmed', 'not_same_entity'):
            raise ValueError('Unknown Canada identity review state')
        if c['status'] != 'confirmed' and c.get('registry_id'):
            raise ValueError('An unreviewed Canada match cannot link a profile')
        if c['status'] == 'confirmed' and (not c.get('registry_id') or not c.get('reviewer') or not c.get('evidence_receipt')):
            raise ValueError('Confirmed Canada match needs an identity receipt')
        if e.get('official_url'):
            https(e['official_url'])
            review = e.get('official_url_review', {})
            if review.get('status') != 'verified' or not review.get('reviewer') or not review.get('evidence_receipt'):
                raise ValueError('Canada website needs a source review receipt')
    return doc


def entry(builder, e):
    face = 'brand' if builder.brand.serif_ok(e['name']) else 'names'
    out = ['<li id="' + esc(e['directory_id']) + '" data-directory-name="' + esc(e['directory_name']) + '">'
           '<h4 class="nm directory-name" dir="auto" data-face="' + face + '">' + esc(e['name']) + '</h4>']
    if e['directory_name'] != e['name']:
        out.append('<p class="note" dir="auto">Published name record: ' + esc(e['directory_name']) + '</p>')
    c = e['registry_crosswalk']
    if c['status'] == 'confirmed' and c['registry_id'] in builder.m.by_id:
        out.append('<p><a href="/nations/' + esc(c['registry_id']) + '">Read the researched profile</a></p>')
    else:
        out.append('<p class="rc">Directory name. A corresponding researched profile has not been confirmed here.</p>')
    if e.get('official_url'):
        out.append('<p>' + source_link(e['official_url'], 'Visit the verified official website') + '</p>')
    out.append('</li>')
    return '\n'.join(out)


def visible_entries(builder, entities):
    known = {n['id'] for n in builder.m.raw['nations']}
    held = {e['nation'] for key in ('hide_nation', 'takedown') for e in builder.m.overrides.get(key, [])}
    for e in entities:
        c = e['registry_crosswalk']
        if c['status'] == 'confirmed' and c['registry_id'] not in known:
            raise ValueError('Confirmed directory match refers to an unknown profile')
    directory_holds = I.directory_holds(getattr(builder, 'root', builder.m.root))
    return [e for e in entities if e['registry_crosswalk'].get('registry_id') not in held
            and e['directory_id'] not in directory_holds]


def page(builder):
    directory, sources = load(builder.root)
    canada = load_canada(builder.root)
    source = directory['source']
    extra = inventories(builder.root)
    # Confirmed links honor canonical publication holds. Unreviewed candidates never create a public link.
    entities = visible_entries(builder, directory['entities'])
    ca_entries = visible_entries(builder, canada['entities'])
    extra_entries = [(doc, visible_entries(builder, doc['entities'])) for doc in extra]
    total = len(entities) + len(ca_entries) + sum(len(entries) for _, entries in extra_entries)
    list_count = 2 + len(extra)
    jumps = [('<a href="#us-directory">United States: federal list</a>'), ('<a href="#canada-directory">Canada: 2024 register groups</a>')]
    jumps += ['<a href="#' + esc(doc['_display']['anchor']) + '">' + esc(doc['_display']['title']) + '</a>' for doc in extra]
    navigation = '<nav aria-label="Directory inventories"><ul class="src-u">' + ''.join('<li>' + link + '</li>' for link in jumps) + '</ul></nav>'
    out = ['<div class="read n-head prose">', '<p class="eyebrow">Directory</p>',
           '<h1 class="page-h">Names deserve visibility.</h1>',
           '<p class="lede">A growing worldwide collection, with separately sourced name directories. Each inventory keeps its own category, source and date.</p>',
           '<p>We have ' + str(len(builder.m.nations)) + ' researched profiles of peoples, communities and governing bodies. '
           'The directory below is a separate list of ' + str(len(entities)) + ' published federal name records. '
           'Canada\'s dated administrative register groups and additional source inventories are listed separately. A directory entry is not a researched profile, '
           'and these different lists cannot be added together as a count of Indigenous nations.</p>',
           '<p>' + esc(directory['scope_note']) + '</p>',
           '<p class="note">' + esc(directory['count_discrepancy']['note']) + '</p>',
           '<p class="rc">' + source_link(source['url'], source['publisher'] + ': ' + source['title'])
           + '. Published <time datetime="' + esc(source['publication_date']) + '">' + esc(source['publication_date']) + '</time>.</p>',
           '<p>Names are reproduced from that dated source, including its historical naming notes. A name or past listing does not establish a present land boundary, treaty right or exclusive community representation.</p>',
           '<p><a href="/nations#find">Search the researched profiles</a> &middot; <a href="/nations/resources">Histories And Rights Resources</a> &middot; <a href="#worldwide">See worldwide work still to do</a></p>',
           navigation,
           '<div class="directory-search"><label for="directoryQuery">Find a name in this directory</label>',
           '<div class="directory-inputs"><input id="directoryQuery" type="search" autocomplete="off" placeholder="Try Ute, Apache or a community name" aria-controls="directoryNames" aria-describedby="directoryResult">',
           '<button type="button" id="directoryClear" class="pill">Clear</button></div>',
           '<p id="directoryResult" class="note" role="status" aria-live="polite">' + str(total) + ' directory records in ' + str(list_count) + ' differently scoped lists. All are shown.</p></div>',
           '<noscript><p>All names remain visible without JavaScript. Use your browser\'s Find command to search.</p></noscript>',
           '<div id="directoryNames"><section class="directory-group" id="us-directory" aria-labelledby="us-directory-title"><h2 id="us-directory-title">United States: the published federal list</h2>']
    for key, label in [('contiguous', 'Contiguous United States'), ('alaska', 'Alaska')]:
        group = sorted((e for e in entities if e['directory_group'] == key), key=lambda e: (e['name'].casefold(), e['directory_id']))
        out.append('<section class="src-g directory-group" aria-labelledby="directory-' + key + '"><h3 id="directory-' + key + '">' + label
                   + '</h3><p class="note">' + str(len(group)) + ' published name records</p><ul class="directory-list">')
        for e in group:
            out.append(entry(builder, e))
        out.append('</ul></section>')
    cs = canada['source']
    out += ['</section>', '<section class="src-g directory-group" id="canada-directory" aria-labelledby="canada-directory-title">'
            '<h2 id="canada-directory-title">Canada: named administrative register groups</h2>',
            '<p>' + str(len(ca_entries)) + ' named registry groups, as of December 31, 2024. These are administrative '
            'records, not a count of current governments or all Indigenous peoples. The report distinguishes 619 bands from 634 registry groups.</p>',
            '<p>' + esc(canada['scope_note']) + '</p>',
            '<p class="rc">' + source_link(cs['url'], cs['publisher'] + ': ' + cs['title']) + '. Snapshot <time datetime="'
            + esc(cs['as_of']) + '">' + esc(cs['as_of']) + '</time>.</p>',
            '<p class="note">' + esc(canada['extraction_note']) + ' Contemporary names and identity links still need '
            'review against each community\'s own sources.</p><ul class="directory-list">']
    out += [entry(builder, e) for e in sorted(ca_entries, key=lambda e: (e['name'].casefold(), e['directory_id']))]
    out += ['</ul></section>']
    for doc, entries in extra_entries:
        display, source = doc['_display'], doc['source']
        out += ['<section class="src-g directory-group" id="' + esc(display['anchor']) + '" aria-labelledby="' + esc(display['anchor']) + '-title">',
                '<h2 id="' + esc(display['anchor']) + '-title">' + esc(display['title']) + '</h2>',
                '<p>' + str(len(entries)) + ' source records. ' + esc(doc['scope_note']) + '</p>',
                '<p class="rc">' + esc(display['label']) + '; source snapshot ' + esc(doc['as_of']) + '. '
                + source_link(source['url'], source['publisher'] + ': ' + source.get('display_title', source['title'])) + '. Read '
                + esc(source['retrieved_at'][:10]) + '.</p>',
                '<p class="note">' + esc(doc.get('public_extraction_note', doc['extraction_note'])) + '</p>']
        if doc.get('count_discrepancy', {}).get('status') == 'unresolved':
            out.append('<p class="note">Unresolved source-count difference: ' + esc(doc['count_discrepancy']['note']) + '</p>')
        if doc.get('public_notes'):
            out += ['<p class="note">' + esc(note) + '</p>' for note in doc['public_notes']]
        if doc.get('edition_note'):
            out.append('<p class="note">' + esc(doc['edition_note']) + '</p>')
        out.append('<ul class="directory-list">')
        out += [entry(builder, e) for e in sorted(entries, key=lambda e: (e['name'].casefold(), e['directory_id']))]
        out.append('</ul></section>')
    out += ['</div>', work_lanes(sources, [doc['_display']['source_id'] for doc in extra]),
            '<section class="src-g"><h2>More than a government list</h2><p>Independent communities and peoples outside state recognition must also be visible. Their own names and sources belong in this collection. We do not merge communities because their names sound similar.</p>',
            '<p><a href="/nations/for-nations">Send a correction, addition or removal request</a>. Land and rights resources link to nations and Indigenous-led organizations directly; this site does not speak on their behalf.</p></section>', '</div>']
    return builder.sp('directory', '\n'.join(out), 'Search separately typed Indigenous name inventories with their sources, dates and unresolved coverage gaps.')


def coverage(builder):
    directory, _ = load(builder.root)
    canada = load_canada(builder.root)
    focus = ['southern-ute-indian-tribe-us-co', 'ute-mountain-ute-tribe-us-co-ut-nm', 'ute-indian-tribe-uintah-ouray-us-ut',
             'fort-sill-apache-us-ok-nm', 'tonto-apache-tribe-us-az', 'lipan-apache-tribe-us-tx', 'chiricahua-apache-nation-us-nm']
    extra = inventories(builder.root)
    progress = ''.join('<p>' + esc(doc['_display']['title']) + ': ' + str(doc['enumerated_count'])
                       + ' source records; snapshot ' + esc(doc['as_of']) + '. ' + esc(doc['scope_note'])
                       + ((' Unresolved source-count difference: ' + esc(doc['count_discrepancy']['note']))
                          if doc.get('count_discrepancy', {}).get('status') == 'unresolved' else '')
                       + '</p>' for doc in extra)
    links = ['<a href="/nations/' + esc(nid) + '">' + esc(builder.m.by_id[nid]['name']) + '</a>' for nid in focus if nid in builder.m.by_id]
    return ('<section class="src-g"><h2>Names missing from profiles should still be visible</h2><p>The '
            '<a href="/nations/directory">new directory</a> preserves ' + str(directory['enumerated_count'])
            + ' published US federal name records, while the source states ' + str(directory['stated_count'])
            + '. That discrepancy remains unresolved. Directory names are separate from the researched profiles counted below.</p>'
            '<p>Canada\'s separate inventory lists ' + str(canada['enumerated_count']) + ' named administrative registry groups '
            'as of December 31, 2024, not that many current governments.</p>'
            + progress
            + ('<p>New researched pages: ' + ', '.join(links) + '. Distinct communities and governments keep separate records.</p>' if links else '')
            +
            '<p><a href="/nations/directory#worldwide">See the worldwide source map and inventories still to research</a>. '
            'No count here defines who is Indigenous, and no worldwide completeness is claimed.</p></section>')
