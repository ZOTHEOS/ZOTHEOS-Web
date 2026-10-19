#!/usr/bin/env python3
"""Doors: the homepage explore section (#explore-zotheos), drawn from the site's own data (Living Gallery, piece 4).

Writes the five doors between <!-- zth:doors:start --> and <!-- zth:doors:end --> in index.html. Every number on a door
is computed here, in one run, with the loaders the Nations, Paths To Action and Theater builds use, so holds, hidden
Nations and held facts are left out exactly as they are on the pages each door opens onto. No number is typed into the
page. When a Codex data batch changes a count, the test suite fails with the one-line fix.

    py -3.10 tools/landing_doors.py            rewrite the block in index.html
    py -3.10 tools/landing_doors.py --check    exit 1 when index.html is out of date (the suite runs this)
    py -3.10 tools/landing_doors.py --install  one time: put the markers in place of the old five-card grid

The art switch is tools/zth_art.py ART_STEPS (plain until the owner's Roots decision). The doors add no script and load
nothing, so the page's script hashes and policies do not move. The Theater door keeps its class ws-theater, so the
Theater chapter's pictogram stays where that chapter puts it.
"""
import argparse
import html
import json
import os
import re
import sys

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
START, END = '<!-- zth:doors:start -->', '<!-- zth:doors:end -->'
# The grid the doors replace, as it stood on main (used once by --install).
OLD_GRID = re.compile(r'<div class="ws-grid"><a class="ws-card ws-pathways" href="/nations/paths-to-action">.*?'
                      r'<span class="ws-action">Open The Games ↗</span></a></div>', re.S)
# Theater rows in two visible groups, never sorted by count: whole works first, then the records that are a part of a
# work or point to one. Within a group the order is KINDS' own. Together they must name every KINDS key exactly once.
WATCH_GROUPS = (('full-film', 'recorded-program', 'short'), ('excerpt', 'trailer', 'official-page'))
WATCH_ORDER = tuple(k for g in WATCH_GROUPS for k in g)
# How the Paths door names each lane in its one computed line: (one, many).
LANE_PHRASES = {'website-now': ('step on this website', 'steps on this website'),
                'reader-controlled': ('you do yourself', 'you do yourself'),
                'future-app': ('proposed for the app', 'proposed for the app')}
WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve']


def e(value):
    return html.escape(str(value), quote=True)


class DoorsError(Exception):
    pass


def word(n):
    if not 0 <= n < len(WORDS):
        raise DoorsError(f'no number word for {n}')
    return WORDS[n]


def fmt(n):
    return f'{n:,}'


def plural(n, one, many):
    return one if n == 1 else many


