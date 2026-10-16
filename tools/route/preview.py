"""Council Route preview harness: the fragment inside an in-memory copy of the landing, under the real landing CSP.

Nothing is written to the repository. The landing (index.html), vercel.json and the static files it needs are read from
this checkout (two levels up; build_page(base=...) takes another checkout or an extracted base with BASE_SHA.txt). When
the landing already carries the route (the integrated blocks between the council-route markers), those blocks and their
script hash are removed first, so the copy starts from the page without the route; the fragment's three blocks are then
inserted exactly as the integration did (markup on its own line after the Fusion figure, CSS as its own <style> before
</head>, JS as one new inline script before </body>), the sha256 of that one script is added to script-src exactly as
csp_sync.py does (header from vercel.json and the page's meta policy), and Playwright serves the page and every asset
through a route on https://zotheos.org. Any request to another host is aborted and recorded. With the fragment
unchanged, the served page is the integrated landing byte for byte (line endings folded to LF).

  py -3.10 tools/route/preview.py shots                  rest + 7 beats + mid-move frames, desktop and phone
  py -3.10 tools/route/preview.py shots --themes all --motions living,calm,still
  py -3.10 tools/route/preview.py checks                 behaviour checks in the real browser: autoplay on view in Living
                                                         and Calm, never in Still, an explicit Pause respected, pause and
                                                         resume by view and tab, CC, the hidden Audio slot, guarded
                                                         haptics, every theme and motion, fit, no-JS, CSP
  py -3.10 tools/route/preview.py play                   one real-time run started by scrolling into view (about 43 s)
Playback: the route starts on its own once 60% of the stage is in view in Living or Calm (never in Still), pauses under
25% or in a hidden tab and resumes in view, unless the visitor pressed Pause or stepped (held until Play). Tools that
need a still stage (shots, contrast, fit, capture) hold the route at rest before they scroll to it (hold()).
Writes PNG and JSON under <temp>/council_route/shots (or --out), never inside the checkout.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from html.parser import HTMLParser

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
FRAGMENT = os.path.join(HERE, 'council_route.fragment.html')
BASE = ROOT
SCRATCH = os.path.join(tempfile.gettempdir(), 'council_route')
ORIGIN = 'https://zotheos.org'
PIXEL_UA = ('Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/141.0.0.0 Mobile Safari/537.36')
DEVICES = {
    'desktop': dict(viewport={'width': 1600, 'height': 993}, device_scale_factor=1.25),
    'phone': dict(viewport={'width': 390, 'height': 844}, device_scale_factor=3, is_mobile=True, has_touch=True,
                  user_agent=PIXEL_UA),
}
THEMES = ['default', 'maya', 'codex', 'skeleton']
MARKERS = {
    'markup': ('<!-- council-route:markup -->', '<!-- /council-route:markup -->'),
    'css': ('/* council-route:css */', '/* /council-route:css */'),
    'js': ('/* council-route:js */', '/* /council-route:js */'),
}
TYPES = {'.woff2': 'font/woff2', '.png': 'image/png', '.mp3': 'audio/mpeg', '.ico': 'image/x-icon',
         '.mp4': 'video/mp4', '.svg': 'image/svg+xml', '.json': 'application/json'}


def read(path, mode='r'):
    with open(path, mode, **({} if 'b' in mode else {'encoding': 'utf-8', 'newline': ''})) as f:
        return f.read()


def blocks(text=None):
    """The three marked blocks of the fragment, markers included, exactly as Codex would copy them."""
    text = read(FRAGMENT) if text is None else text
    out = {}
    for name, (a, b) in MARKERS.items():
        i, j = text.find(a), text.find(b)
        assert i >= 0 and j > i and text.count(a) == 1 and text.count(b) == 1, 'marker problem: ' + name
        out[name] = text[i:j + len(b)]
    return out


class _Scripts(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bodies, self.cur = [], None

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            self.cur = 'skip' if any(k == 'src' for k, _ in attrs) else []

    def handle_data(self, data):
        if isinstance(self.cur, list):
            self.cur.append(data)

    def handle_endtag(self, tag):
        if tag == 'script':
            if isinstance(self.cur, list):
                self.bodies.append(''.join(self.cur))
            self.cur = None


def sha(body):
    return "'sha256-" + base64.b64encode(hashlib.sha256(body.encode('utf-8')).digest()).decode('ascii') + "'"


def inline_hashes(html):
    p = _Scripts()
    p.feed(html.replace('\r\n', '\n').replace('\r', '\n'))
    p.close()
    return [sha(b) for b in p.bodies]


def landing_csp(vercel):
    for entry in vercel['headers']:
        if entry['source'] == '/':
            for h in entry['headers']:
                if h['key'] == 'Content-Security-Policy':
                    return h['value']
    raise SystemExit('no landing CSP in vercel.json')


def add_hash(policy, h):
    return re.sub(r"(?<![\w-])script-src(?![\w-])([^;]*)", lambda m: 'script-src' + m.group(1) + ' ' + h, policy, count=1)


META_CSP = re.compile(r'(<meta\b[^>]*http-equiv="Content-Security-Policy"[^>]*\bcontent=")([^"]*)(")', re.I)


def base_commit(base):
    """BASE_SHA.txt of an extracted base directory, else the checkout's HEAD (marked when the tree has changes)."""
    p = os.path.join(base, 'BASE_SHA.txt')
    if os.path.exists(p):
        return read(p).strip()
    try:
        git = ['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-C', base]
        head = subprocess.run(git + ['rev-parse', 'HEAD'], capture_output=True, text=True, timeout=20).stdout.strip()
        dirty = subprocess.run(git + ['status', '--porcelain', '--untracked-files=no'], capture_output=True, text=True,
                               timeout=60).stdout.strip()
        return (head + ('+changes' if dirty else '')) or '?'
    except (OSError, subprocess.SubprocessError):
        return '?'


def strip_route(html, csp):
    """The landing without the integrated route: the three blocks and their wrappers removed exactly as the integration
    added them, and the route script's hash removed from the header and meta policies. Unchanged when not integrated."""
    found = [MARKERS[k][0] in html for k in MARKERS]
    if not any(found):
        return html, csp, None
    assert all(found), 'index.html carries only some council-route blocks'
    own = blocks(html)
    pieces = {'markup': '\n' + ' ' * 10 + own['markup'], 'css': '<style>\n' + own['css'] + '\n</style>\n',
              'js': '<script>\n' + own['js'] + '\n</script>\n'}
    for k, p in pieces.items():
        assert html.count(p) == 1, 'the integrated %s block is not wrapped as the integration wrote it' % k
        html = html.replace(p, '')
    h = sha('\n' + own['js'] + '\n')
    csp = csp.replace(' ' + h, '')
    html = META_CSP.sub(lambda m: m.group(1) + m.group(2).replace(' ' + h, '') + m.group(3), html, count=1)
    return html, csp, h


def build_page(base=BASE, fragment_text=None, with_fragment=True):
    """Returns dict(html, csp, script_hash, base_sha, report)."""
    html = read(os.path.join(base, 'index.html')).replace('\r\n', '\n').replace('\r', '\n')
    vercel = json.loads(read(os.path.join(base, 'vercel.json')))
    csp = landing_csp(vercel)
    integrated_html, integrated_csp = html, csp
    html, csp, old = strip_route(html, csp)
    base_sha = base_commit(base)
    report = {'base_sha': base_sha, 'base_bytes': len(html.encode('utf-8')), 'landing_had_route': bool(old)}
    before = set(inline_hashes(html))
    missing_before = [h for h in before if h not in csp]
    report['base_scripts_all_hashed'] = not missing_before
    if not with_fragment:
        return dict(html=html, csp=csp, script_hash=None, base_sha=base_sha, report=report)
    b = blocks(fragment_text)
    fig = html.find('<figcaption class="fusion-caption">')
    end = html.find('</figure>', fig)
    assert fig > 0 and end > fig, 'Fusion figure not found'
    end += len('</figure>')
    html = html[:end] + '\n' + ' ' * 10 + b['markup'] + html[end:]
    style = '<style>\n' + b['css'] + '\n</style>\n'
    i = html.find('</head>')
    html = html[:i] + style + html[i:]
    body = '\n' + b['js'] + '\n'
    i = html.rfind('</body>')
    html = html[:i] + '<script>' + body + '</script>\n' + html[i:]
    h = sha(body)
    csp = add_hash(csp, h)
    html = META_CSP.sub(lambda m: m.group(1) + add_hash(m.group(2), h) + m.group(3), html, count=1)
    after = inline_hashes(html)
    report.update(script_hash=h, inline_scripts=len(after),
                  new_hashes=[x for x in after if x not in before],
                  all_inline_scripts_in_policy=all(x in csp for x in after),
                  page_bytes=len(html.encode('utf-8')),
                  equals_integrated_landing=bool(old) and html == integrated_html and csp == integrated_csp)
    return dict(html=html, csp=csp, script_hash=h, base_sha=base_sha, report=report)


