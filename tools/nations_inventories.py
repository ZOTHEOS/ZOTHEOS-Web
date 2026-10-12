"""Separately typed research name inventories. These never create nation facts or identity matches."""
import datetime as dt
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

INVENTORIES = (
    ('ca_fn_profiles_2026.json', 'ca-profile-', 'first_nation_profile', 'CA', 'ca-first-nation-profiles',
     'canada-profiles', 'Canada: the First Nation Profiles search', 'First Nation profile search records'),
    ('br_census_groups_2022.json', 'br-census-', 'census_ethnicity_people_or_group', 'BR', 'br-ibge-census-2022',
     'brazil-census', 'Brazil: named 2022 census categories', 'Named census ethnicity, people or group categories'),
)
MAX_BYTES = 4 * 1024 * 1024


def https(url):
    try:
        p = urlsplit(url)
        if (p.scheme != 'https' or not p.hostname or p.username or p.password
                or p.port not in (None, 443) or re.search(r'[\s"<>]', url)):
            raise ValueError('Inventory source must use public HTTPS')
    except (TypeError, ValueError) as exc:
        raise ValueError('Inventory source must use public HTTPS') from exc
    return url


def text(value, label, limit=1600):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError('Invalid inventory ' + label)
    return value


def snapshot(value):
    if isinstance(value, str) and re.fullmatch(r'\d{4}', value):
        if not 1 <= int(value) <= dt.date.today().year:
            raise ValueError('Invalid inventory snapshot year')
    else:
        if dt.date.fromisoformat(value) > dt.date.today():
            raise ValueError('Future inventory snapshot')
    return value


def directory_holds(root):
    """Dated removal receipts can target directory-only names. Never auto-restore them."""
    path = Path(root) / 'data/nations/research/publication_holds.json'
    if not path.exists():
        return set()
    if path.stat().st_size > 128 * 1024:
        raise ValueError('Directory holds exceed 128 KiB')
    doc = json.loads(path.read_text(encoding='utf-8'))
    rows = doc.get('entries')
    if doc.get('schema_version') != 1 or not isinstance(rows, list) or len(rows) > 512:
        raise ValueError('Unknown or oversized directory hold contract')
    result = set()
    for row in rows:
        key = row.get('directory_id')
        if (not isinstance(key, str) or key in result
                or not re.fullmatch(r'(?:us-fed-[a-f0-9]{12}|ca-register-[0-9]{3}|ca-profile-[a-z0-9-]+|br-census-[a-z0-9-]+)', key)
                or row.get('action') not in ('hold', 'takedown')):
            raise ValueError('Invalid or duplicate directory hold')
        text(row.get('receipt'), 'removal receipt', 700)
        stamp = dt.datetime.fromisoformat(row['requested_at'].replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            raise ValueError('Directory removal receipt needs a timezone')
        result.add(key)
    return result


def documents(root):
    folder = Path(root) / 'data/nations/research'
    result = []
    for filename, prefix, unit, country, source_id, anchor, title, label in INVENTORIES:
        path = folder / filename
        if not path.exists():
            continue
        if path.stat().st_size > MAX_BYTES:
            raise ValueError('Inventory exceeds 4 MiB')
        doc = json.loads(path.read_text(encoding='utf-8'))
        entities, source = doc['entities'], doc['source']
        if (doc.get('schema_version') != 1 or doc.get('entity_unit') != unit
                or not 0 < len(entities) <= 5000 or doc['enumerated_count'] != len(entities)
                or len({e['directory_id'] for e in entities}) != len(entities)):
            raise ValueError('Inventory units, ids or counts disagree')
        stated = doc.get('stated_count')
        if stated is not None and (isinstance(stated, bool) or not isinstance(stated, int) or stated < 0):
            raise ValueError('Invalid stated inventory count')
        if stated is not None and stated != len(entities):
            if (doc.get('count_discrepancy', {}).get('status') != 'unresolved'
                    or not doc['count_discrepancy'].get('note')):
                raise ValueError('Inventory count discrepancy must remain disclosed')
        for field in ('title', 'publisher'):
            text(source[field], 'source ' + field)
        https(source['url'])
        if source.get('display_title'):
            text(source['display_title'], 'source display title')
        for note in doc.get('public_notes', []):
            text(note, 'public scope note')
        stamp = dt.datetime.fromisoformat(source['retrieved_at'].replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            raise ValueError('Inventory receipt needs a timezone')
        if not re.fullmatch(r'[a-f0-9]{64}', source['sha256']):
            raise ValueError('Inventory source needs its measured SHA-256')
        snapshot(doc['as_of'])
        text(doc['scope_note'], 'scope note')
        text(doc['extraction_note'], 'extraction note')
        if doc.get('public_extraction_note'):
            text(doc['public_extraction_note'], 'public source note')
        for e in entities:
            if (not re.fullmatch(re.escape(prefix) + r'[a-z0-9]+(?:-[a-z0-9]+)*', e['directory_id'])
                    or e['entity_type'] != unit or e['countries'] != [country]
                    or e['as_of'] != doc['as_of']):
                raise ValueError('Inventory record differs from its typed source scope')
            text(e['name'], 'name', 700)
            text(e['directory_name'], 'source name', 700)
            crosswalk = e['registry_crosswalk']
            if crosswalk['status'] not in ('unreviewed', 'confirmed', 'not_same_entity'):
                raise ValueError('Unknown inventory identity review state')
            if crosswalk['status'] != 'confirmed' and crosswalk.get('registry_id'):
                raise ValueError('Unreviewed inventory identity cannot link a profile')
            if crosswalk['status'] != 'unreviewed' and (not crosswalk.get('reviewer') or not crosswalk.get('evidence_receipt')):
                raise ValueError('Inventory identity decision needs an explicit review receipt')
            if crosswalk['status'] == 'confirmed' and not crosswalk.get('registry_id'):
                raise ValueError('Confirmed inventory identity needs a registry id')
            if not isinstance(crosswalk.get('candidates'), list):
                raise ValueError('Inventory identity candidates must be a list')
            if e.get('official_url'):
                https(e['official_url'])
                review = e.get('official_url_review', {})
                if review.get('status') != 'verified' or not review.get('reviewer') or not review.get('evidence_receipt'):
                    raise ValueError('Inventory website needs a separate source review')
        doc['_display'] = {'anchor': anchor, 'title': title, 'label': label, 'source_id': source_id}
        result.append(doc)
    return result
