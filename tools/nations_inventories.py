"""Separately typed research name inventories. These never create nation facts or identity matches."""
import datetime as dt
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

INVENTORIES = (
    ('us_va_state_directory_2026.json', 'us-state-va-', 'state_tribal_directory_listing', 'US', 'us-va-tribal-directory',
     'us-virginia', 'United States: Virginia tribal directory', 'Virginia state directory listings'),
    ('us_nc_state_directory_2026.json', 'us-state-nc-', 'state_tribal_directory_listing', 'US', 'us-nc-tribal-directory',
     'us-north-carolina', 'United States: North Carolina tribal directory', 'North Carolina state directory listings'),
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
        if not 1 <= int(value) <= dt.datetime.now(dt.timezone.utc).year:
            raise ValueError('Invalid inventory snapshot year')
    else:
        if dt.date.fromisoformat(value) > dt.datetime.now(dt.timezone.utc).date():
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
                or not re.fullmatch(r'(?:us-fed-[a-f0-9]{12}|us-state-(?:va|nc)-[a-z0-9]+(?:-[a-z0-9]+)*|ca-register-[0-9]{3}|ca-profile-[a-z0-9-]+|br-census-[a-z0-9-]+)', key)
                or row.get('action') not in ('hold', 'takedown')):
            raise ValueError('Invalid or duplicate directory hold')
        text(row.get('receipt'), 'removal receipt', 700)
        stamp = dt.datetime.fromisoformat(row['requested_at'].replace('Z', '+00:00'))
        if stamp.tzinfo is None:
            raise ValueError('Directory removal receipt needs a timezone')
        result.add(key)
    return result


def state_receipt(folder, reference):
    # Referenced state evidence must exist in this contract, never escape into other workspace files.
    if not isinstance(reference, str) or not re.fullmatch(r'receipts/[a-zA-Z0-9][a-zA-Z0-9._-]{0,180}\.json', reference):
        raise ValueError('State evidence receipt must use a confined receipts JSON path')
    path = folder / reference
    if (not path.is_file() or path.is_symlink() or path.stat().st_size > 128 * 1024
            or path.resolve().parent != (folder / 'receipts').resolve()):
        raise ValueError('State evidence receipt is missing or outside its bounded folder')
    receipt = json.loads(path.read_text(encoding='utf-8'))
    if receipt.get('http_status') != 200 or not re.fullmatch(r'[a-f0-9]{64}', receipt.get('sha256', '')):
        raise ValueError('State evidence receipt must retain a successful measured source hash')
    stamp = dt.datetime.fromisoformat((receipt.get('retrieved_at') or receipt.get('checked_at') or '').replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('State evidence receipt needs an actual timestamp with timezone')
    https(receipt.get('final_url') or receipt.get('url') or receipt.get('source_url'))
    return receipt


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
        for note in doc.get('public_notes', []) + doc.get('public_alerts', []):
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
        if unit == 'state_tribal_directory_listing':
            state = 'VA' if prefix == 'us-state-va-' else 'NC'
            if doc.get('state') != state or doc.get('snapshot_kind') != 'source_observation':
                raise ValueError('State inventory must retain its observed geographic scope')
            measured = state_receipt(folder, source.get('receipt'))
            if (measured.get('url') != source['url'] or measured['sha256'] != source['sha256']
                    or measured.get('retrieved_at') != source['retrieved_at']):
                raise ValueError('State inventory source must match its measured evidence receipt')
            if doc['as_of'] != stamp.astimezone(dt.timezone.utc).date().isoformat():
                raise ValueError('State snapshot must use its actual UTC source observation date')
        entry_ids = {e['directory_id'] for e in entities}
        scoped_notes = doc.get('scoped_notes', [])
        if not isinstance(scoped_notes, list) or len(scoped_notes) > 32:
            raise ValueError('Inventory scoped notes exceed their bounded contract')
        for note in scoped_notes:
            refs = note.get('directory_ids')
            if (note.get('kind') not in ('alert', 'note') or not isinstance(refs, list)
                    or not 0 < len(refs) <= 16 or len(set(refs)) != len(refs)
                    or any(key not in entry_ids for key in refs)):
                raise ValueError('Named inventory notes need known distinct directory bindings')
            text(note.get('text'), 'scoped source note')
        for discrepancy in doc.get('source_discrepancies', []):
            if discrepancy.get('subject_directory_id') not in entry_ids or discrepancy.get('status') != 'unresolved':
                raise ValueError('Inventory discrepancy needs its known held-capable subject')
            https(discrepancy['announcement_url'])
            supporting = discrepancy.get('supporting_sources', [])
            if not isinstance(supporting, list) or len(supporting) > 8:
                raise ValueError('Inventory supporting sources exceed their bounded contract')
            for evidence in supporting:
                text(evidence.get('label'), 'supporting source label', 240)
                https(evidence.get('url'))
                measured = state_receipt(folder, evidence.get('receipt'))
                if measured.get('url') != evidence['url'] or measured.get('final_url') != evidence['url']:
                    raise ValueError('Supporting source URL must match its measured receipt and destination')
                pages = evidence.get('pages', [])
                if (not isinstance(pages, list) or len(pages) > 32
                        or any(type(page) is not int or page <= 0 for page in pages)):
                    raise ValueError('Supporting source page references must be bounded positive integers')
        for e in entities:
            if (not re.fullmatch(re.escape(prefix) + r'[a-z0-9]+(?:-[a-z0-9]+)*', e['directory_id'])
                    or e['entity_type'] != unit or e['countries'] != [country]
                    or e['as_of'] != doc['as_of']):
                raise ValueError('Inventory record differs from its typed source scope')
            if unit == 'state_tribal_directory_listing' and e.get('state') != state:
                raise ValueError('State directory record differs from its source scope')
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
                if unit == 'state_tribal_directory_listing':
                    measured = state_receipt(folder, review['evidence_receipt'])
                    if (measured.get('final_url') != e['official_url']
                            or not (review.get('evidence') or measured.get('evidence_phrase'))):
                        raise ValueError('State official website must match its source identity evidence')
        doc['_display'] = {'anchor': anchor, 'title': title, 'label': label, 'source_id': source_id}
        result.append(doc)
    return result