class Server:
    """Playwright route handler: the page and its same-origin assets; every other host is aborted and recorded."""

    def __init__(self, page_html, csp, base=BASE):
        self.html = page_html.encode('utf-8')
        self.csp = csp
        self.base = base
        self.external = []
        self.served = []

    def __call__(self, route):
        url = route.request.url
        m = re.match(r'https?://([^/]+)(/[^?#]*)?', url)
        host, path = (m.group(1), m.group(2) or '/') if m else ('', '')
        if host != 'zotheos.org':
            if not url.startswith(('data:', 'blob:')):
                self.external.append(url)
            return route.abort()
        self.served.append(path)
        common = {'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer'}
        if path in ('/', '/index', '/index.html'):
            return route.fulfill(status=200, body=self.html, headers=dict(common, **{
                'Content-Type': 'text/html; charset=utf-8', 'Content-Security-Policy': self.csp}))
        f = os.path.normpath(os.path.join(self.base, path.lstrip('/')))
        if f.startswith(os.path.normpath(self.base)) and os.path.isfile(f):
            ext = os.path.splitext(f)[1].lower()
            return route.fulfill(status=200, body=read(f, 'rb'),
                                 headers=dict(common, **{'Content-Type': TYPES.get(ext, 'application/octet-stream')}))
        return route.fulfill(status=404, body=b'not in preview', headers={'Content-Type': 'text/plain'})


INIT = r"""
(() => {
  const cfg = %s;
  if (!cfg.intro) try { sessionStorage.setItem('zotheos_intro_seen', '1'); } catch (e) {}
  // Haptics recorder: the route's navigator.vibrate calls are logged (time, pattern, user activation), never sent.
  window.__vib = [];
  try { Object.defineProperty(Navigator.prototype, 'vibrate', {configurable: true, writable: true, value: function (p) {
    window.__vib.push([Math.round(performance.now()), p, !!(navigator.userActivation && navigator.userActivation.hasBeenActive)]); return true; }}); } catch (e) {}
  try {
    if (cfg.theme) localStorage.setItem('zotheos_landing_theme', cfg.theme); else localStorage.removeItem('zotheos_landing_theme');
    localStorage.setItem('zotheos_motion', cfg.motion);
  } catch (e) {}
  window.__cspv = [];
  document.addEventListener('securitypolicyviolation', e => window.__cspv.push(e.violatedDirective + ' ' + e.blockedURI + ' ' + (e.sample || '')));
  window.__lt = [];
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) window.__lt.push([Math.round(e.startTime), Math.round(e.duration)]); }).observe({type: 'longtask', buffered: true}); } catch (e) {}
  // Layout shifts without recent input (the 4.9 budget: 0 caused by the stage), with the shifted nodes named.
  window.__ls = [];
  try { new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__ls.push({t: Math.round(e.startTime), v: +e.value.toFixed(5),
    src: (e.sources || []).map(s => { const n = s.node && (s.node.nodeType === 1 ? s.node : s.node.parentElement), R = document.getElementById('councilRoute');
      return (n ? (n.id || n.tagName.toLowerCase() + '.' + (n.getAttribute('class') || '')) : '?') + (R && n && R.contains(n) ? ' [route]' : ''); })}); })
    .observe({type: 'layout-shift', buffered: true}); } catch (e) {}
})();
"""


def launch(p, headed=False):
    return p.chromium.launch(channel='chrome', headless=not headed, args=['--mute-audio'])


def open_page(browser, device='desktop', theme='default', motion='living', reduce=False, built=None, viewport=None, intro=False):
    built = built or build_page()
    opts = dict(DEVICES[device])
    if viewport:
        opts['viewport'] = viewport
    if reduce:
        opts['reduced_motion'] = 'reduce'
    ctx = browser.new_context(**opts)
    srv = Server(built['html'], built['csp'])
    ctx.route('**/*', srv)
    ctx.add_init_script(INIT % json.dumps({'theme': '' if theme == 'default' else theme, 'motion': motion, 'intro': intro}))
    page = ctx.new_page()
    logs = []
    page.on('console', lambda m: logs.append(m.type + ': ' + m.text))
    page.on('pageerror', lambda e: logs.append('pageerror: ' + str(e)))
    page.goto(ORIGIN + '/', wait_until='load')
    try:
        if page.locator('#introGate').is_visible():
            page.click('#gateQuiet')
    except Exception:
        pass
    page.wait_for_function("() => !document.body.classList.contains('page-loading')", timeout=20000)
    page.wait_for_timeout(400)
    return ctx, page, srv, logs


HOLD_JS = ("() => { const R = document.getElementById('councilRoute');"
           " R.dispatchEvent(new CustomEvent('cr:seek', {detail: 0}));"
           " document.getElementById('crCtl').dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowLeft', bubbles: true})); }")


def hold(page):
    """Hold the route at rest as a visitor's step would (no autoplay until Play), without a user activation: the capture
    hook seeks to the first beat, then one step back paints the rest diagram."""
    page.evaluate(HOLD_JS)


def to_route(page, settle=1300, held=True):
    """Scroll the route block to the top of the viewport (below the fixed header) and let the card reveal. With held
    (the default) the route is first held at rest, so it does not start on its own; held=False lets it autoplay."""
    if held:
        hold(page)
    page.evaluate("() => { const r = document.getElementById('councilRoute'); r.scrollIntoView({block: 'start', behavior: 'instant'}); }")
    page.wait_for_timeout(settle)


STATE_JS = r"""() => {
  const R = document.getElementById('councilRoute'), S = document.getElementById('crStage');
  const inR = a => { const t = a.effect && a.effect.target; return !!(t && R.contains(t)); };
  const all = document.getAnimations();
  const sr = S.getBoundingClientRect(), rr = R.getBoundingClientRect();
  return {hidden: R.hidden, b: R.getAttribute('data-b'), p: R.getAttribute('data-p'),
    caption: document.getElementById('crCap').textContent, live: document.getElementById('crCap').getAttribute('aria-live'),
    status: document.querySelector('.cr-st').innerText, playHidden: document.getElementById('crPlay').hidden,
    transcriptOpen: document.getElementById('crText').open, layout: S.className,
    stageAnims: all.filter(inR).length, runningStageAnims: all.filter(a => inR(a) && a.playState === 'running').length,
    stage: [Math.round(sr.left), Math.round(sr.top), Math.round(sr.width), Math.round(sr.height)],
    route: [Math.round(rr.left), Math.round(rr.top), Math.round(rr.width), Math.round(rr.height)],
    scrollW: document.documentElement.scrollWidth, innerW: innerWidth, cspv: window.__cspv.slice()};
}"""

# Text over lines: sample every drawn stroke (lines, frames, enclosure, circles) and test it against every label box.
COLLIDE_JS = r"""() => {
  const S = document.getElementById('crStage'), out = [];
  const labels = [...S.querySelectorAll('.cr-l')].filter(l => getComputedStyle(l).opacity !== '0' && l.offsetParent)
    .map(l => ({k: l.dataset.k, r: l.getBoundingClientRect()}));
  for (let i = 0; i < labels.length; i++) for (let j = i + 1; j < labels.length; j++) {
    const a = labels[i].r, b = labels[j].r;
    if (a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom) out.push(['label', labels[i].k, labels[j].k]);
  }
  const shapes = [...S.querySelectorAll('svg path, svg rect, svg circle')].filter(s => !s.closest('mask') && !s.classList.contains('hn') && !s.classList.contains('h') && !(s.parentNode && s.parentNode.classList && s.parentNode.classList.contains('hn')));
  for (const s of shapes) {
    let n; try { n = s.getTotalLength(); } catch (e) { continue; }
    const m = s.getScreenCTM(); if (!m) continue;
    const cls = s.getAttribute('class') || s.tagName;
    for (let t = 0; t <= n; t += 2) {
      const p = s.getPointAtLength(t), x = m.a * p.x + m.c * p.y + m.e, y = m.b * p.x + m.d * p.y + m.f;
      for (const l of labels) {
        const r = l.r;
        if (x > r.left - 1 && x < r.right + 1 && y > r.top - 1 && y < r.bottom + 1) { out.push(['line', l.k, cls]); break; }
      }
    }
  }
  const seen = new Set();
  return out.filter(o => { const k = o.join('|'); if (seen.has(k)) return false; seen.add(k); return true; });
}"""


