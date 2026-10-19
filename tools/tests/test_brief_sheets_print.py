"""Every committed printable sheet prints on at most two pages on A4 and on US Letter (Living Gallery piece 3).

Runs the committed pages in Chrome through Playwright (channel="chrome", --mute-audio), served from the tree with the
committed vercel.json headers. Nothing reaches the network. Skipped only where Playwright or Chrome is missing.
"""
import io
import json
import os
from pathlib import Path
import re

import pytest

REPO = Path(os.environ.get('ZOTHEOS_TEST_REPO', Path(__file__).resolve().parents[2]))
TYPES = {'.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.woff2': 'font/woff2',
         '.png': 'image/png', '.ico': 'image/x-icon', '.txt': 'text/plain; charset=utf-8', '.svg': 'image/svg+xml'}


def page_count(pdf):
    try:
        import pypdf
        return len(pypdf.PdfReader(io.BytesIO(pdf)).pages)
    except ImportError:
        return len(re.findall(rb'/Type\s*/Page(?!s)', pdf))


def test_every_sheet_prints_on_at_most_two_pages():
    sync_api = pytest.importorskip('playwright.sync_api')
    pages = sorted((REPO / 'nations/brief').glob('*.html'))
    assert pages
    conf = json.loads((REPO / 'vercel.json').read_text(encoding='utf8'))
    rules = [(re.compile('^' + h['source'] + '$'), {x['key']: x['value'] for x in h['headers']}) for h in conf['headers']]
    root = REPO.resolve()
    off_site = []

    def serve(route):
        url = route.request.url
        if not url.startswith('https://zotheos.org/'):
            off_site.append(url)
            return route.abort()
        path = url[len('https://zotheos.org'):].split('#')[0].split('?')[0]
        rel = path.lstrip('/')
        for cand in (rel, rel + '.html'):
            f = (root / cand).resolve()
            if cand and f.is_file() and root in f.parents:
                headers = {}
                for rx, hs in rules:
                    if rx.match(path):
                        headers.update(hs)
                headers['content-type'] = TYPES.get(f.suffix, 'application/octet-stream')
                return route.fulfill(status=200, body=f.read_bytes(), headers=headers)
        return route.fulfill(status=404, body='')
    with sync_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel='chrome', args=['--mute-audio'])
        except Exception as error:  # pragma: no cover - depends on the machine
            pytest.skip(f'Chrome is not available to Playwright: {error}')
        context = browser.new_context()
        context.route('**/*', serve)
        page = context.new_page()
        counts = {}
        for sheet in pages:
            page.goto('https://zotheos.org/nations/brief/' + sheet.stem, wait_until='load')
            page.evaluate('document.fonts.ready.then(() => true)')
            for size in ('A4', 'Letter'):
                counts[(sheet.stem, size)] = page_count(page.pdf(format=size))
        browser.close()
    assert off_site == []
    assert all(1 <= n <= 2 for n in counts.values()), counts
