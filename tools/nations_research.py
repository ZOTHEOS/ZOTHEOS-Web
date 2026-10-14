#!/usr/bin/env python3
"""Durable Nations research queue. Stdlib only; offline and read-only by default.

This tool cannot publish profiles, approve identity matches, or modify nations.json.
Use the existing source/verify/respect assembler and a reviewed PR for publication.
"""
import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.parse

import nations_inventories as I

DEFAULT_ROOT = Path(__file__).resolve().parent.parent
DATA = Path('data/nations/research')
TASK_STATUSES = {'pending', 'researching', 'needs_review', 'blocked'}
UNITS = {'federally_listed_tribal_entity', 'directory_government_or_affiliate', 'first_nation_profile',
         'indian_register_group', 'inuit_land_claim_region', 'metis_representative_government',
         'people_or_community', 'linguistic_community', 'census_self_identification_category',
         'indigenous_people', 'census_ethnicity_people_or_group', 'census_indigenous_people',
         'people_or_nationality', 'representative_organization', 'inuit_representative_body',
         'source_discovery', 'nation_owned_source', 'research_subject', 'state_tribal_directory_listing'}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def stamp(value=None):
    date = dt.datetime.fromisoformat(value.replace('Z', '+00:00')) if value else dt.datetime.now(dt.timezone.utc)
    if date.tzinfo is None:
        raise ValueError('Timestamp needs an explicit timezone')
    return date.astimezone(dt.timezone.utc)


def source_allowed(url, source):
    try:
        parts = urllib.parse.urlsplit(url)
        return (parts.scheme == 'https' and not parts.username and not parts.password
                and parts.port in (None, 443) and parts.hostname in source['allowed_hosts'])
    except (TypeError, ValueError):
        return False


def paths(root):
    folder = Path(root) / DATA
    return folder / 'coverage_queue.json', folder / 'directory_sources.json', folder / 'us_federal_directory.json'


def directory_entries(root):
    entries = load(paths(root)[2])['entities'][:]
    for doc in I.documents(root):
        entries.extend(doc['entities'])
    return entries


def validate(root):
    qp, sp, dp = paths(root)
    queue, sources, directory = load(qp), load(sp), load(dp)
    errors = []
    I.directory_holds(root)
    source_map = {s['source_id']: s for s in sources['sources']}
    registry_path = Path(root)/'data/nations/nations.json'
    registry_ids = {n['id'] for n in load(registry_path)['nations']} if registry_path.exists() else None
    allowed_hosts = {h for s in sources['sources'] for h in s['allowed_hosts']}
    if len(source_map) != len(sources['sources']):
        errors.append('Duplicate source ids')
    for s in sources['sources']:
        if s['entity_unit'] not in UNITS or not source_allowed(s['url'], s):
            errors.append('Invalid source unit or HTTPS allowlist: '+s['source_id'])
    entities = directory['entities']
    ids = {e['directory_id'] for e in entities}
    if len(ids) != len(entities) or directory['enumerated_count'] != len(entities):
        errors.append('Directory ids or enumerated count do not match the actual records')
    if dict(Counter(e['directory_group'] for e in entities)) != directory['group_counts']:
        errors.append('Directory group counts do not match the records')
    if directory['stated_count'] != len(entities) and directory['count_discrepancy']['status'] != 'unresolved':
        errors.append('Source count discrepancy must stay disclosed until resolved')
    for e in entities:
        crosswalk = e['registry_crosswalk']
        if e['entity_type'] != 'federally_listed_tribal_entity' or e['countries'] != ['US']:
            errors.append('Federal list has the wrong entity unit: '+e['directory_id'])
        if e['official_url'] is not None:
            review = e.get('official_url_review', {})
            if (not source_allowed(e['official_url'], {'allowed_hosts': allowed_hosts})
                    or review.get('status') != 'verified' or not review.get('reviewer') or not review.get('evidence_receipt')):
                errors.append('Directory website link lacks a verified HTTPS/source review')
        if crosswalk['status'] not in ('unreviewed', 'confirmed', 'not_same_entity'):
            errors.append('Unknown crosswalk review status')
        if crosswalk['status'] == 'not_same_entity' and (not crosswalk.get('reviewer') or not crosswalk.get('evidence_receipt')):
            errors.append('A distinct-identity decision needs an explicit identity-review receipt')
        if crosswalk['status'] == 'confirmed':
            if not crosswalk.get('registry_id') or not crosswalk.get('reviewer') or not crosswalk.get('evidence_receipt'):
                errors.append('Confirmed crosswalk lacks an explicit identity-review receipt')
            if registry_ids is None or crosswalk.get('registry_id') not in registry_ids:
                errors.append('Confirmed crosswalk must point to an existing registry id')
        elif crosswalk.get('registry_id'):
            errors.append('Unreviewed candidate cannot become a confirmed profile link')
        if registry_ids is not None and any(c['registry_id'] not in registry_ids for c in crosswalk['candidates']):
            errors.append('Candidate crosswalk refers to an absent registry id')
    extras = I.documents(root)
    all_entries = entities + [e for doc in extras for e in doc['entities']]
    ids = {e['directory_id'] for e in all_entries}
    if len(ids) != len(all_entries):
        errors.append('Directory inventory ids collide across source categories')
    for doc in extras:
        sid = doc['_display']['source_id']
        if sid not in source_map or not source_allowed(doc['source']['url'], source_map[sid]):
            errors.append('Inventory source is outside its exact host allowlist')
        for e in doc['entities']:
            crosswalk = e['registry_crosswalk']
            if crosswalk['status'] == 'confirmed' and (registry_ids is None or crosswalk['registry_id'] not in registry_ids):
                errors.append('Confirmed inventory crosswalk must point to an existing registry id')
            if registry_ids is not None and any(c['registry_id'] not in registry_ids for c in crosswalk['candidates']):
                errors.append('Inventory candidate refers to an absent registry id')
    task_ids = set()
    for task in queue['tasks']:
        if task['task_id'] in task_ids:
            errors.append('Duplicate task id: '+task['task_id'])
        task_ids.add(task['task_id'])
        if task['status'] not in TASK_STATUSES or task['entity_type'] not in UNITS:
            errors.append('Unknown task state or entity unit: '+task['task_id'])
        if any(s not in source_map for s in task['allowed_source_ids']):
            errors.append('Unknown task source id: '+task['task_id'])
        if task['entity_id'] and task['entity_id'] not in ids:
            errors.append('Unknown directory entity: '+task['task_id'])
        elif task['entity_id']:
            entry = next(e for e in all_entries if e['directory_id'] == task['entity_id'])
            if task['entity_type'] != entry['entity_type'] or task['countries'] != entry['countries']:
                errors.append('Task differs from its typed directory scope: '+task['task_id'])
        for signal in task['risk']['signals']:
            required = {'source_url', 'publication_date', 'event_date', 'receipt_id', 'review_status'}
            if not required <= signal.keys() or signal['review_status'] != 'pending':
                errors.append('Risk signals need dated evidence and independent review')
    return errors