def gather(root):
    """Every value the doors draw, from the same loaders as the pages they open onto."""
    sys.path.insert(0, os.path.join(root, 'tools'))
    import nations_lib as L
    import nations_pathways as P
    import theater_build as T

    m = L.Model(root)
    if m.errors:
        raise DoorsError('nations data: ' + '; '.join(m.errors))
    _, chapters, _ = P.load(root, m)
    if list(LANE_PHRASES) != list(P.SCOPES):
        raise DoorsError('Paths To Action lanes changed: update LANE_PHRASES in tools/landing_doors.py')
    with open(os.path.join(root, 'data', 'theater', 'films.json'), encoding='utf-8') as f:
        films = T.validate(json.load(f))
    if sorted(WATCH_ORDER) != sorted(T.KINDS):
        raise DoorsError('Theater viewing types changed: update WATCH_GROUPS in tools/landing_doors.py')
    counts = {k: 0 for k in WATCH_ORDER}
    for film in films['films']:
        counts[film['viewing']] += 1
    history = [(n, f) for n in m.nations for f in n['facts'] if f['kind'] == 'history']
    decades = {}
    for _, f in history:
        if f['as_of']:
            year = str(f['as_of'])[:4]
            if not re.fullmatch(r'\d{4}', year):
                raise DoorsError('history fact with an unreadable year: ' + f['id'])
            decades[int(year) // 10 * 10] = decades.get(int(year) // 10 * 10, 0) + 1
    per_region = {}
    for n in m.nations:
        per_region[n['region']] = per_region.get(n['region'], 0) + 1
    return {
        'chapters': len(chapters), 'scopes': list(P.SCOPES), 'method': tuple(P.METHOD), 'method_label': P.METHOD_LABEL,
        'lanes': [[s['scope'] for s in c['steps']] for c in chapters],
        'viewing': [(k, T.KINDS[k], counts[k]) for k in WATCH_ORDER], 'films': len(films['films']),
        'profiles': len(m.nations), 'region_counts': [per_region.get(r['key'], 0) for r in m.regions],
        'history_facts': len(history), 'history_nations': len({n['id'] for n, _ in history}),
        'decades': decades, 'undated': sum(1 for _, f in history if not f['as_of']),
    }


# ------------------------------------------------------------------------------------------------------- the doors
def door(key, index, title, para, href, action, figure, wide=False):
    """One door. The heading comes first in the document, so in heading navigation the figure belongs to its own door;
    CSS places the figure first on screen. The action is the door's one link, last, stretched over the whole door."""
    cls = f'ws-door ws-{key}' + (' ws-wide' if wide else '')
    return (f'<article class="{cls}" aria-labelledby="wsd-{key}">'
            f'<span class="ws-index">{index}</span><h3 id="wsd-{key}">{title}</h3><p>{para}</p>{figure}'
            f'<a class="ws-action" href="{href}">{action}<span aria-hidden="true"> ↗</span></a></article>')


def lane_line(d):
    """One computed sentence that explains the three lanes where the homepage introduces them. While every public
    pathway has exactly one step in each lane it says so; otherwise it gives the true totals."""
    keys = d['scopes']
    if d['lanes'] and all(sorted(c) == sorted(keys) for c in d['lanes']):
        one = [LANE_PHRASES[k][0] for k in keys]
        lead = 'Each also has' if len(d['lanes']) > 1 else 'It also has'
        return f'{lead} one {one[0]}, one {one[1]} and one {one[2]}.'
    totals = [sum(c.count(k) for c in d['lanes']) for k in keys]
    parts = [f'{n} {LANE_PHRASES[k][0 if n == 1 else 1]}' for n, k in zip(totals, keys)]
    return f'Together they hold {parts[0]}, {parts[1]} and {parts[2]}.'


def paths_figure(d, A):
    c = d['chapters']
    lead = 'Each includes' if c != 1 else 'It includes'
    caption = f'{c} {plural(c, "pathway", "pathways")}. {lead} something you can prepare offline. {lane_line(d)}'
    return A.door_figure('paths', A.door_climb(d['method'], d['method_label']), caption)


def theater_figure(d, A):
    top = max(c for _, _, c in d['viewing'])
    second = WATCH_GROUPS[1][0]
    group = ' class="ws-g2"'
    rows = ''.join(f'<div{group if k == second else ""}><dt>{e(label)}</dt><dd><span class="n">{c}</span>'
                   f'{A.bar(c, top)}</dd></div>' for k, label, c in d['viewing'])
    caption = f'{fmt(d["films"])} records in {word(len(d["viewing"]))} viewing types.'
    return A.door_figure('theater', f'<dl class="ws-ledger">{rows}</dl>', caption)


def nations_figure(d, A):
    """One equal cell per region in the directory's own order, holding that region's profile count: this directory's
    coverage so far, shown as numerals so no shape can read as how many peoples live anywhere. Never sorted."""
    counts, p = d['region_counts'], d['profiles']
    r = len(counts)
    if sum(counts) != p:
        raise DoorsError('region counts do not add up to the profile count')
    caption = f'{fmt(p)} {plural(p, "profile", "profiles")} in {r} {plural(r, "region", "regions")} so far'
    if r > 1 and min(counts) == max(counts):
        caption += f', {fmt(counts[0])} in each.'
    elif r > 1:
        caption += f', from {fmt(min(counts))} in the least covered region to {fmt(max(counts))} in the most.'
    else:
        caption += '.'
    cells = ''.join(f'<li>{n}</li>' for n in counts)
    return A.door_figure('nations', f'<ol class="ws-regions" aria-hidden="true">{cells}</ol>', caption)


def history_figure(d, A):
    """One square per published history fact, stacked in the decade its statement gives; a dotted lead run before the
    first decade (earlier, not to scale), and the facts with no year kept apart, never guessed into a decade."""
    dec, nd = d['decades'], d['undated']
    if not dec:
        raise DoorsError('no dated history fact: the Histories rail has nothing to draw')
    lo, hi = min(dec), max(dec)
    cols = ''.join('<b>' + '<i></i>' * dec.get(y, 0) + '</b>' for y in range(lo, hi + 10, 10))
    undated = (f'<span class="ws-rail-sep"></span><span class="ws-rail-undated">{"<i></i>" * nd}</span>') if nd else ''
    key_undated = f'<span class="ws-rail-key ws-rail-key-undated"><span class="n">{nd}</span> No year given</span>' if nd else ''
    marks = (f'<div class="ws-rail"><span class="ws-rail-lead"></span><span class="ws-rail-dated">{cols}</span>{undated}'
             f'<span class="ws-rail-axis" aria-hidden="true"><span>{lo}s</span><span>{hi}s</span></span>'
             f'<span class="ws-rail-key ws-rail-key-dated"><span class="n">{sum(dec.values())}</span> Year given'
             f'<span class="sr-only">, from the {lo}s to the {hi}s</span></span>{key_undated}</div>')
    hf, hn = d['history_facts'], d['history_nations']
    caption = (f'{fmt(hf)} published historical {plural(hf, "fact", "facts")} across {fmt(hn)} '
               f'{plural(hn, "Nation", "Nations")}. The record here begins where the cited sources begin, '
               'not where the history begins.')
    return A.door_figure('history', marks, caption)


def render(d, steps=None):
    sys.path.insert(0, TOOLS)
    import zth_art as A
    saved = A.ART_STEPS
    A.ART_STEPS = A.stepped(steps)
    try:
        c = d['chapters']
        paths_para = (f'{word(c).capitalize()} practical {plural(c, "pathway", "pathways")} through land, representation, '
                      'language and more. Follow the evidence, prepare a concrete next step and keep the decision in your hands.')
        doors = [
            door('pathways', 'From Understanding To Action', 'What Can ZOTHEOS Do For Indigenous People And Nations?',
                 paths_para, '/nations/paths-to-action', 'Explore Paths To Action', paths_figure(d, A), wide=True),
            door('theater', '01 · Watch', 'ZOTHEOS Theater',
                 'Films, shorts and conversations from official sources. Clear viewing notes, with Indigenous voices first.',
                 '/theater', 'Enter The Theater', theater_figure(d, A)),
            door('nations', '02 · Discover', 'Nations Worldwide',
                 'Distinct peoples, histories and Nations’ own resources. A growing directory with its coverage gaps visible.',
                 '/nations/directory', 'Explore The Directory', nations_figure(d, A)),
            door('history', '03 · Go Deeper', 'Histories And Resources',
                 'Continue into cited histories, languages, land and community-led knowledge.',
                 '/nations/resources', 'Follow The Sources', history_figure(d, A), wide=True),
            # The game door draws nothing: its own data (Nation cards, history cards) would only repeat another door's
            # number, and no drawing on this door may suggest a court, a temple or a ball on steps.
            door('game', '04 · Play And Learn', 'A Different Way In',
                 'Games and learning cards offer another starting point. The histories and sources remain yours to explore.',
                 '/game', 'Open The Games', '', wide=True),
        ]
        credit = A.credit(cls='ws-credit')
        return f'{START}<div class="ws-grid">{"".join(doors)}</div>{credit}{END}'
    finally:
        A.ART_STEPS = saved


def apply(page, block):
    i, j = page.find(START), page.find(END)
    if i < 0 or j < i or page.count(START) != 1 or page.count(END) != 1:
        raise DoorsError('index.html needs exactly one zth:doors block (run --install once)')
    return page[:i] + block + page[j + len(END):]


def install(page):
    if START in page:
        return page
    if len(OLD_GRID.findall(page)) != 1:
        raise DoorsError('the old explore grid was not found exactly once; install by hand')
    return OLD_GRID.sub(lambda _: START + END, page, count=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--root', default=os.path.dirname(TOOLS))
    ap.add_argument('--page', default=None, help='index.html to read and write (default <root>/index.html)')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--install', action='store_true')
    a = ap.parse_args(argv)
    target = a.page or os.path.join(a.root, 'index.html')
    try:
        with open(target, encoding='utf-8', newline='') as f:
            page = f.read()
        if a.install:
            page = install(page)
        out = apply(page, render(gather(a.root)))
        if a.check:
            if out != page:
                print('landing_doors: index.html is out of date; run py -3.10 tools/landing_doors.py', file=sys.stderr)
                return 1
            print('landing_doors --check: ok')
            return 0
        if out != page:
            with open(target, 'w', encoding='utf-8', newline='') as f:
                f.write(out)
        print('landing_doors: ' + ('written' if out != page else 'already current'))
    except (DoorsError, ValueError, KeyError, OSError) as exc:
        print('landing_doors: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