def shot(page, path, clip_route=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if clip_route:
        page.locator('#councilRoute').screenshot(path=path)
    else:
        page.screenshot(path=path)
    return path


def seek(page, t):
    page.evaluate("t => document.getElementById('councilRoute').dispatchEvent(new CustomEvent('cr:seek', {detail: t}))", t)
    page.wait_for_timeout(60)


def run_shots(args):
    from playwright.sync_api import sync_playwright
    built = build_page()
    out = args.out
    report = {'build': built['report'], 'runs': []}
    themes = THEMES if args.themes == 'all' else args.themes.split(',')
    motions = args.motions.split(',')
    devices = args.devices.split(',')
    with sync_playwright() as p:
        b = launch(p, args.headed)
        for dev in devices:
            for theme in themes:
                for motion in motions:
                    ctx, page, srv, logs = open_page(b, dev, theme, motion, built=built)
                    to_route(page)
                    tag = '%s_%s_%s' % (dev, theme, motion)
                    run = {'tag': tag, 'beats': [], 'collisions': {}}
                    run['rest'] = page.evaluate(STATE_JS)
                    shot(page, os.path.join(out, tag + '_view_rest.png'), clip_route=False)
                    shot(page, os.path.join(out, tag + '_b0.png'))
                    run['collisions']['b0'] = page.evaluate(COLLIDE_JS)
                    full = theme == 'default' and motion == 'living'
                    for k in range(1, 8):
                        if not full and k not in (4, 7):
                            page.click('#crNext')
                            continue
                        page.click('#crNext')
                        page.wait_for_timeout(50)
                        st = page.evaluate(STATE_JS)
                        run['beats'].append({'k': k, 'b': st['b'], 'caption': st['caption'], 'anims': st['stageAnims']})
                        shot(page, os.path.join(out, '%s_b%d.png' % (tag, k)))
                        if full:
                            run['collisions']['b%d' % k] = page.evaluate(COLLIDE_JS)
                    if full and motion != 'still':
                        starts = page.evaluate("() => null")
                        for t in args.mid:
                            seek(page, t)
                            st = page.evaluate(STATE_JS)
                            shot(page, os.path.join(out, '%s_t%05.2f.png' % (tag, t)))
                            run.setdefault('mid', []).append({'t': t, 'b': st['b'], 'anims': st['stageAnims'],
                                                              'running': st['runningStageAnims']})
                    run['external'] = srv.external
                    run['errors'] = [l for l in logs if l.startswith(('error', 'pageerror'))]
                    run['final'] = page.evaluate(STATE_JS)
                    report['runs'].append(run)
                    print(tag, 'rest', run['rest']['layout'], run['rest']['stage'], 'collisions',
                          sum(len(v) for v in run['collisions'].values()), 'errors', len(run['errors']),
                          'external', len(srv.external), 'cspv', len(run['final']['cspv']))
                    ctx.close()
        b.close()
    with open(os.path.join(out, 'shots_report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)
    return report


FIT_JS = r"""() => {
  const v = el => { if (!el) return null; const r = el.getBoundingClientRect(); return [Math.round(r.top), Math.round(r.bottom)]; };
  const cta = document.querySelector('.mobile-cta'), cr = cta && cta.getBoundingClientRect();
  const hdr = document.getElementById('header').getBoundingClientRect();
  const acts = [...document.querySelectorAll('#crSvg .h, #crSvg .hn')].filter(p => parseFloat(getComputedStyle(p).opacity) > 0.5).map(v);
  const cap = document.getElementById('crCap'), rg = document.createRange();
  rg.selectNodeContents(cap);
  const ct = rg.getBoundingClientRect();
  return {innerH: innerHeight, header_bottom: Math.round(hdr.bottom),
    sticky_top: cta && cta.classList.contains('visible') && getComputedStyle(cta).display !== 'none' ? Math.round(cr.top) : null,
    pause: v(document.getElementById('crPlay')), p: document.getElementById('councilRoute').dataset.p,
    stage: v(document.getElementById('crStage')), caption_text: [Math.round(ct.top), Math.round(ct.bottom)],
    caption_box: v(document.getElementById('crCb')), active: acts, scrollY: Math.round(scrollY), beat: document.getElementById('councilRoute').dataset.b};
}"""

FIT_TOPS = {'phone': (100, 150, 200, 250, 300, 350, 389, 500, 650), 'desktop': (150, 300, 400, 440, 480, 505, 700)}


def fit_case(b, built, dev, theme, y, out=None, viewport=None, tag=None):
    """Scroll so the stage top sits at y, press Play there (tap on the phone), read what is visible 2.5 s later. The
    route is held at rest first, so the press (not an autoplay) starts it from every position."""
    ctx, page, srv, logs = open_page(b, dev, theme, 'living', built=built, viewport=viewport)
    hold(page)
    page.evaluate("y => { const s = document.getElementById('crStage'); window.scrollBy({top: s.getBoundingClientRect().top - y, behavior: 'instant'}); }", y)
    page.wait_for_timeout(900)
    before = page.evaluate(FIT_JS)
    if dev == 'phone':
        page.locator('#crPlay').tap()
    else:
        page.locator('#crPlay').click()
    page.wait_for_timeout(2500)
    a = page.evaluate(FIT_JS)
    top = max(a['header_bottom'], 0)
    bot = a['sticky_top'] if a['sticky_top'] is not None else a['innerH']
    vis = lambda r: bool(r and r[0] >= top and r[1] <= bot)
    rec = {'device': dev, 'theme': theme, 'viewport': viewport, 'stage_top_before_press': before['stage'][0], 'band': [top, bot],
           'scrolled_by_play': a['scrollY'] - before['scrollY'], 'playing': a['p'] == 'pause', 'beat': a['beat'],
           'pause': a['pause'], 'stage': a['stage'], 'caption_text': a['caption_text'], 'caption_box': a['caption_box'],
           'pause_visible': vis(a['pause']), 'caption_visible': vis(a['caption_text']), 'caption_box_visible': vis(a['caption_box']),
           'active_visible': any(vis(r) for r in a['active'])}
    rec['pass'] = rec['playing'] and rec['pause_visible'] and rec['caption_visible'] and rec['caption_box_visible'] and rec['active_visible']
    if out:
        page.screenshot(path=os.path.join(out, tag or 'fit_%s_%s_stage_at_%d.png' % (dev, theme, y)))
    ctx.close()
    return rec


def run_fit_cases(b, built, out, themes=('default', 'codex')):
    fit_dir = os.path.join(out, 'fit')
    os.makedirs(fit_dir, exist_ok=True)
    cases = []
    for dev in ('phone', 'desktop'):
        for theme in themes:
            for y in FIT_TOPS[dev]:
                c = fit_case(b, built, dev, theme, y, fit_dir)
                cases.append(c)
                print('fit', dev, theme, 'stage top', y, 'scrolled', c['scrolled_by_play'], 'band', c['band'], 'pause', c['pause'],
                      'caption', c['caption_text'], 'box', c['caption_box'], 'pass', c['pass'], flush=True)
    return cases


def run_fit(args):
    from playwright.sync_api import sync_playwright
    built = build_page()
    with sync_playwright() as p:
        b = launch(p, args.headed)
        res = {'build': built['report'], 'cases': run_fit_cases(b, built, args.out)}
        b.close()
    res['pass'] = all(c['pass'] for c in res['cases'])
    with open(os.path.join(args.out, 'fit_report.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    return {'pass': res['pass'], 'failed': [(c['device'], c['theme'], c['stage_top_before_press']) for c in res['cases'] if not c['pass']]}


# Route playback state in the real page: the run's clock, the controls, CC, the Audio slot and the haptics log.
PLAY_JS = r"""() => {
  const R = document.getElementById('councilRoute'), S = document.getElementById('crStage');
  const a = document.getAnimations().filter(x => x.effect && x.effect.target && R.contains(x.effect.target) && x.playState !== 'idle');
  const sr = S.getBoundingClientRect(), vis = Math.max(0, Math.min(sr.bottom, innerHeight) - Math.max(sr.top, 0)) / sr.height;
  const box = id => { const e = document.getElementById(id); if (!e || !e.offsetParent) return null; const r = e.getBoundingClientRect();
    return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; };
  return {p: R.dataset.p, b: R.dataset.b, t: a.length ? Math.round(a[0].currentTime) : null,
    running: a.filter(x => x.playState === 'running').length, stageAnims: a.length, inView: +vis.toFixed(2),
    scrollY: Math.round(scrollY), vib: window.__vib.length, vibLog: window.__vib.slice(-3),
    active: !!(navigator.userActivation && navigator.userActivation.hasBeenActive),
    cc: document.getElementById('crCc').getAttribute('aria-pressed'), cb: getComputedStyle(document.getElementById('crCb')).display,
    caption: document.getElementById('crCap').textContent, status: document.querySelector('.cr-st').innerText,
    sndHidden: document.getElementById('crSnd').hidden, sndShown: !!document.getElementById('crSnd').offsetParent,
    playHidden: document.getElementById('crPlay').hidden, transcriptOpen: document.getElementById('crText').open,
    motion: document.documentElement.dataset.motion, audioEls: document.querySelectorAll('#councilRoute audio').length,
    buttons: {play: box('crPlay'), prev: box('crPrev'), next: box('crNext'), cc: box('crCc'), snd: box('crSnd')},
    scrollW: document.documentElement.scrollWidth, innerW: innerWidth, cspv: window.__cspv.slice()};
}"""


def _at_ratio(page, r):
    """Scroll so that the top fraction r of the stage shows at the bottom of the viewport; returns the scroll position."""
    return page.evaluate("r => { const s = document.getElementById('crStage').getBoundingClientRect();"
                         " window.scrollBy({top: s.top - (innerHeight - r * s.height), behavior: 'instant'}); return Math.round(scrollY); }", r)


def _view(page):
    """The whole stage in view (the route block at the top, below the fixed header); returns the scroll position."""
    return page.evaluate("() => { document.getElementById('councilRoute').scrollIntoView({block: 'start', behavior: 'instant'});"
                         " return Math.round(scrollY); }")


def _away(page):
    page.evaluate("() => window.scrollTo({top: 0, behavior: 'instant'})")


def _tab(page, hidden):
    page.evaluate("h => { Object.defineProperty(document, 'hidden', {configurable: true, get: () => h});"
                  " Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => h ? 'hidden' : 'visible'});"
                  " document.dispatchEvent(new Event('visibilitychange')); }", hidden)


def _press(page, sel, dev):
    if dev == 'phone':
        page.locator(sel).tap()
    else:
        page.locator(sel).click()


def _check(rec, name, ok):
    rec.setdefault('checks', {})[name] = bool(ok)


def _playback_living(b, built, dev, motion='living'):
    """Autoplay on view, pause and resume by view and tab, explicit Pause respected, CC, Audio slot, haptics."""
    ctx, page, srv, logs = open_page(b, dev, 'default', motion, built=built)
    st = lambda: page.evaluate(PLAY_JS)
    r = {'device': dev, 'motion': motion}
    r['top'] = st()
    page.wait_for_timeout(1500)
    r['top_later'] = st()
    _check(r, 'no autoplay out of view', r['top']['stageAnims'] == 0 and r['top_later']['stageAnims'] == 0 and r['top_later']['p'] == 'play')
    _at_ratio(page, 0.45)
    page.wait_for_timeout(900)
    r['ratio_45'] = st()
    _check(r, 'no autoplay under 60% in view', r['ratio_45']['stageAnims'] == 0)
    y = _at_ratio(page, 0.75)
    page.wait_for_timeout(1200)
    r['ratio_75'] = st()
    _check(r, 'autoplays at 60% or more in view', r['ratio_75']['p'] == 'pause' and r['ratio_75']['running'] > 0)
    _check(r, 'autoplay does not scroll', r['ratio_75']['scrollY'] == y)
    # page.evaluate grants user activation, so the pulse-before-interaction rule is proven by _activation instead.
    _view(page)
    page.wait_for_timeout(1500)
    r['in_view'] = st()
    _away(page)
    page.wait_for_timeout(700)
    r['away'] = st()
    page.wait_for_timeout(1500)
    r['away_later'] = st()
    _check(r, 'pauses out of view', r['away']['p'] == 'play' and r['away']['running'] == 0 and r['away']['t'] == r['away_later']['t'])
    _view(page)
    page.wait_for_timeout(1000)
    r['back'] = st()
    _check(r, 'resumes back in view, where it stopped', r['back']['p'] == 'pause' and r['back']['t'] is not None and r['back']['t'] >= r['away']['t'])
    _tab(page, True)
    page.wait_for_timeout(400)
    r['tab_hidden'] = st()
    _tab(page, False)
    page.wait_for_timeout(600)
    r['tab_shown'] = st()
    _check(r, 'a hidden tab pauses and the tab shown again resumes', r['tab_hidden']['p'] == 'play' and r['tab_hidden']['running'] == 0 and r['tab_shown']['p'] == 'pause')
    v0 = st()['vib']
    _press(page, '#crPlay', dev)
    page.wait_for_timeout(300)
    r['paused_by_visitor'] = st()
    _check(r, 'Pause pauses, with one pulse', r['paused_by_visitor']['p'] == 'play' and r['paused_by_visitor']['vib'] == v0 + 1)
    t = r['paused_by_visitor']['t']
    _away(page)
    page.wait_for_timeout(600)
    _view(page)
    page.wait_for_timeout(1000)
    _tab(page, True)
    _tab(page, False)
    page.wait_for_timeout(1000)
    r['held'] = st()
    _check(r, 'an explicit Pause is respected (scroll, view, tab)', r['held']['p'] == 'play' and r['held']['running'] == 0 and r['held']['t'] == t)
    _press(page, '#crPlay', dev)
    page.wait_for_timeout(400)
    r['played_by_visitor'] = st()
    _check(r, 'Play resumes from the pause', r['played_by_visitor']['p'] == 'pause' and r['played_by_visitor']['t'] >= t)
    v1 = r['played_by_visitor']['vib']
    b0 = r['played_by_visitor']['b']
    page.wait_for_function("b => document.getElementById('councilRoute').dataset.b !== b", arg=b0, timeout=9000)
    page.wait_for_timeout(100)
    r['after_beat'] = st()
    _check(r, 'a beat change pulses once (after interaction), 8 to 12 ms',
           r['after_beat']['vib'] == v1 + 1 and all(x[1] in (8, 9, 10, 11, 12) for x in page.evaluate('() => window.__vib')))
    _press(page, '#crCc', dev)
    page.wait_for_timeout(200)
    r['cc_off'] = st()
    _press(page, '#crCc', dev)
    page.wait_for_timeout(200)
    r['cc_on'] = st()
    _check(r, 'CC toggles the caption line; the run goes on', r['cc_off']['cc'] == 'false' and r['cc_off']['cb'] == 'none'
           and r['cc_on']['cc'] == 'true' and r['cc_on']['cb'] != 'none' and r['cc_on']['p'] == 'pause')
    _check(r, 'Audio slot hidden, no audio element', r['cc_on']['sndHidden'] and not r['cc_on']['sndShown'] and r['cc_on']['audioEls'] == 0)
    page.evaluate("() => localStorage.setItem('zotheos_haptics', 'off')")
    v2 = st()['vib']
    b1 = st()['b']
    page.wait_for_function("b => document.getElementById('councilRoute').dataset.b !== b", arg=b1, timeout=9000)
    _press(page, '#crPlay', dev)
    _press(page, '#crPlay', dev)
    page.wait_for_timeout(200)
    r['haptics_off'] = st()
    _check(r, 'haptics off by preference', r['haptics_off']['vib'] == v2)
    page.evaluate("() => localStorage.removeItem('zotheos_haptics')")
    bt = r['haptics_off']['buttons']
    r['layout'] = {'buttons': bt, 'one_row': len({x[1] for x in (bt['play'], bt['prev'], bt['next']) if x}) == 1,
                   'min_target': min(min(x[2], x[3]) for x in bt.values() if x), 'scrollW': r['haptics_off']['scrollW'], 'innerW': r['haptics_off']['innerW']}
    _check(r, 'controls at least 44 x 44, Play row on one line, no horizontal scroll',
           r['layout']['min_target'] >= 44 and r['layout']['one_row'] and r['layout']['scrollW'] <= r['layout']['innerW'])
    if dev == 'desktop' and motion == 'living':
        page.click('#appearanceBtn')
        page.wait_for_timeout(300)
        page.click('#apMotionRow [data-mode="still"]')
        page.wait_for_timeout(500)
        r['to_still'] = st()
        _check(r, 'Motion to Still stops the run and hides Play', r['to_still']['stageAnims'] == 0 and r['to_still']['playHidden'])
        # Still changes the page's height above the route (the landing is shorter in Still), so bring it back first.
        _view(page)
        page.wait_for_timeout(800)
        r['still_in_view'] = st()
        page.click('#apMotionRow [data-mode="calm"]')
        page.wait_for_timeout(300)
        _view(page)
        page.wait_for_timeout(1000)
        r['to_calm'] = st()
        _check(r, 'Calm in view plays on', r['still_in_view']['stageAnims'] == 0 and r['to_calm']['p'] == 'pause' and r['to_calm']['running'] > 0)
        page.keyboard.press('Escape')
        page.focus('#crNext')
        page.keyboard.press('ArrowRight')
        b2 = int(st()['b'])
        page.keyboard.press('ArrowRight')
        r['arrows'] = st()
        _check(r, 'arrow keys step inside the group and hold', int(r['arrows']['b']) == b2 + 1 and r['arrows']['stageAnims'] == 0)
    r['errors'] = [l for l in logs if l.startswith(('error', 'pageerror'))]
    r['warnings'] = sorted(set(l[:200] for l in logs if l.startswith('warning')))
    r['external'] = srv.external
    r['cspv'] = page.evaluate('() => window.__cspv')
    _check(r, '0 console errors, 0 CSP violations, 0 external requests', not r['errors'] and not r['cspv'] and not r['external'])
    ctx.close()
    return r


def _playback_still(b, built, dev, reduce=False):
    ctx, page, srv, logs = open_page(b, dev, 'default', 'living' if reduce else 'still', reduce=reduce, built=built)
    st = lambda: page.evaluate(PLAY_JS)
    r = {'device': dev, 'still': 'OS reduced motion over Living' if reduce else 'Still chosen'}
    _view(page)
    page.wait_for_timeout(2000)
    r['in_view'] = st()
    _check(r, 'no autoplay, Play hidden, transcript open', r['in_view']['stageAnims'] == 0 and r['in_view']['playHidden']
           and r['in_view']['transcriptOpen'] and r['in_view']['p'] == 'play')
    _press(page, '#crNext', dev)
    _press(page, '#crNext', dev)
    page.wait_for_timeout(300)
    r['stepped'] = st()
    page.evaluate("() => document.getElementById('councilRoute').dispatchEvent(new CustomEvent('cr:seek', {detail: 20}))")
    _away(page)
    _view(page)
    page.wait_for_timeout(1500)
    r['after'] = st()
    _check(r, 'the stepper steps with 0 animations and no pulse', r['stepped']['b'] == '2' and r['after']['stageAnims'] == 0 and r['after']['vib'] == 0)
    _press(page, '#crCc', dev)
    r['cc_off'] = st()
    _check(r, 'CC works in Still', r['cc_off']['cc'] == 'false' and r['cc_off']['cb'] == 'none')
    r['errors'] = [l for l in logs if l.startswith(('error', 'pageerror'))]
    r['external'] = srv.external
    r['cspv'] = page.evaluate('() => window.__cspv')
    _check(r, '0 console errors, 0 CSP violations, 0 external requests', not r['errors'] and not r['cspv'] and not r['external'])
    ctx.close()
    return r


def _intro(b, built):
    """A first visit (no intro seen this session): the full intro runs; the route never starts under the overlay, even
    with the stage scrolled into view behind it, and starts once the overlay is gone."""
    ctx = b.new_context(**DEVICES['desktop'])
    srv = Server(built['html'], built['csp'])
    ctx.route('**/*', srv)
    ctx.add_init_script(INIT % json.dumps({'theme': '', 'motion': 'living', 'intro': True}))
    page = ctx.new_page()
    logs = []
    page.on('console', lambda m: logs.append(m.type + ': ' + m.text))
    page.on('pageerror', lambda e: logs.append('pageerror: ' + str(e)))
    page.goto(ORIGIN + '/', wait_until='load')
    st = lambda: page.evaluate(PLAY_JS)
    gone = "() => { const o = document.getElementById('introOverlay'); return !o || o.classList.contains('dismissed'); }"
    r = {'overlay_up_at_start': not page.evaluate(gone)}
    page.evaluate("() => { document.getElementById('crStage').scrollIntoView({block: 'center', behavior: 'instant'}); }")
    under, gate = [], False
    for _ in range(80):
        page.wait_for_timeout(250)
        if page.evaluate(gone):
            break
        s = st()
        under.append([s['inView'], s['stageAnims']])
        if not gate and page.locator('#introGate').is_visible():
            page.click('#gateQuiet')
            gate = True
    r['gate_clicked'] = gate
    r['samples_under_overlay'] = len(under)
    r['max_in_view_under_overlay'] = max([u[0] for u in under] or [0])
    r['route_anims_under_overlay'] = max([u[1] for u in under] or [0])
    page.wait_for_function(gone, timeout=30000)
    page.wait_for_timeout(800)
    _view(page)
    page.wait_for_timeout(1500)
    r['after_intro'] = st()
    _check(r, 'never under the intro, plays once it is gone', r['overlay_up_at_start'] and len(under) > 0
           and r['route_anims_under_overlay'] == 0 and r['after_intro']['p'] == 'pause')
    r['errors'] = [l for l in logs if l.startswith(('error', 'pageerror'))]
    r['cspv'] = page.evaluate('() => window.__cspv')
    _check(r, '0 console errors, 0 CSP violations', not r['errors'] and not r['cspv'])
    ctx.close()
    return r


def _matrix(b, built):
    """Every theme x Living, Calm and Still x desktop and phone: scrolled into view, the route autoplays outside Still."""
    out = []
    for dev in ('desktop', 'phone'):
        for theme in THEMES:
            for motion in ('living', 'calm', 'still'):
                ctx, page, srv, logs = open_page(b, dev, theme, motion, built=built)
                _view(page)
                page.wait_for_timeout(1300)
                s = page.evaluate(PLAY_JS)
                rec = {'device': dev, 'theme': theme, 'motion': motion, 'p': s['p'], 'running': s['running'], 'stageAnims': s['stageAnims'],
                       'playHidden': s['playHidden'], 'errors': [l for l in logs if l.startswith(('error', 'pageerror'))],
                       'cspv': s['cspv'], 'external': srv.external, 'scrollW': s['scrollW'], 'innerW': s['innerW']}
                rec['pass'] = ((s['p'] == 'pause' and s['running'] > 0) if motion != 'still' else (s['stageAnims'] == 0 and s['playHidden'])) \
                    and not rec['errors'] and not rec['cspv'] and not rec['external'] and s['scrollW'] <= s['innerW']
                out.append(rec)
                print('matrix', dev, theme, motion, 'p', s['p'], 'running', s['running'], 'pass', rec['pass'], flush=True)
                ctx.close()
    return out


PROBE_INIT = r"""(() => {
  const cfg = %s;
  try { sessionStorage.setItem('zotheos_intro_seen', '1'); localStorage.setItem('zotheos_motion', cfg.motion); } catch (e) {}
  const say = (k, v) => console.log('PROBE ' + JSON.stringify([k, Math.round(performance.now()), v]));
  try { Object.defineProperty(Navigator.prototype, 'vibrate', {configurable: true, writable: true, value: function (p) {
    say('vibrate', {ms: p, active: navigator.userActivation.hasBeenActive}); return true; }}); } catch (e) {}
  document.addEventListener('securitypolicyviolation', e => say('csp', e.violatedDirective));
  addEventListener('DOMContentLoaded', () => {
    const R = document.getElementById('councilRoute');
    say('activation at load', navigator.userActivation.hasBeenActive);
    new MutationObserver(() => say('route', {b: R.dataset.b, p: R.dataset.p, active: navigator.userActivation.hasBeenActive}))
      .observe(R, {attributes: true, attributeFilter: ['data-b', 'data-p']});
  });
})();"""


def _activation(b, built, dev):
    """Haptics before any interaction. Playwright's page.evaluate runs as a user gesture (it grants sticky user
    activation), so this probe never evaluates in the page: the page reports through console.log, and the visitor only
    scrolls with the mouse wheel (not an activating input) until the route autoplays, then clicks Pause once."""
    events = []
    ctx = b.new_context(**DEVICES[dev])
    ctx.route('**/*', Server(built['html'], built['csp']))
    ctx.add_init_script(PROBE_INIT % json.dumps({'motion': 'living'}))
    page = ctx.new_page()
    page.on('console', lambda m: events.append(json.loads(m.text[6:])) if m.text.startswith('PROBE ') else None)
    page.goto(ORIGIN + '/', wait_until='load')
    page.wait_for_timeout(2500)
    started = False
    for _ in range(120):
        page.mouse.move(200, 400)
        page.mouse.wheel(0, 300)
        page.wait_for_timeout(250)
        if any(e[0] == 'route' and e[2]['p'] == 'pause' for e in events):
            started = True
            break
    page.wait_for_timeout(7000)   # past one beat change while nobody has interacted
    before = [e for e in events if e[0] == 'vibrate']
    route_before = [e for e in events if e[0] == 'route']
    page.locator('#crPlay').click()   # the visitor's first press (Pause)
    page.wait_for_timeout(500)
    after = [e for e in events if e[0] == 'vibrate'][len(before):]
    r = {'device': dev, 'motion': 'activation', 'activation_at_load': [e[2] for e in events if e[0] == 'activation at load'],
         'autoplay_started_by_wheel': started, 'beats_before_press': [e[2]['b'] for e in route_before],
         'activation_during_autoplay': sorted({e[2]['active'] for e in route_before}), 'pulses_before_press': len(before),
         'pulses_on_first_press': [e[2] for e in after], 'csp': [e for e in events if e[0] == 'csp']}
    _check(r, 'autoplay by wheel scrolling, no pulse before any interaction, one 10 ms pulse on the first press',
           started and r['activation_during_autoplay'] == [False] and len(set(r['beats_before_press']) - {'0'}) >= 2
           and not before and len(after) == 1 and after[0][2]['ms'] == 10 and not r['csp'])
    ctx.close()
    return r


def run_checks(args):
    """Real-browser behaviour under the landing CSP (desktop and phone): autoplay on view in Living and Calm, never in
    Still or under OS reduced motion, pause and resume by view and tab, an explicit Pause respected, CC, the hidden Audio
    slot, guarded haptics (navigator.vibrate is replaced by a recorder), the intro, every theme and motion, fit, no-JS,
    CSP-blocked script, height added."""
    from playwright.sync_api import sync_playwright
    built = build_page()
    res = {'build': built['report']}
    with sync_playwright() as p:
        b = launch(p, args.headed)
        res['playback'] = [_playback_living(b, built, 'desktop', 'living'), _playback_living(b, built, 'desktop', 'calm'),
                           _playback_living(b, built, 'phone', 'living')]
        res['still'] = [_playback_still(b, built, 'desktop'), _playback_still(b, built, 'desktop', reduce=True),
                        _playback_still(b, built, 'phone'), _playback_still(b, built, 'phone', reduce=True)]
        res['activation'] = [_activation(b, built, 'desktop'), _activation(b, built, 'phone')]
        for r in res['playback'] + res['still'] + res['activation']:
            print(r['device'], r.get('motion') or r.get('still'), json.dumps(r['checks']), flush=True)
        res['intro'] = _intro(b, built)
        print('intro', json.dumps(res['intro']['checks']), flush=True)
        res['matrix'] = _matrix(b, built)
        # Fit (4.8): Play pressed where the visitor finds it (route held at rest first), desktop and phone with the
        # sticky release bar showing. Pause, the caption, the reserved caption box and an active stroke visible together.
        res['fit'] = run_fit_cases(b, built, args.out)
        res['phone_fit'] = {'pass': all(c['pass'] for c in res['fit'] if c['device'] == 'phone')}
        res['desktop_fit'] = {'pass': all(c['pass'] for c in res['fit'] if c['device'] == 'desktop')}
        # No JavaScript: the stage stays hidden, the Fusion figure is unchanged and shown.
        ctx = b.new_context(**DEVICES['desktop'], java_script_enabled=False)
        srv = Server(built['html'], built['csp'])
        ctx.route('**/*', srv)
        page = ctx.new_page()
        page.goto(ORIGIN + '/', wait_until='load')
        res['no_js'] = {'stage_hidden': page.locator('#councilRoute').is_hidden(),
                        'figure_visible_in_dom': page.locator('.fusion-fig').count() == 1}
        ctx.close()
        # CSP-blocked script (hash omitted): the stage stays hidden and the violation is reported.
        bad_csp = built['csp'].replace(' ' + built['script_hash'], '')
        ctx = b.new_context(**DEVICES['desktop'])
        srv = Server(built['html'].replace(built['script_hash'], ''), bad_csp)
        ctx.route('**/*', srv)
        ctx.add_init_script(INIT % json.dumps({'theme': '', 'motion': 'living', 'intro': False}))
        page = ctx.new_page()
        page.goto(ORIGIN + '/', wait_until='load')
        page.wait_for_timeout(1500)
        res['csp_blocked'] = page.evaluate("() => ({hidden: document.getElementById('councilRoute').hidden, cspv: window.__cspv.slice(0, 3)})")
        ctx.close()
        # Landing height added: base page vs page with the fragment, desktop and phone, at rest.
        base_built = build_page(with_fragment=False)
        heights = {}
        for dev in ('desktop', 'phone'):
            for mo in ('living', 'still'):
                for name, bb in (('base', base_built), ('route', built)):
                    ctx, page, srv, logs = open_page(b, dev, 'default', mo, built=bb)
                    page.wait_for_timeout(600)
                    heights['%s_%s_%s' % (dev, mo, name)] = page.evaluate('() => document.documentElement.scrollHeight')
                    if name == 'route':
                        heights['%s_%s_block' % (dev, mo)] = page.evaluate("() => Math.round(document.getElementById('councilRoute').getBoundingClientRect().height)")
                    ctx.close()
                heights['%s_%s_added' % (dev, mo)] = heights['%s_%s_route' % (dev, mo)] - heights['%s_%s_base' % (dev, mo)]
        res['heights'] = heights
        b.close()
    checks = {}
    for r in res['playback'] + res['still'] + res['activation'] + [res['intro']]:
        for k, v in r['checks'].items():
            checks['%s %s: %s' % (r.get('device', 'desktop'), r.get('motion') or r.get('still') or 'intro', k)] = v
    res['summary'] = {'checks_passed': sum(checks.values()), 'checks': len(checks),
                      'failed': [k for k, v in checks.items() if not v],
                      'matrix_passed': sum(m['pass'] for m in res['matrix']), 'matrix': len(res['matrix']),
                      'fit_passed': sum(c['pass'] for c in res['fit']), 'fit': len(res['fit']),
                      'no_js': res['no_js'], 'csp_blocked': res['csp_blocked'], 'heights': res['heights']}
    with open(os.path.join(args.out, 'checks_report.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    return res['summary']


def run_play(args):
    """One real-time run per device, started the way a visitor starts it: by scrolling the stage into view. Long tasks
    and layout shifts during play, captions in order, end state."""
    from playwright.sync_api import sync_playwright
    built = build_page()
    out = {}
    with sync_playwright() as p:
        b = launch(p, args.headed)
        for dev in args.devices.split(','):
            ctx, page, srv, logs = open_page(b, dev, 'default', 'living', built=built)
            page.evaluate("() => { window.__lt = []; window.__ls = []; window.__caps = []; const c = document.getElementById('crCap');"
                          " new MutationObserver(() => window.__caps.push([Math.round(performance.now()), c.getAttribute('aria-live'), c.textContent]))"
                          ".observe(c, {childList: true, characterData: true, subtree: true}); window.__t0 = performance.now(); }")
            to_route(page, 0, held=False)
            samples = []
            for i in range(46):
                page.wait_for_timeout(1000)
                samples.append(page.evaluate(STATE_JS))
            res = page.evaluate("() => ({lt: window.__lt, caps: window.__caps, t0: Math.round(window.__t0), layout_shifts: window.__ls})")
            if res['caps']:
                res['t0'] = res['caps'][0][0]   # the run's first caption: the moment autoplay started it
            res['layout_shift_total'] = round(sum(x['v'] for x in res['layout_shifts']), 5)
            res['layout_shifts_from_route'] = [x for x in res['layout_shifts'] if any('[route]' in s for s in x['src'])]
            res['end'] = page.evaluate(STATE_JS)
            res['beat_trace'] = [s['b'] for s in samples]
            res['max_stage_anims'] = max(s['stageAnims'] for s in samples)
            res['errors'] = [l for l in logs if l.startswith(('error', 'pageerror'))]
            res['external'] = srv.external
            out[dev] = res
            print(dev, 'captions at', [round((c[0] - res['t0']) / 1000, 2) for c in res['caps']], 'long tasks', res['lt'],
                  'layout shifts', res['layout_shifts'], 'end', res['end']['p'], res['end']['stageAnims'], flush=True)
            ctx.close()
        b.close()
    with open(os.path.join(args.out, 'play_report.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    return {d: {'layout_shift_total': r['layout_shift_total'], 'layout_shifts_from_route': r['layout_shifts_from_route'],
                'long_tasks': r['lt'], 'end_p': r['end']['p'],
                'captions_at_s': [round((c[0] - r['t0']) / 1000, 2) for c in r['caps']]} for d, r in out.items()}


PROFILE_JS = r"""() => {
  // Every visible, drawn stroke of the stage (rest lines, node frames, the enclosure, active strokes) as ordered
  // centre-line points in viewport device px, plus the visible band between the fixed header and the sticky bar.
  const S = document.getElementById('crStage'), dpr = devicePixelRatio, lines = [];
  const mk = document.querySelector('#crMk path');
  const opa = e => { let o = 1; for (let n = e; n && n !== S; n = n.parentNode) if (n.nodeType === 1) o *= parseFloat(getComputedStyle(n).opacity); return o; };
  for (const s of S.querySelectorAll('svg path, svg rect, svg circle')) {
    if (s.closest('mask') || s.classList.contains('dot') || s.classList.contains('bg')) continue;
    if (s.closest('g[mask]') && mk && parseFloat(getComputedStyle(mk).strokeDashoffset) > 0.5) continue;
    if (opa(s) < 0.99 || (parseFloat(getComputedStyle(s).strokeDashoffset) || 0) > 0.5) continue;
    const kind = s.classList.contains('h') || s.closest('.hn') ? 'active' : s.classList.contains('en') ? 'enclosure' : s.classList.contains('b') ? 'line' : 'node';
    let n; try { n = s.getTotalLength(); } catch (e) { continue; }
    const m = s.getScreenCTM(), pts = [];
    // dashed strokes (the enclosure, the tie): one point per user unit, so every dash period can be scored by its
    // best cross-section; solid strokes: about 60 points per stroke, at least 2 user units apart
    const dashed = s.classList.contains('en') || s.classList.contains('t');
    const period = dashed ? getComputedStyle(s).strokeDasharray.split(/[ ,]+/).map(parseFloat).filter(x => x > 0).reduce((a, b) => a + b, 0) : 0;
    const step = dashed ? 1 : Math.max(2, n / 60);
    for (let t = 1; t < n - 1; t += step) {
      const p = s.getPointAtLength(t);
      pts.push([(m.a * p.x + m.c * p.y + m.e) * dpr, (m.b * p.x + m.d * p.y + m.f) * dpr]);
    }
    lines.push({kind, cls: (s.getAttribute('class') || s.tagName) + ' ' + s.tagName.toLowerCase(), dashed, period, step,
      sw: parseFloat(getComputedStyle(s).strokeWidth) * Math.hypot(m.a, m.b) * dpr, stroke: getComputedStyle(s).stroke, pts});
  }
  const hdr = document.getElementById('header').getBoundingClientRect(), cta = document.querySelector('.mobile-cta');
  const bot = cta && cta.classList.contains('visible') && getComputedStyle(cta).display !== 'none' ? cta.getBoundingClientRect().top : innerHeight;
  return {lines, dpr, band: [Math.max(0, hdr.bottom) * dpr, bot * dpr]};
}"""

# The route's own HTML text, one record per rendered line box (Range client rects), in viewport device px.
# Method from the independent visual review (verify_visual/vv4.py).
TEXT_LINES_JS = r"""() => {
  const dpr = devicePixelRatio, out = [];
  const els = [['caption', document.getElementById('crCap')], ['summary', document.querySelector('#crText summary')]];
  for (const s of document.querySelectorAll('.cr-st > span')) if (getComputedStyle(s).display !== 'none') els.push(['status', s]);
  for (const b of document.querySelectorAll('.cr .cr-b')) if (!b.hidden) els.push(['button:' + b.id + (b.getAttribute('aria-disabled') === 'true' ? ' (aria-disabled)' : ''), b]);
  if (document.getElementById('crText').open) { let i = 0; for (const li of document.querySelectorAll('#crList li')) els.push(['li' + (++i), li]); els.push(['note', document.querySelector('#crText > p')]); }
  for (const l of document.querySelectorAll('#crStage .cr-l')) if (parseFloat(getComputedStyle(l).opacity) > .99) els.push(['label:' + l.dataset.k, l]);
  for (const [k, el] of els) {
    if (!el || !el.offsetParent) continue;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let n, i = 0;
    while ((n = walker.nextNode())) {
      if (!n.textContent.trim()) continue;
      const pe = n.parentElement;
      if (getComputedStyle(pe).display === 'none' || pe.closest('.sr-only')) continue;
      const rg = document.createRange(); rg.selectNodeContents(n);
      for (const r of rg.getClientRects()) {
        if (r.width < 4 || r.height < 4) continue;
        out.push({k, i: i++, color: getComputedStyle(pe).color, size: getComputedStyle(pe).fontSize, box: [r.left, r.top, r.right, r.bottom].map(v => Math.round(v * dpr))});
      }
    }
  }
  const hdr = document.getElementById('header').getBoundingClientRect(), cta = document.querySelector('.mobile-cta');
  const bot = cta && cta.classList.contains('visible') && getComputedStyle(cta).display !== 'none' ? cta.getBoundingClientRect().top : innerHeight;
  return {lines: out, band: [Math.max(0, hdr.bottom) * dpr, bot * dpr]};
}"""


def _lum(rgb):
    import numpy as np
    c = rgb.astype(float) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def _ratio(a, b):
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def stroke_profiles(L, line, dpr, band):
    """Stroke contrast against the LOCAL ground (review F2): at each centre-line point the ground is the median of a
    ring 6 to 10 CSS px around it (robust where another line crosses or a label sits near, unlike a cross-line profile,
    whose far window runs along a crossing line), and the stroke is the pixel furthest from that ground within half the
    stroke width plus 3 device px of the computed centre (the review instrument's window: at scroll offsets that are not
    whole device pixels the compositor snaps the page up to 2 device px away from the layout coordinates); the peak
    pixel of a thin antialiased line still counts against it. A dashed stroke is scored once per dash period by its
    best cross-section (a dash end is partial coverage by design). Points whose ring leaves the screenshot or the
    visible band (header, sticky bar) are skipped."""
    import math
    import numpy as np
    R = int(math.ceil(10 * dpr))
    yy, xx = np.mgrid[-R:R + 1, -R:R + 1]
    dist = np.hypot(yy, xx)
    ring, near = (dist >= 6 * dpr) & (dist <= 10 * dpr), dist <= line['sw'] / 2 + 3.0
    H, W = L.shape
    vals = []
    for x, y in line['pts']:
        cx, cy = int(math.floor(x)), int(math.floor(y))
        if cx - R < 0 or cx + R >= W or cy - R < band[0] or cy + R >= min(band[1], H):
            vals.append(None)
            continue
        patch = L[cy - R:cy + R + 1, cx - R:cx + R + 1]
        g = float(np.median(patch[ring]))
        s = patch[near]
        vals.append(_ratio(float(s[np.argmax(np.abs(s - g))]), g))
    if not line['dashed']:
        return [v for v in vals if v is not None]
    k = max(1, int(round(line['period'] / line['step'])))
    out = []
    for i in range(0, len(vals) - k + 1, k):   # whole dash periods only
        w = vals[i:i + k]
        if all(v is not None for v in w):
            out.append(max(w))
    return out


def text_lines(L, data):
    """Per rendered line box: ground = the box median, ink = the pixel at the 99th percentile of distance from it."""
    import numpy as np
    res = {}
    for ln in data['lines']:
        x0, y0, x1, y1 = ln['box']
        if y0 < data['band'][0] or y1 > data['band'][1] or x0 < 0 or x1 > L.shape[1] or y1 > L.shape[0]:
            continue
        patch = L[y0:y1, x0:x1]
        bg = float(np.median(patch))
        d = np.abs(patch - bg)
        r = _ratio(float(patch.flat[np.argsort(d.ravel())[int(d.size * 0.99)]]), bg)
        if ln['k'] not in res or r < res[ln['k']]['ratio']:
            res[ln['k']] = {'ratio': round(r, 2), 'line': ln['i'], 'size': ln['size'], 'color': ln['color'], 'ground_L': round(bg, 4)}
    return res


_BAND_BOTTOM = ("const cta = document.querySelector('.mobile-cta'), bot = cta && cta.classList.contains('visible') && "
                "getComputedStyle(cta).display !== 'none' ? cta.getBoundingClientRect().top : innerHeight;")
POSITIONS = {
    # the play position: the route block under the header, as Play's own scroll leaves it
    'play': "() => (document.getElementById('crRun') || document.getElementById('councilRoute')).scrollIntoView({block: 'start', behavior: 'instant'})",
    # the stage's bottom edge at the bottom of the visible band (the darker ground of the Codex and Ember page gradients)
    'stage_low': "() => { const s = document.getElementById('crStage').getBoundingClientRect(); " + _BAND_BOTTOM +
                 " window.scrollBy({top: s.bottom - bot + 4, behavior: 'instant'}); }",
    # the route's bottom edge (the transcript, when open) at the bottom of the visible band
    'low': "() => { const s = document.getElementById('councilRoute').getBoundingClientRect(); " + _BAND_BOTTOM +
           " window.scrollBy({top: s.bottom - bot + 4, behavior: 'instant'}); }",
}


def run_contrast(args):
    """Contrast measured from pixels against the local ground (4.12 item 4): strokes by cross-line profile (pass: the
    10th percentile of every stroke at 3:1 or more), the route's text by line box (pass: 4.5:1 or more; disabled
    buttons are reported, WCAG 1.4.3 exempts inactive controls). Rest and beat 4, every theme and motion mode, at the
    play position and two low positions. Page animations keep running (nothing is paused)."""
    import io
    import numpy as np
    from PIL import Image
    from playwright.sync_api import sync_playwright
    built = build_page(fragment_text=read(args.fragment) if args.fragment else None)
    res = []
    motions = ['living', 'calm', 'still'] if args.motions == 'living' else args.motions.split(',')
    themes = THEMES if args.themes in ('all', 'default') else args.themes.split(',')
    with sync_playwright() as p:
        b = launch(p, args.headed)
        for dev in args.devices.split(','):
            for theme in themes:
                for motion in motions:
                    ctx, page, srv, logs = open_page(b, dev, theme, motion, built=built)
                    to_route(page)
                    for beat in (0, 4):
                        while int(page.evaluate("() => document.getElementById('councilRoute').dataset.b")) < beat:
                            page.click('#crNext')
                        page.mouse.move(0, 0)
                        for pos, js in POSITIONS.items():
                            page.evaluate(js)
                            page.wait_for_timeout(350)
                            img = np.array(Image.open(io.BytesIO(page.screenshot())).convert('RGB'))
                            L = _lum(img)
                            geo = page.evaluate(PROFILE_JS)
                            out = {'device': dev, 'theme': theme, 'motion': motion, 'beat': beat, 'position': pos, 'strokes': {}, 'text': {}}
                            for ln in geo['lines']:
                                v = stroke_profiles(L, ln, geo['dpr'], geo['band'])
                                if len(v) < 3:
                                    continue
                                key = ln['kind'] + ': ' + ln['cls']
                                rec = {'n': len(v), 'min': round(min(v), 2), 'p10': round(float(np.percentile(v, 10)), 2),
                                       'p50': round(float(np.percentile(v, 50)), 2), 'below_3': round(float(np.mean(np.array(v) < 3)), 3),
                                       'width_device_px': round(ln['sw'], 2), 'stroke': ln['stroke']}
                                if key not in out['strokes'] or rec['p10'] < out['strokes'][key]['p10']:
                                    out['strokes'][key] = rec
                            out['text'] = text_lines(L, page.evaluate(TEXT_LINES_JS))
                            st = [v['p10'] for v in out['strokes'].values()]
                            tx = {k: v['ratio'] for k, v in out['text'].items() if 'aria-disabled' not in k}
                            out['min_stroke_p10'] = min(st) if st else None
                            out['min_stroke_sample'] = min(v['min'] for v in out['strokes'].values()) if st else None
                            out['min_text'] = min(tx.values()) if tx else None
                            out['disabled_buttons'] = {k: v['ratio'] for k, v in out['text'].items() if 'aria-disabled' in k}
                            out['pass'] = bool((not st or min(st) >= 3) and (not tx or min(tx.values()) >= 4.5))   # no stroke or text in the band: not applicable
                            out['worst_stroke'] = min(out['strokes'].items(), key=lambda kv: kv[1]['p10'])[0] if st else None
                            out['worst_text'] = min(tx.items(), key=lambda kv: kv[1])[0] if tx else None
                            res.append(out)
                            print(dev, theme, motion, 'b%d' % beat, pos, 'stroke p10 min', out['min_stroke_p10'], '(%s)' % out['worst_stroke'],
                                  'sample min', out['min_stroke_sample'], '| text min', out['min_text'], '(%s)' % out['worst_text'],
                                  '| disabled', out['disabled_buttons'], '| pass', out['pass'], flush=True)
                    ctx.close()
        b.close()
    with open(os.path.join(args.out, 'contrast_report.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, indent=1)
    return {'states': len(res), 'pass': all(r['pass'] for r in res),
            'failed': [(r['device'], r['theme'], r['motion'], r['beat'], r['position'], r['worst_stroke'], r['min_stroke_p10'],
                        r['worst_text'], r['min_text']) for r in res if not r['pass']]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['shots', 'checks', 'play', 'page', 'contrast', 'fit'])
    ap.add_argument('--out', default=os.path.join(SCRATCH, 'shots'))
    ap.add_argument('--themes', default='default')
    ap.add_argument('--motions', default='living')
    ap.add_argument('--devices', default='desktop,phone')
    ap.add_argument('--mid', default='0.6,1.4,6.6,7.8,12.4,13.6,18.4,19.0,24.0,24.8,25.4,31.0,36.0', help='seconds to seek for mid-move frames')
    ap.add_argument('--headed', action='store_true')
    ap.add_argument('--fragment', default=None, help='contrast only: measure another fragment file (for example the pre-fix one)')
    a = ap.parse_args()
    a.mid = [float(x) for x in a.mid.split(',')]
    os.makedirs(a.out, exist_ok=True)
    if a.cmd == 'page':
        print(json.dumps(build_page()['report'], indent=1))
        return
    r = {'shots': run_shots, 'checks': run_checks, 'play': run_play, 'contrast': run_contrast, 'fit': run_fit}[a.cmd](a)
    if a.cmd != 'shots':
        print(json.dumps(r, indent=1)[:6000])


if __name__ == '__main__':
    sys.exit(main())