def audit(root):
    qp, sp, dp = paths(root)
    registry = load(Path(root)/'data/nations/nations.json')
    directory, queue, sources = load(dp), load(qp), load(sp)
    return {
        'registry_unit': 'Mixed peoples, governments and representative entries; untyped in the published contract',
        'registry_entries': len(registry['nations']),
        'registry_facts': sum(len(n['facts']) for n in registry['nations']),
        'registry_by_region': dict(sorted(Counter(n['region'] for n in registry['nations']).items())),
        'registry_by_country': dict(sorted(Counter(c for n in registry['nations'] for c in n['countries']).items())),
        'directory_unit': 'Published US federal-list name records',
        'directory_stated_count': directory['stated_count'],
        'directory_enumerated_count': len(directory['entities']),
        'directory_exact_candidate_rows': sum(bool(e['registry_crosswalk']['candidates']) for e in directory['entities']),
        'directory_no_exact_candidate_rows': sum(not e['registry_crosswalk']['candidates'] for e in directory['entities']),
        'directory_confirmed_crosswalks': sum(e['registry_crosswalk']['status'] == 'confirmed' for e in directory['entities']),
        'queue_by_status': dict(Counter(t['status'] for t in queue['tasks'])),
        'queue_by_region': dict(sorted(Counter(t['region'] for t in queue['tasks']).items())),
        'source_units': [{'source_id': s['source_id'], 'unit': s['entity_unit'], 'stated_count': s['stated_count'], 'as_of': s['as_of']} for s in sources['sources']],
        'additional_inventories': [{'unit': d['entity_unit'], 'snapshot': d['as_of'], 'records': len(d['entities']), 'stated_count': d.get('stated_count'), 'count_discrepancy': d.get('count_discrepancy')} for d in I.documents(root)],
        'coverage_percent': None,
        'note': 'No government-coverage percentage is computed from the mixed registry. Exact-name candidates still need identity review.'
    }


def due(task, now):
    after = task.get('next_attempt_after')
    if after and stamp(after) > now:
        return False
    if task['status'] in ('pending', 'blocked'):
        return True
    return task['status'] == 'researching' and task.get('lease_until') and stamp(task['lease_until']) <= now


