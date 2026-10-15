"""Sourced directory names, separate from researched nation profiles."""
from collections import Counter
from datetime import date, datetime, timezone
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import nations_inventories as I


def esc(value):
    return html.escape(str(value), quote=True)


def display_date(value):
    if re.fullmatch(r'\d{4}', value):
        return value
    parsed = date.fromisoformat(value)
    months = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
    return str(parsed.day) + ' ' + months[parsed.month - 1] + ' ' + str(parsed.year)


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
    ('us-fr-2026', 'United States', 'The federal source names are preserved in this directory. Independent and state-recognized communities need additional sources.'),
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
        state = ('Source inventory preserved; researched profiles incomplete' if key in {'us-fr-2026', *listed} else
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
        out.append('<p class="rc directory-state">Profile Link Pending</p>')
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


def us_gaps(builder, extra):
    path = Path(builder.root) / 'data/nations/research/us_coverage_plan.json'
    if not path.exists():
        if any(doc['entity_unit'] == 'state_tribal_directory_listing' for doc in extra):
            raise ValueError('State directories require their explicit incomplete US inclusion plan')
        return ''
    plan = json.loads(path.read_text(encoding='utf-8'))
    states = plan.get('state_scopes', [])
    expected = set('AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split())
    if (plan.get('schema_version') != 1 or {row.get('state') for row in states} != expected
            or len(states) != 50 or plan.get('complete') is not False):
        raise ValueError('US inclusion plan must preserve all state scopes and its incomplete status')
    docs = {doc.get('state'): doc for doc in extra if doc['entity_unit'] == 'state_tribal_directory_listing'}
    preserved, pending = [], []
    for row in states:
        if row['status'] == 'source_inventory_preserved':
            doc = docs.get(row['state'])
            if not doc or row.get('inventory_file') != ('us_' + row['state'].lower() + '_state_directory_2026.json'):
                raise ValueError('US state scope cannot claim an inventory without its typed source')
            preserved.append(row['name'])
        elif row['status'] == 'source_discovery_pending':
            pending.append(row['name'])
        else:
            raise ValueError('Unknown US inclusion work state')
    lanes = plan.get('additional_lanes', [])
    if (len(lanes) != 4 or {row.get('id') for row in lanes} != {'outside-recognition', 'native-hawaiian', 'alaska-communities', 'borders-and-territories'}
            or any(row.get('status') != 'pending' for row in lanes)):
        raise ValueError('US inclusion lanes cannot be silently declared complete')
    out = ['<section class="src-g directory-gap" id="us-inclusion" aria-labelledby="us-inclusion-title">',
           '<p class="eyebrow">United States inclusion</p><h2 id="us-inclusion-title">Every nation belongs. Coverage is still growing.</h2>',
           '<p>Federal recognition is not a definition of Indigenous identity. The federal name list is one source. '
           'Separate state directories and nations outside recognition need their own records, sources and identity review.</p>',
           '<p>State-level source inventories preserved here: ' + esc(', '.join(preserved)) + '. '
           + str(len(pending)) + ' other state source-discovery scopes remain pending. '
           'This measures research work on state directories, not how many nations exist or a percentage of US coverage.</p>',
           '<details class="directory-source"><summary>See the remaining inclusion work</summary>',
           '<p>State-level source discovery still pending: ' + esc(', '.join(pending)) + '.</p>',
           '<ul>' + ''.join('<li><strong>' + esc(row['title']) + '.</strong> ' + esc(row['note']) + '</li>' for row in lanes) + '</ul>',
           '<p>State and country labels organize research. They do not draw homelands, establish ownership or confine a people to one jurisdiction. '
           'Names appearing in several inventories remain separate source records until an explicit identity review links them.</p></details>',
           '<p><a href="/nations/for-nations">Request an addition, correction or removal</a> &middot; '
           '<a href="/nations/in/us">Read the US-associated profiles</a></p></section>']
    return '\n'.join(out)


def page(builder):
    directory, sources = load(builder.root)
    canada = load_canada(builder.root)
    source = directory['source']
    extra = inventories(builder.root)
    entities = visible_entries(builder, directory['entities'])
    ca_entries = visible_entries(builder, canada['entities'])
    extra_entries = [(doc, visible_entries(builder, doc['entities'])) for doc in extra]
    us_extra = [(doc, rows) for doc, rows in extra_entries if doc['entity_unit'] == 'state_tribal_directory_listing']
    other_extra = [(doc, rows) for doc, rows in extra_entries if doc['entity_unit'] != 'state_tribal_directory_listing']
    total = len(entities) + len(ca_entries) + sum(len(rows) for _, rows in extra_entries)
    choices = [('us-directory', 'United States', 'Federal published names', str(len(entities)), display_date(source['publication_date']))]
    choices += [(d['_display']['anchor'], d['_display']['title'],
                 d['_display']['label'], str(len(rows)), display_date(d['as_of']) + ' UTC observation') for d, rows in us_extra]
    choices += [('canada-directory', 'Canada', '2024 administrative register groups', str(len(ca_entries)), display_date(canada['source']['as_of']))]
    choices += [(d['_display']['anchor'], d['_display']['title'], d['_display']['label'], str(len(rows)), display_date(d['as_of'])) for d, rows in other_extra]
    navigation = '<nav class="directory-inventory-nav" aria-label="Directory inventories"><ul>' + ''.join(
        '<li><a href="#' + esc(key) + '"><span class="directory-inventory-title">' + esc(title) + '</span>'
        '<span class="directory-inventory-meta">' + count + ' records &middot; ' + esc(label) + '<br>Snapshot ' + esc(snapshot) + '</span></a></li>'
        for key, title, label, count, snapshot in choices) + '</ul></nav>'
    out = ['<div class="read n-head prose directory-page">', '<p class="eyebrow">Names And Sources</p>',
           '<h1 class="page-h">Names deserve visibility.</h1>',
           '<p class="lede">Start with a name. Follow its source. See what still needs research.</p>',
           '<div class="directory-search" id="directoryTools" hidden><h2>Find A Name</h2><p class="note">Search the preserved source records, or choose one inventory. A missing result does not mean a nation does not exist.</p>',
           '<label for="directoryQuery">Find a name in this directory</label>',
           '<div class="directory-inputs"><input id="directoryQuery" type="search" autocomplete="off" placeholder="Try Ute, Apache or a community name" aria-controls="directoryNames" aria-describedby="directoryResult">',
           '<button type="button" id="directoryClear" class="pill">Clear</button></div>',
           '<div class="directory-filter"><label for="directoryInventory">Source inventory</label>',
           '<select id="directoryInventory" aria-controls="directoryNames"><option value="all">All source inventories</option>'
           + ''.join('<option value="' + esc(key) + '">' + esc(title + ': ' + label) + '</option>' for key, title, label, _, _ in choices) + '</select></div>',
           '<p id="directoryResult" class="note" role="status" aria-live="polite">' + str(total) + ' directory records in ' + str(len(choices)) + ' differently scoped lists. All are shown.</p>',
           '<p id="directoryLimit" class="note"></p></div>',
           '<noscript><p>All names remain visible without JavaScript. Use your browser Find command or the source inventory links to browse.</p></noscript>',
           '<details class="directory-source"><summary>Understand These Records</summary>',
           '<p class="note directory-key"><strong>Profile Link Pending</strong> means this source record has not yet been linked to a researched profile. A profile may already exist under another name; identity review comes first.</p>',
           '<div class="directory-paths"><section><h2>Sourced name records</h2><p>A directory entry is not a researched profile. '
           'Names below retain the published category and date. These different lists cannot be added together as a count of Indigenous nations.</p></section>',
           '<section><h2>Researched profiles</h2><p>' + str(len(builder.m.nations)) + ' profiles of peoples, communities and governing bodies. '
           'Read short facts, deeper histories where available, and the evidence behind them.</p><p><a href="/nations#find">Search the researched profiles</a> '
           '&middot; <a href="/nations/resources">Histories And Rights Resources</a></p></section></div></details>',
           us_gaps(builder, extra), '<h2>Choose a source inventory</h2>', navigation,
           '<div id="directoryNames"><section class="directory-group" data-directory-inventory="us-directory" id="us-directory" aria-labelledby="us-directory-title">',
           '<h2 id="us-directory-title">United States: the published federal list</h2>',
           '<p>' + str(len(entities)) + ' published federal name records. The source states ' + str(directory['stated_count']) + ' Tribal entities.</p>',
           '<p class="note">Unresolved source-count difference: ' + esc(directory['count_discrepancy']['note']) + '</p>',
           '<details class="directory-source"><summary>Read the source and scope</summary>', '<p>' + esc(directory['scope_note']) + '</p>',
           '<p class="rc">' + source_link(source['url'], source['publisher'] + ': ' + source['title']) + '. Published <time datetime="'
           + esc(source['publication_date']) + '">' + esc(display_date(source['publication_date'])) + '</time>.</p>',
           '<p>Names are reproduced from that dated source, including its historical naming notes. A name or past listing does not establish a present land boundary, '
           'treaty right or exclusive community representation.</p></details>']
    for key, label in [('contiguous', 'Contiguous United States'), ('alaska', 'Alaska')]:
        rows = sorted((e for e in entities if e['directory_group'] == key), key=lambda e: (e['name'].casefold(), e['directory_id']))
        out.append('<section class="src-g directory-group" aria-labelledby="directory-' + key + '"><h3 id="directory-' + key + '">' + label
                   + '</h3><p class="note">' + str(len(rows)) + ' published name records</p><ul class="directory-list">')
        out += [entry(builder, e) for e in rows]
        out.append('</ul></section>')
    out.append('</section>')
    def extra_section(doc, rows):
        display, src = doc['_display'], doc['source']
        block = ['<section class="src-g directory-group" data-directory-inventory="' + esc(display['anchor']) + '" id="' + esc(display['anchor'])
                 + '" aria-labelledby="' + esc(display['anchor']) + '-title">',
                 '<h2 id="' + esc(display['anchor']) + '-title">' + esc(display['title']) + '</h2>',
                 '<p>' + str(len(rows)) + ' source records. ' + esc(doc['scope_note']) + '</p>']
        if doc.get('count_discrepancy', {}).get('status') == 'unresolved':
            block.append('<p class="note">Unresolved source-count difference: ' + esc(doc['count_discrepancy']['note']) + '</p>')
        present = {entry['directory_id'] for entry in rows}
        visible_notes = [note for note in doc.get('scoped_notes', []) if set(note['directory_ids']) <= present]
        block += ['<p class="note">' + esc(note) + '</p>' for note in doc.get('public_alerts', [])]
        block += ['<p class="note">' + esc(note['text']) + '</p>' for note in visible_notes if note['kind'] == 'alert']
        for discrepancy in doc.get('source_discrepancies', []):
            if discrepancy.get('status') == 'unresolved' and discrepancy['subject_directory_id'] in present:
                block.append('<p>' + source_link(discrepancy['announcement_url'], 'Read the other published account') + '</p>')
                for evidence in discrepancy.get('supporting_sources', []):
                    page_note = (' (pages ' + ', '.join(str(page) for page in evidence['pages']) + ')') if evidence.get('pages') else ''
                    block.append('<p class="note">' + source_link(evidence['url'], evidence['label']) + esc(page_note) + '</p>')
        block += ['<details class="directory-source"><summary>Read the source and scope</summary>',
                  '<p class="rc">' + esc(display['label']) + '; source snapshot ' + esc(display_date(doc['as_of'])) + '. '
                  + source_link(src['url'], src['publisher'] + ': ' + src.get('display_title', src['title'])) + '. Read ' + esc(display_date(datetime.fromisoformat(src['retrieved_at'].replace('Z', '+00:00')).astimezone(timezone.utc).date().isoformat())) + ' UTC.</p>',
                  '<p class="note">' + esc(doc.get('public_extraction_note', doc['extraction_note'])) + '</p>']
        block += ['<p class="note">' + esc(note) + '</p>' for note in doc.get('public_notes', [])]
        block += ['<p class="note">' + esc(note['text']) + '</p>' for note in visible_notes if note['kind'] == 'note']
        if doc.get('edition_note'):
            block.append('<p class="note">' + esc(doc['edition_note']) + '</p>')
        block.append('</details><ul class="directory-list">')
        block += [entry(builder, e) for e in sorted(rows, key=lambda e: (e['name'].casefold(), e['directory_id']))]
        block.append('</ul></section>')
        return block
    for doc, rows in us_extra:
        out += extra_section(doc, rows)
    cs = canada['source']
    out += ['<section class="src-g directory-group" data-directory-inventory="canada-directory" id="canada-directory" aria-labelledby="canada-directory-title">',
            '<h2 id="canada-directory-title">Canada: named administrative register groups</h2>',
            '<p>' + str(len(ca_entries)) + ' named registry groups, as of December 31, 2024. These are administrative records, '
            'not a count of current governments or all Indigenous peoples. The report distinguishes 619 bands from 634 registry groups.</p>',
            '<details class="directory-source"><summary>Read the source and scope</summary><p>' + esc(canada['scope_note']) + '</p>',
            '<p class="rc">' + source_link(cs['url'], cs['publisher'] + ': ' + cs['title']) + '. Snapshot <time datetime="' + esc(cs['as_of']) + '">'
            + esc(display_date(cs['as_of'])) + '</time>.</p>',
            '<p class="note">' + esc(canada['extraction_note']) + ' Contemporary names and identity links still need review against each community&#8217;s own sources.</p></details><ul class="directory-list">']
    out += [entry(builder, e) for e in sorted(ca_entries, key=lambda e: (e['name'].casefold(), e['directory_id']))]
    out.append('</ul></section>')
    for doc, rows in other_extra:
        out += extra_section(doc, rows)
    out += ['</div><div class="directory-loading"><button type="button" class="pill" id="directoryMore" aria-controls="directoryNames" hidden>Show More Names</button></div>',
            work_lanes(sources, [doc['_display']['source_id'] for doc in extra]),
            '<section class="src-g"><h2>More than a government list</h2><p>Independent communities and peoples outside state recognition must also be visible. '
            'Their own names and sources belong in this collection. We do not merge communities because their names sound similar.</p>',
            '<p><a href="/nations/for-nations">Send a correction, addition or removal request</a>. Land and rights resources link to nations and Indigenous-led organizations directly; '
            'this site does not speak on their behalf.</p></section></div>']
    return builder.sp('directory', '\n'.join(out), 'Browse separately typed Indigenous name inventories with sources, dates and openly tracked US and worldwide coverage gaps.')


def coverage(builder):
    directory, _ = load(builder.root)
    canada = load_canada(builder.root)
    focus = ['southern-ute-indian-tribe-us-co', 'ute-mountain-ute-tribe-us-co-ut-nm', 'ute-indian-tribe-uintah-ouray-us-ut',
             'fort-sill-apache-us-ok-nm', 'tonto-apache-tribe-us-az', 'lipan-apache-tribe-us-tx', 'chiricahua-apache-nation-us-nm']
    extra = inventories(builder.root)
    us_work = us_gaps(builder, extra)
    progress = ''.join('<p>' + esc(doc['_display']['title']) + ': ' + str(doc['enumerated_count'])
                       + ' source records; snapshot ' + esc(display_date(doc['as_of'])) + '. ' + esc(doc['scope_note'])
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
            + progress + us_work
            + ('<p>New researched pages: ' + ', '.join(links) + '. Distinct communities and governments keep separate records.</p>' if links else '')
            +
            '<p><a href="/nations/directory#worldwide">See the worldwide source map and inventories still to research</a>. '
            'No count here defines who is Indigenous, and no worldwide completeness is claimed.</p></section>')