def next_tasks(root, limit=3, now=None):
    queue = load(paths(root)[0])
    now = stamp(now)
    limit = min(max(limit, 0), queue['max_subjects_per_run'])
    held = I.directory_holds(root)
    ready = [t for t in queue['tasks'] if due(t, now) and t.get('entity_id') not in held]
    ready.sort(key=lambda t: (-t['priority'], t['subject'].casefold(), t['task_id']))
    # At an equal priority, rotate among geographic lanes before a second task
    # from one lane. Explicit owner-priority work remains first.
    selected, seen = [], set()
    for priority in sorted({t['priority'] for t in ready}, reverse=True):
        group = [t for t in ready if t['priority'] == priority]
        fresh, rest, lanes = [], [], set(seen)
        for task in group:
            if task['region'] not in lanes:
                fresh.append(task); lanes.add(task['region'])
            else:
                rest.append(task)
        for task in fresh+rest:
            if len(selected) >= limit:
                return selected
            selected.append(task)
            seen.add(task['region'])
    return selected


def write_queue(root, queue):
    path = paths(root)[0]
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(queue, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    temporary.replace(path)


def reconcile(root, now=None):
    """Do not re-add known registry entries or treat name candidates as approvals."""
    errors = validate(root)
    if errors:
        raise ValueError('; '.join(errors))
    queue = load(paths(root)[0])
    directory = {e['directory_id']:e for e in directory_entries(root)}
    registry_ids = {n['id'] for n in load(Path(root)/'data/nations/nations.json')['nations']}
    task_ids = {t['task_id'] for t in queue['tasks']}
    changed, added, resolved = [], [], []
    for task in queue['tasks']:
        if task.get('task_type') != 'entity_profile' or task['status'] not in ('pending', 'blocked', 'needs_review'):
            continue
        entry = directory.get(task['entity_id'])
        if not entry:
            continue
        review = entry['registry_crosswalk']
        if review['status'] == 'confirmed' and review['registry_id'] in registry_ids:
            if (task.get('profile_disposition') != 'exists_in_registry' or task['status'] != 'needs_review'
                    or task.get('identity_receipt') != review['evidence_receipt']):
                task.update(status='needs_review', profile_disposition='exists_in_registry',
                            note='Existing registry profile linked by an explicit identity-review receipt. Do not re-add it; existing source-refresh rules apply.',
                            identity_receipt=review['evidence_receipt'],
                            identity_review_kind=review.get('review_kind', 'explicit source review'),
                            updated_at=stamp(now).isoformat(), next_attempt_after=None)
                changed.append(task['task_id'])
            continue
        if task['status'] == 'needs_review':
            if task.get('profile_disposition') == 'identity_crosswalk_first' and review['status'] == 'not_same_entity':
                task.update(status='pending',profile_disposition='distinct_entity_reviewed',
                            note='Explicit source-backed identity review found the candidates are different entities. A distinct profile may now be researched.',
                            updated_at=stamp(now).isoformat(),next_attempt_after=None)
                changed.append(task['task_id'])
            continue
        candidates = [c['registry_id'] for c in review['candidates'] if c['registry_id'] in registry_ids]
        if review['status'] == 'unreviewed' and candidates:
            task['profile_disposition'] = 'identity_crosswalk_first'
            task['note'] = 'Existing exact-name candidates need identity review before any new profile draft. A broader people entry is not automatically the same government.'
            identity_id = 'identity-'+entry['directory_id']
            if identity_id not in task_ids:
                identity = dict(task)
                identity.update(task_id=identity_id, task_type='identity_review', status='pending',
                                subject='Resolve identity crosswalk: '+entry['name'],
                                candidate_registry_ids=candidates, receipts=[], note=None,
                                profile_disposition=None, updated_at=None, next_attempt_after=None)
                added.append(identity); task_ids.add(identity_id)
        else:
            continue
        task['status'] = 'needs_review'
        task['updated_at'] = stamp(now).isoformat()
        changed.append(task['task_id'])
    queue['tasks'].extend(added)
    for task in queue['tasks']:
        if task.get('task_type') != 'identity_review' or task['status'] not in ('pending', 'blocked', 'needs_review'):
            continue
        entry = directory.get(task['entity_id'])
        if not entry or entry['registry_crosswalk']['status'] == 'unreviewed':
            continue
        review = entry['registry_crosswalk']
        if (task.get('profile_disposition') != 'identity_resolved_in_crosswalk'
                or task['status'] != 'needs_review' or task.get('identity_receipt') != review['evidence_receipt']):
            task.update(status='needs_review', profile_disposition='identity_resolved_in_crosswalk',
                        note='Explicit identity review is recorded in the directory crosswalk. Do not repeat this identity task.',
                        identity_receipt=review['evidence_receipt'],
                        identity_review_kind=review.get('review_kind', 'explicit source review'),
                        updated_at=stamp(now).isoformat(), next_attempt_after=None)
            resolved.append(task['task_id'])
    write_queue(root, queue)
    return {'changed_profile_tasks':changed,'new_identity_tasks':[t['task_id'] for t in added],
            'resolved_identity_tasks':resolved,
            'note':'No identity matches, source claims or human approvals were generated.'}


def transition(root, task_id, action, now=None, note=None, receipt=None):
    if action not in ('claim', 'finish', 'block'):
        raise ValueError('Only research queue transitions are supported')
    errors = validate(root)
    if errors:
        raise ValueError('; '.join(errors))
    queue = load(paths(root)[0])
    task = next((t for t in queue['tasks'] if t['task_id'] == task_id), None)
    if task is None:
        raise ValueError('Unknown task id')
    current = stamp(now)
    if action == 'claim':
        if task.get('entity_id') in I.directory_holds(root):
            raise ValueError('Directory subject has a publication hold; do not research or restore it automatically')
        if not due(task, current):
            raise ValueError('Task is already leased or awaiting review')
        task['status'] = 'researching'
        task['lease_until'] = (current+dt.timedelta(hours=4)).isoformat()
    else:
        if task['status'] != 'researching' or not note:
            raise ValueError('Claim the task first and provide a factual handoff note')
        if receipt:
            sources = {s['source_id']:s for s in load(paths(root)[1])['sources']}
            sid = receipt.get('source_id')
            if sid not in task['allowed_source_ids'] or not source_allowed(receipt.get('url', ''), sources[sid]):
                raise ValueError('Receipt URL is outside the task source allowlist')
            if not receipt.get('retrieved_at'):
                raise ValueError('Receipt needs a real retrieval timestamp')
            stamp(receipt['retrieved_at'])
            # No fabricated HTTP codes or byte hashes for browser-only reads.
            if receipt.get('retrieval_method') == 'http':
                if not isinstance(receipt.get('http_status'), int):
                    raise ValueError('HTTP receipt needs the measured status')
                if receipt['http_status'] == 200 and not re.fullmatch('[0-9a-f]{64}', receipt.get('sha256', '')):
                    raise ValueError('Successful HTTP receipt needs the measured body hash')
            elif receipt.get('retrieval_method') == 'browser_tool':
                if 'http_status' in receipt or not receipt.get('source_title') or not receipt.get('evidence'):
                    raise ValueError('Browser receipt needs observed source text, without a guessed HTTP code')
            else:
                raise ValueError('Unknown receipt method')
            receipt = dict(receipt)
            receipt['receipt_id'] = 'r-'+hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()[:16]
            task['receipts'].append(receipt)
        usable = [r for r in task['receipts'] if r.get('retrieval_method') == 'browser_tool'
                  or r.get('retrieval_method') == 'http' and r.get('http_status') == 200]
        if action == 'finish' and not usable:
            raise ValueError('A review handoff needs at least one dated source receipt')
        task['status'] = 'needs_review' if action == 'finish' else 'blocked'
        task['note'] = note
        task['lease_until'] = None
        task['next_attempt_after'] = (current+dt.timedelta(days=1)).isoformat() if action == 'block' else None
    task['updated_at'] = current.isoformat()
    write_queue(root, queue)
    return task


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=DEFAULT_ROOT)
    parser.add_argument('--now', help='ISO timestamp with timezone; defaults to actual UTC time')
    subs = parser.add_subparsers(dest='command', required=True)
    subs.add_parser('audit')
    subs.add_parser('validate')
    rec = subs.add_parser('reconcile'); rec.add_argument('--write', action='store_true')
    nxt = subs.add_parser('next'); nxt.add_argument('--limit', type=int, default=3)
    for command in ('claim', 'finish', 'block'):
        p = subs.add_parser(command); p.add_argument('--task', required=True); p.add_argument('--write', action='store_true')
        p.add_argument('--note'); p.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'validate':
            result = validate(args.root)
            print(json.dumps({'errors': result})); return bool(result)
        if args.command == 'audit':
            result = audit(args.root)
        elif args.command == 'next':
            result = next_tasks(args.root, args.limit, args.now)
        elif args.command == 'reconcile':
            if not args.write:
                raise ValueError('Queue mutations require the explicit --write flag')
            result = reconcile(args.root, args.now)
        else:
            if not args.write:
                raise ValueError('Queue mutations require the explicit --write flag')
            receipt = load(args.receipt) if args.receipt else None
            result = transition(args.root, args.task, args.command, args.now, args.note, receipt)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
