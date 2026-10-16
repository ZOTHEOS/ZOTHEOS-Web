"""Council Route review capture: deterministic frames of the code-drawn route, encoded for review (never for the site).

The page is the preview page (fragment injected into an in-memory copy of the landing, real landing CSP plus one hash).
Every frame is a seek, not a recording: the run's Web Animations are held paused and set to t = n / fps through the
stage's own 'cr:seek' hook, no pointer moves, and the rest of the page is held deterministic in one of two ways:
  --motion calm    (the fix-pass captures) every other time-based animation is paused at currentTime 0 and the
                   ambient field holds one composed frame (scroll-driven animations hold still with the scroll);
  --motion living  (the final review captures) the page runs as a visitor in Living sees it, on a capture clock:
                   Playwright's clock drives Date, timers, requestAnimationFrame and performance.now (so the default
                   theme's WebGL edge effect and any rAF loop advance exactly 1/fps per frame), every page animation
                   that is running and endless when first seen (the card sheens, the release bar's sheen) is held
                   paused and set to the frame's page time, a finite one still running is finished, and an endless
                   one the page itself paused is held at phase 0.
PNG frames are piped to ffmpeg as a lossless FFV1 master, then encoded with SVT-AV1 10-bit and x264 (-an, +faststart),
each kept under the 4.9 caps (4 MB and 6 MB; the CRF steps up and the step is recorded if a file is over).

Outputs go to <temp>/council_route/out (or --out), never inside the checkout. From the repository root:
  py -3.10 tools/route/capture.py --motion living --verify --out <dir>/final    final review videos: desktop 1920x1080
                                            @1 and phone 390x844 @3, 60 fps, second pass compared
  py -3.10 tools/route/capture.py --sheets --out <dir>/final      contact sheets: 4 themes x (rest + 7 beats), desktop
                                            and phone; Still stepping sheets
  py -3.10 tools/route/capture.py                                 fix-pass captures (Calm), once each
  py -3.10 tools/route/capture.py --verify                        also a second pass per device, frame by frame
  py -3.10 tools/route/capture.py --devices desktop --theme skeleton --flash --clip-route --out <dir>/flash/skeleton
                                            flash check in process for a theme (no master: FFV1 is intra-only and
                                            the themed pages' grain texture makes every lossless frame costly)
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import platform
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import preview  # noqa: E402

OUT = os.path.join(preview.SCRATCH, 'out')
DEV = {
    'desktop': dict(viewport={'width': 1920, 'height': 1080}, device_scale_factor=1),
    'phone': dict(preview.DEVICES['phone']),
}
PRE, POST = 0.5, 1.0   # seconds of rest before the press and after the end
# Software raster: GPU raster alternated 1-level antialiasing on a few edge pixels between identical frames.
# WebGL still runs (ANGLE on SwiftShader, CPU), so the default theme's edge effect is drawn in Living.
ARGS = ['--mute-audio', '--disable-gpu', '--force-color-profile=srgb']
CAPS = {'av1': 4 * 1024 * 1024, 'x264': 6 * 1024 * 1024}   # 4.9: at most 4 MB SVT-AV1 10-bit and 6 MB x264
# The capture clock's wall time (Date) for --motion living: fixed, so nothing on the page can differ between passes.
CLOCK_T0 = '2026-10-15T18:00:00Z'
THEME_NAMES = {'default': 'Sovereign Skeleton', 'maya': 'Maya Radiance', 'codex': 'Living Codex', 'skeleton': 'Obsidian Ember'}

FREEZE = r"""() => {
  const R = document.getElementById('councilRoute');
  for (const a of document.getAnimations()) {
    const t = a.effect && a.effect.target;
    if ((!t || !R.contains(t)) && a.timeline instanceof DocumentTimeline) { a.pause(); a.currentTime = 0; }
  }
}"""
SEEK = r"""([t, label]) => {
  const R = document.getElementById('councilRoute');
  if (t !== null) R.dispatchEvent(new CustomEvent('cr:seek', {detail: t}));
  if (label) R.dataset.p = label;
  const R2 = R;
  for (const a of document.getAnimations()) {
    const x = a.effect && a.effect.target;
    if ((!x || !R2.contains(x)) && a.timeline instanceof DocumentTimeline) { a.pause(); a.currentTime = 0; }
  }
  return document.getAnimations().filter(a => a.effect && a.effect.target && R.contains(a.effect.target) && a.playState === 'running').length;
}"""
# Living: page time g (s since the first captured frame), route time t (s since the press, or null), button label.
LIVE = r"""([g, t, label]) => {
  const R = document.getElementById('councilRoute');
  if (t !== null) R.dispatchEvent(new CustomEvent('cr:seek', {detail: t}));
  if (label) R.dataset.p = label;
  const W = window.__crPage || (window.__crPage = {seen: new WeakSet(), amb: new Set(), log: []});
  for (const a of document.getAnimations()) {
    const x = a.effect && a.effect.target;
    if ((x && R.contains(x)) || !(a.timeline instanceof DocumentTimeline)) continue;
    if (!W.seen.has(a)) {
      W.seen.add(a);
      const endless = a.effect.getTiming().iterations === Infinity, what = (a.animationName || a.transitionProperty || 'animation') + ' on ' +
        (x ? (x.id || x.tagName.toLowerCase() + '.' + String(x.getAttribute('class') || '').split(' ').join('.')) : '?');
      if (a.playState === 'running' && endless) { W.amb.add(a); W.log.push(['advanced with page time', what]); }
      else if (a.playState === 'running') { a.finish(); W.log.push(['finished', what]); }
      else if (endless) { a.pause(); a.currentTime = 0; W.log.push(['held at 0 (paused by the page)', what]); }
    }
    if (W.amb.has(a)) { a.pause(); a.currentTime = g * 1000; }
  }
  return document.getAnimations().filter(a => a.effect && a.effect.target && R.contains(a.effect.target) && a.playState === 'running').length;
}"""
# Where the visitor's eye has to be during the run (4.8 fit): Pause, the stage, the caption box, the band between the
# fixed header and the sticky release bar (CSS px, viewport).
FIT_JS = r"""() => {
  const r = e => { const b = e.getBoundingClientRect(); return [Math.round(b.top), Math.round(b.bottom)]; };
  const hdr = document.getElementById('header').getBoundingClientRect(), cta = document.querySelector('.mobile-cta');
  const bar = cta && cta.classList.contains('visible') && getComputedStyle(cta).display !== 'none' ? Math.round(cta.getBoundingClientRect().top) : null;
  const o = {play: r(document.getElementById('crPlay')), stage: r(document.getElementById('crStage')),
    caption_box: r(document.querySelector('.cr-cap')), header_bottom: Math.round(hdr.bottom), sticky_bar_top: bar, viewport_h: innerHeight};
  const lo = o.header_bottom, hi = bar === null ? innerHeight : bar;
  o.all_visible = [o.play, o.stage, o.caption_box].every(([a, b]) => a >= lo && b <= hi);
  return o;
}"""


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def versions():
    def first(cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True).stdout.splitlines()[0].strip()
        except Exception as e:
            return 'unavailable: %s' % e
    from importlib.metadata import version
    ff = subprocess.run(['ffmpeg', '-hide_banner', '-version'], capture_output=True, text=True).stdout
    libs = [l.strip() for l in ff.splitlines() if l.strip().startswith(('libavcodec', 'libavformat'))]
    enc = {}
    for e in ('libsvtav1', 'libx264', 'ffv1'):
        r = subprocess.run(['ffmpeg', '-hide_banner', '-h', 'encoder=' + e], capture_output=True, text=True).stdout
        enc[e] = r.splitlines()[0].strip() if r else 'missing'
    out = {'python': platform.python_version(), 'playwright': version('playwright'), 'ffmpeg': ff.splitlines()[0],
           'ffmpeg_libs': libs, 'encoders': enc, 'node': first(['node', '--version']), 'os': platform.platform()}
    for m in ('PIL', 'cv2', 'numpy'):
        try:
            out[m] = __import__(m).__version__
        except Exception as e:
            out[m] = 'unavailable: %s' % e
    return out


def tag_of(device, theme, motion):
    t = device if theme == 'default' else '%s_%s' % (device, theme)
    return t if motion == 'calm' else '%s_%s' % (t, motion)


def capture(device, fps, built, out_dir, encode=True, theme='default', motion='calm', analyzer=None, clip_route=False, limit=None):
    from playwright.sync_api import sync_playwright
    os.makedirs(out_dir, exist_ok=True)
    tag = tag_of(device, theme, motion)
    master = os.path.join(out_dir, '%s_master.mkv' % tag)
    hashes = []
    clocked = motion == 'living'
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', headless=True, args=ARGS)
        chrome = b.version
        ctx, page, srv, logs = open_device(b, device, theme, motion, built, clock=clocked)
        vp = DEV[device]['viewport']
        scale = DEV[device].get('device_scale_factor', 1)
        size = '%dx%d' % (vp['width'] * scale, vp['height'] * scale)
        cur = [0]

        def advance(ms):   # the capture clock: page timers and rAF run only here
            if clocked and ms > cur[0]:
                page.clock.run_for(ms - cur[0])
                cur[0] = ms

        preview.to_route(page, 1600)
        if clocked:
            page.clock.run_for(1600)
            page.evaluate(LIVE, [0, None, None])
        else:
            page.evaluate(FREEZE)
        page.wait_for_timeout(300)
        tt = page.evaluate("() => { const L = [...document.querySelectorAll('#crList li')]; let T = 0;"
                           " for (const li of L) T += Math.ceil((1.5 + .26 * li.textContent.replace(/\\s+/g, ' ').trim().split(' ').length) * 2) / 2; return T; }")
        ff = None
        if encode:
            ff = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', str(fps),
                                   '-c:v', 'png', '-i', '-', '-c:v', 'ffv1', '-level', '3', '-pix_fmt', 'bgr0', '-an', master],
                                  stdin=subprocess.PIPE)

        box = page.locator('#councilRoute').bounding_box() if clip_route else None
        made = []

        def grab():
            png = page.screenshot(type='png', caret='hide', animations='allow', clip=box)
            hashes.append(hashlib.sha256(png).hexdigest())
            if ff:
                ff.stdin.write(png)
            if analyzer:   # flash check in process: no master file (FFV1 is intra-only; textured themes cost GBs)
                import cv2
                import numpy as np
                rgb = cv2.cvtColor(cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
                if not made:
                    made.append(analyzer(rgb.shape[1] // 4, rgb.shape[0] // 4))
                made[0].push(cv2.resize(rgb, (made[0].w, made[0].h), interpolation=cv2.INTER_AREA))

        def frame(t, label):
            i = len(hashes)
            if clocked:
                advance(round(i * 1000 / fps))
                r = page.evaluate(LIVE, [cur[0] / 1000, t, label])
            else:
                r = page.evaluate(SEEK, [t, label])
            grab()
            return r

        running = []
        fit = {}
        n_pre, n = int(PRE * fps), int(round(tt * fps))
        n_post = int(POST * fps)
        if limit:
            n_pre, n, n_post = min(n_pre, limit), min(n, limit), min(n_post, limit)
        for _ in range(n_pre):                    # rest diagram, Play offered
            frame(None, None)
        fit['rest'] = page.evaluate(FIT_JS)
        for i in range(n):                        # the run, one seek per frame; frame n_pre is the press
            running.append(frame(i / fps, 'pause'))
            if i == 0:
                fit['press'] = page.evaluate(FIT_JS)
        fit['end_of_run'] = page.evaluate(FIT_JS)
        # the end: the stage returns to rest and offers Replay (the same paint the timer reaches at 42.0 s)
        page.evaluate("() => { const R = document.getElementById('councilRoute'), c = document.getElementById('crCtl');"
                      " R.dispatchEvent(new CustomEvent('cr:seek', {detail: 0}));"
                      " c.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowLeft', bubbles: true}));"
                      " R.dataset.p = 'replay'; }")
        for _ in range(n_post):
            frame(None, None)
        end_state = page.evaluate(preview.STATE_JS)
        info = {'device': device, 'chrome': chrome, 'frames': len(hashes), 'fps': fps, 'run_seconds': tt, 'size': size,
                'theme': theme, 'motion': motion, 'max_running_stage_animations_during_seek': max(running or [0]),
                'clip': box, 'analyzer': made[0] if made else None, 'fit': fit,
                'end_state': {k: end_state[k] for k in ('b', 'p', 'caption', 'status', 'playHidden', 'stageAnims', 'runningStageAnims')},
                'external_requests': srv.external, 'console_errors': [l for l in logs if l.startswith(('error', 'pageerror'))],
                'console_warnings': sorted(set(l[:160] for l in logs if l.startswith('warning')))}
        if clocked:
            info['capture_clock'] = {'wall_time': CLOCK_T0, 'page_ms_advanced_during_capture': cur[0],
                                     'page_animations': page.evaluate('() => window.__crPage ? window.__crPage.log : []')}
            info['fx'] = page.evaluate("() => { const f = document.getElementById('zthFx'); return {has_mono_fx: document.documentElement.classList.contains('has-mono-fx'),"
                                       " canvas_class: f && f.className, display: f && getComputedStyle(f).display, opacity: f && getComputedStyle(f).opacity}; }")
        ctx.close()
        b.close()
    if ff:
        ff.stdin.close()
        ff.wait()
        info['master'] = os.path.basename(master)
    with open(os.path.join(out_dir, '%s_frames.sha256' % tag), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join('%05d %s' % (i, h) for i, h in enumerate(hashes)) + '\n')
    info['frames_digest'] = hashlib.sha256(''.join(hashes).encode()).hexdigest()
    return info, hashes


def open_device(b, device, theme, motion, built, clock=False, dev_opts=None):
    opts = dict(dev_opts or DEV[device])
    ctx = b.new_context(**opts)
    srv = preview.Server(built['html'], built['csp'])
    ctx.route('**/*', srv)
    ctx.add_init_script(preview.INIT % json.dumps({'theme': '' if theme == 'default' else theme, 'motion': motion}))
    if clock:
        ctx.clock.install(time=CLOCK_T0)
    page = ctx.new_page()
    logs = []
    page.on('console', lambda m: logs.append(m.type + ': ' + m.text))
    page.on('pageerror', lambda e: logs.append('pageerror: ' + str(e)))
    page.goto(preview.ORIGIN + '/', wait_until='load')
    if clock:   # no rAF polling under the capture clock: step the clock and look
        for i in range(400):
            page.clock.run_for(50)
            if i == 2:
                try:
                    if page.locator('#introGate').is_visible():
                        page.click('#gateQuiet')
                except Exception:
                    pass
            if page.evaluate("() => !document.body.classList.contains('page-loading')"):
                break
        else:
            raise RuntimeError('page-loading never cleared under the capture clock')
        page.evaluate('() => document.fonts.ready.then(() => true)')
        page.clock.run_for(600)
        page.wait_for_timeout(600)
        return ctx, page, srv, logs
    try:
        if page.locator('#introGate').is_visible():
            page.click('#gateQuiet')
    except Exception:
        pass
    page.wait_for_function("() => !document.body.classList.contains('page-loading')", timeout=20000)
    page.wait_for_timeout(600)
    return ctx, page, srv, logs


def encode(tag, out_dir):
    master = os.path.join(out_dir, '%s_master.mkv' % tag)
    av1 = os.path.join(out_dir, '%s_av1.mp4' % tag)
    x264 = os.path.join(out_dir, '%s_x264.mp4' % tag)
    settings = {}
    for crf in (32, 36, 40, 44):
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', master, '-c:v', 'libsvtav1',
                        '-pix_fmt', 'yuv420p10le', '-preset', '6', '-crf', str(crf), '-g', '300', '-svtav1-params', 'tune=0',
                        '-an', '-movflags', '+faststart', av1], check=True)
        settings['av1'] = 'libsvtav1 yuv420p10le preset 6 crf %d g 300 tune=0, -an, +faststart' % crf
        if os.path.getsize(av1) <= CAPS['av1']:
            break
    for crf in (20, 23, 26, 29):
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', master, '-c:v', 'libx264',
                        '-pix_fmt', 'yuv420p', '-preset', 'slow', '-crf', str(crf), '-tune', 'animation', '-threads', '1',
                        '-an', '-movflags', '+faststart', x264], check=True)
        settings['x264'] = 'libx264 yuv420p preset slow crf %d tune animation threads 1, -an, +faststart' % crf
        if os.path.getsize(x264) <= CAPS['x264']:
            break
    out = {}
    for p in (master, av1, x264):
        probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,nb_frames',
                                '-show_entries', 'format=duration', '-of', 'json', p], capture_output=True, text=True).stdout
        pj = json.loads(probe)
        streams = pj.get('streams', [])
        kind = 'av1' if p == av1 else 'x264' if p == x264 else None
        out[os.path.basename(p)] = {'bytes': os.path.getsize(p), 'sha256': sha_file(p), 'streams': streams,
                                    'duration_s': pj.get('format', {}).get('duration'),
                                    'audio_streams': sum(1 for s in streams if s.get('codec_type') == 'audio'),
                                    'settings': settings.get(kind, 'ffv1 level 3 bgr0 (lossless master)'),
                                    'cap_bytes': CAPS.get(kind), 'within_cap': os.path.getsize(p) <= CAPS[kind] if kind else None,
                                    'faststart_moov_before_mdat': faststart(p) if kind else None}
    return out


def faststart(path):
    """True when the moov box comes before mdat (what +faststart promises)."""
    with open(path, 'rb') as f:
        pos, order = 0, []
        while len(order) < 8:
            f.seek(pos)
            hdr = f.read(8)
            if len(hdr) < 8:
                break
            size, kind = int.from_bytes(hdr[:4], 'big'), hdr[4:].decode('latin-1')
            if size == 1:
                size = int.from_bytes(f.read(8), 'big')
            order.append(kind)
            if size < 8:
                break
            pos += size
    return 'moov' in order and 'mdat' in order and order.index('moov') < order.index('mdat')


# ---------------------------------------------------------------------------------------------------------------
# Contact sheets: still images for review, composed with Pillow. Every cell is a real screenshot of the preview page.

def _font(size, bold=False):
    from PIL import ImageFont
    for f in (('segoeuib.ttf' if bold else 'segoeui.ttf'), 'arial.ttf'):
        try:
            return ImageFont.truetype(os.path.join(os.environ.get('WINDIR', 'C:/Windows'), 'Fonts', f), size)
        except OSError:
            continue
    return ImageFont.load_default()


def _union(page, sels, pad_bottom=12):
    # pad_bottom: CSS px of the card below the caption box, so descenders of the last caption line are never at the edge
    boxes = [page.locator(s).bounding_box() for s in sels]
    x0 = min(b['x'] for b in boxes)
    y0 = min(b['y'] for b in boxes)
    x1 = max(b['x'] + b['width'] for b in boxes)
    y1 = max(b['y'] + b['height'] for b in boxes) + pad_bottom
    return {'x': x0, 'y': y0, 'width': x1 - x0, 'height': y1 - y0}


def _png(page, clip):
    from PIL import Image
    data = page.screenshot(type='png', caret='hide', animations='allow', clip=clip)
    return data, Image.open(io.BytesIO(data)).convert('RGB')


def _neutral_mouse(page, dev):
    # Off the route and off every control: the left page margin, mid height (no hover state in a cell).
    page.mouse.move(4, DEV_SHEET[dev]['viewport']['height'] // 2)


DEV_SHEET = {'desktop': dict(preview.DEVICES['desktop']), 'phone': dict(preview.DEVICES['phone'])}
STATE_NAMES = ['Rest, before Play'] + ['Beat %d' % k for k in range(1, 8)]


def sheet_cells_themes(b, built, dev, cells_dir):
    """4 themes x (rest + 7 beats), each at the end state of the beat (Next shows it instantly), Calm."""
    rows = {}
    rep = {}
    for theme in preview.THEMES:
        ctx, page, srv, logs = open_device(b, dev, theme, 'calm', built, dev_opts=DEV_SHEET[dev])
        preview.to_route(page, 1600)
        _neutral_mouse(page, dev)
        page.evaluate(LIVE, [0, None, None])
        page.wait_for_timeout(200)
        imgs, states = [], []
        for k in range(8):
            if k:
                page.click('#crNext')
                _neutral_mouse(page, dev)
                page.wait_for_timeout(120)
                page.evaluate(LIVE, [0, None, None])
                page.wait_for_timeout(80)
            clip = _union(page, ['#crStage', '.cr-cap'])
            data, im = _png(page, clip)
            name = '%s_%s_%s.png' % (dev, theme, 'rest' if k == 0 else 'beat%d' % k)
            with open(os.path.join(cells_dir, name), 'wb') as f:
                f.write(data)
            st = page.evaluate(preview.STATE_JS)
            collisions = page.evaluate(preview.COLLIDE_JS)
            states.append({'cell': name, 'sha256': hashlib.sha256(data).hexdigest(), 'b': st['b'], 'status': st['status'],
                           'caption': st['caption'], 'stage_animations': st['stageAnims'], 'collisions': collisions,
                           'play_hidden': st['playHidden']})
            imgs.append(im)
        rep[theme] = {'states': states, 'external_requests': srv.external,
                      'console_errors': [l for l in logs if l.startswith(('error', 'pageerror'))], 'cspv': page.evaluate('() => window.__cspv')}
        rows[theme] = imgs
        ctx.close()
    return rows, rep


def sheet_cells_still(b, built, dev, cells_dir):
    """Still (Appearance Motion), default theme: the static diagram, then Next through all 7 beats, then Previous back."""
    ctx, page, srv, logs = open_device(b, dev, 'default', 'still', built, dev_opts=DEV_SHEET[dev])
    preview.to_route(page, 1600)
    _neutral_mouse(page, dev)
    page.wait_for_timeout(300)
    route_anims = "() => { const R = document.getElementById('councilRoute'); return document.getAnimations().filter(a => a.effect && a.effect.target && R.contains(a.effect.target)).length; }"
    imgs, states, fwd = [], [], {}
    for k in range(8):
        if k:
            page.click('#crNext')
            _neutral_mouse(page, dev)
            page.wait_for_timeout(150)
        clip = _union(page, ['#crRun'])
        data, im = _png(page, clip)
        name = '%s_still_%s.png' % (dev, 'rest' if k == 0 else 'step%d' % k)
        with open(os.path.join(cells_dir, name), 'wb') as f:
            f.write(data)
        stage = page.locator('#crStage').screenshot(type='png', animations='allow')
        fwd[k] = hashlib.sha256(stage).hexdigest()
        st = page.evaluate(preview.STATE_JS)
        states.append({'cell': name, 'sha256': hashlib.sha256(data).hexdigest(), 'b': st['b'], 'status': st['status'],
                       'caption': st['caption'], 'play_hidden': st['playHidden'], 'transcript_open': st['transcriptOpen'],
                       'route_animations': page.evaluate(route_anims), 'running_stage_animations': st['runningStageAnims'],
                       'prev_disabled': page.get_attribute('#crPrev', 'aria-disabled'),
                       'next_disabled': page.get_attribute('#crNext', 'aria-disabled'),
                       'motion': page.evaluate('() => document.documentElement.dataset.motion')})
        imgs.append(im)
    # Next at step 7 does nothing; Previous walks back to rest, each state identical to the way forward.
    page.click('#crNext', force=True)   # aria-disabled at step 7: Playwright would wait for it to be enabled
    page.wait_for_timeout(100)
    after_extra_next = page.evaluate(preview.STATE_JS)['b']
    back = {}
    for k in range(6, -1, -1):
        page.click('#crPrev')
        _neutral_mouse(page, dev)
        page.wait_for_timeout(150)
        back[k] = hashlib.sha256(page.locator('#crStage').screenshot(type='png', animations='allow')).hexdigest()
    # A seek attempt under Still must create nothing (the capture hook does nothing in Still).
    page.evaluate("() => document.getElementById('councilRoute').dispatchEvent(new CustomEvent('cr:seek', {detail: 20}))")
    seek_anims = page.evaluate(route_anims)
    # The transcript, open by default in Still: brought between the header and the release bar, then captured.
    page.evaluate("() => { const t = document.getElementById('crText'), h = document.getElementById('header').getBoundingClientRect().bottom;"
                  " window.scrollBy({top: t.getBoundingClientRect().top - h - 8, behavior: 'instant'}); }")
    page.wait_for_timeout(400)
    tb = page.locator('#crText').bounding_box()
    fitj = page.evaluate(FIT_JS)
    bottom = fitj['sticky_bar_top'] if fitj['sticky_bar_top'] is not None else fitj['viewport_h']
    clip = {'x': tb['x'], 'y': tb['y'], 'width': tb['width'], 'height': min(tb['height'], bottom - tb['y'])}
    data, tim = _png(page, clip)
    tname = '%s_still_transcript.png' % dev
    with open(os.path.join(cells_dir, tname), 'wb') as f:
        f.write(data)
    rep = {'states': states, 'next_at_7_stays': after_extra_next == '7',
           'previous_matches_forward': {str(k): back[k] == fwd[k] for k in back},
           'route_animations_after_seek_attempt': seek_anims,
           'transcript': {'cell': tname, 'sha256': hashlib.sha256(data).hexdigest(), 'height_css': round(tb['height']),
                          'clipped_by_bar_css': round(max(0, tb['y'] + tb['height'] - bottom))},
           'external_requests': srv.external, 'console_errors': [l for l in logs if l.startswith(('error', 'pageerror'))],
           'cspv': page.evaluate('() => window.__cspv')}
    ctx.close()
    return imgs, tim, rep


def compose(grid, col_titles, row_titles, title, footer, scale, out_path, wide=None):
    """grid: list of rows, each a list of PIL images (None for an empty slot). wide: one extra image across the bottom."""
    from PIL import Image, ImageDraw
    pad, gap = 32, 18
    f_title, f_head, f_lab, f_foot = _font(30, True), _font(22, True), _font(19), _font(17)
    cells = [[im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS) if im else None for im in row] for row in grid]
    ncol = max(len(r) for r in cells)
    colw = [max((r[c].width for r in cells if c < len(r) and r[c]), default=0) for c in range(ncol)]
    rowh = [max((im.height for im in r if im), default=0) for r in cells]
    lab_h = 30
    head_h = 44 if col_titles else 0
    width = pad * 2 + sum(colw) + gap * (ncol - 1)
    probe = ImageDraw.Draw(Image.new('RGB', (8, 8)))

    def wrap(text, font, w):   # greedy word wrap to the sheet width
        lines, cur = [], ''
        for word in text.split(' '):
            t = (cur + ' ' + word).strip()
            if cur and probe.textlength(t, font=font) > w:
                lines.append(cur)
                cur = word
            else:
                cur = t
        return lines + [cur]
    t_lines, f_lines = wrap(title, f_title, width - 2 * pad), wrap(footer, f_foot, width - 2 * pad)
    title_h = 40 * len(t_lines) + 16
    foot_h = 26 * len(f_lines) + 30
    wide_im = wide.resize((max(1, round(wide.width * scale)), max(1, round(wide.height * scale))), Image.LANCZOS) if wide else None
    height = pad + title_h + head_h + sum(h + lab_h + gap for h in rowh) + (wide_im.height + lab_h + gap if wide_im else 0) + foot_h
    canvas = Image.new('RGB', (width, height), (38, 38, 40))
    d = ImageDraw.Draw(canvas)
    for i, line in enumerate(t_lines):
        d.text((pad, pad + 40 * i), line, font=f_title, fill=(240, 240, 240))
    y = pad + title_h
    if col_titles:
        x = pad
        for c, t in enumerate(col_titles):
            d.text((x, y + 6), t, font=f_head, fill=(230, 230, 230))
            x += colw[c] + gap
        y += head_h
    for r, row in enumerate(cells):
        x = pad
        for c, im in enumerate(row):
            lab = row_titles[r][c] if isinstance(row_titles[r], (list, tuple)) else (row_titles[r] if c == 0 else '')
            if lab:
                d.text((x, y + 2), lab, font=f_lab, fill=(205, 205, 205))
            if im:
                canvas.paste(im, (x, y + lab_h))
                d.rectangle([x - 1, y + lab_h - 1, x + im.width, y + lab_h + im.height], outline=(90, 90, 94))
            x += colw[c] + gap
        y += rowh[r] + lab_h + gap
    if wide_im:
        d.text((pad, y + 2), wide[1] if isinstance(wide, tuple) else 'Read the route as text (open by default in Still)', font=f_lab, fill=(205, 205, 205))
        canvas.paste(wide_im, (pad, y + lab_h))
        y += wide_im.height + lab_h + gap
    for i, line in enumerate(f_lines):
        d.text((pad, height - foot_h + 8 + 26 * i), line, font=f_foot, fill=(170, 170, 170))
    canvas.save(out_path, optimize=True)
    return {'path': out_path, 'size': [width, height], 'bytes': os.path.getsize(out_path), 'sha256': sha_file(out_path), 'cell_scale': scale}


def run_sheets(out_dir, built):
    from playwright.sync_api import sync_playwright
    cells_dir = os.path.join(out_dir, 'cells')
    os.makedirs(cells_dir, exist_ok=True)
    foot = ('Review material, not on the site. Real screenshots of the preview page (fragment sha256 %s, base origin/main %s, '
            'landing CSP plus one hash). No generative model.' % (sha_file(preview.FRAGMENT)[:12], built['base_sha'][:7]))
    report = {'made': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'), 'sheets': {}, 'checks': {}}
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', headless=True, args=ARGS)
        report['chrome'] = b.version
        for dev in ('desktop', 'phone'):
            rows, rep = sheet_cells_themes(b, built, dev, cells_dir)
            report['checks']['themes_' + dev] = rep
            vp, dpr = DEV_SHEET[dev]['viewport'], DEV_SHEET[dev]['device_scale_factor']
            dims = '%dx%d at %sx' % (vp['width'], vp['height'], dpr)
            if dev == 'desktop':   # rows: rest + 7 beats; columns: the four themes
                grid = [[rows[t][k] for t in preview.THEMES] for k in range(8)]
                info = compose(grid, ['%s (%s)' % (THEME_NAMES[t], t) for t in preview.THEMES], STATE_NAMES,
                               'The Council Route: rest and the 7 beats, each at its end state, in the four Appearance themes (desktop %s, Calm)' % dims,
                               foot, 0.48, os.path.join(out_dir, 'contact_sheet_themes_desktop.png'))
            else:                  # rows: the four themes; columns: rest + 7 beats
                grid = [rows[t] for t in preview.THEMES]
                info = compose(grid, None, [['%s: %s' % (THEME_NAMES[t], s) for s in STATE_NAMES] for t in preview.THEMES],
                               'The Council Route on a phone: rest and the 7 beats in the four Appearance themes (%s, Calm)' % dims,
                               foot, 0.40, os.path.join(out_dir, 'contact_sheet_themes_phone.png'))
            report['sheets']['themes_' + dev] = info
            print('sheet', info['path'], info['size'], info['bytes'], flush=True)
        for dev in ('desktop', 'phone'):
            imgs, tim, rep = sheet_cells_still(b, built, dev, cells_dir)
            report['checks']['still_' + dev] = rep
            vp, dpr = DEV_SHEET[dev]['viewport'], DEV_SHEET[dev]['device_scale_factor']
            dims = '%dx%d at %sx' % (vp['width'], vp['height'], dpr)
            labels = ['Rest: the static diagram (Play hidden)'] + ['Next, step %d of 7' % k for k in range(1, 8)]
            if dev == 'desktop':
                grid = [imgs[0:2], imgs[2:4], imgs[4:6], imgs[6:8]]
                titles = [labels[0:2], labels[2:4], labels[4:6], labels[6:8]]
                scale = 0.5
            else:
                grid = [imgs[0:4], imgs[4:8]]
                titles = [labels[0:4], labels[4:8]]
                scale = 0.5
            info = compose(grid, None, titles,
                           'The Council Route in Still (Appearance Motion): the static diagram and stepping, nothing animates (%s, default theme)' % dims,
                           foot, scale, os.path.join(out_dir, 'still_sheet_%s.png' % dev), wide=tim)
            report['sheets']['still_' + dev] = info
            print('sheet', info['path'], info['size'], info['bytes'], flush=True)
        b.close()
    report['cells'] = {n: sha_file(os.path.join(cells_dir, n)) for n in sorted(os.listdir(cells_dir))}
    with open(os.path.join(out_dir, 'sheets.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=1)
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--devices', default='desktop,phone')
    ap.add_argument('--fps', type=int, default=60)
    ap.add_argument('--verify', action='store_true', help='a second pass per device, compared frame by frame')
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--theme', default='default', choices=preview.THEMES)
    ap.add_argument('--motion', default='calm', choices=['calm', 'living'])
    ap.add_argument('--flash', action='store_true', help='flash check in process (flash_check.Analyzer), no master or encodes')
    ap.add_argument('--clip-route', action='store_true', help='frames of the route block only (smaller fields: a stricter check)')
    ap.add_argument('--sheets', action='store_true', help='contact sheets instead of videos')
    ap.add_argument('--limit', type=int, default=None, help='probe: at most this many frames per phase, no encode')
    a = ap.parse_args()
    built = preview.build_page()
    os.makedirs(a.out, exist_ok=True)
    if a.sheets:
        r = run_sheets(a.out, built)
        print(json.dumps({k: (v['path'], v['size'], v['bytes']) for k, v in r['sheets'].items()}, indent=1))
        return
    frag_sha = sha_file(preview.FRAGMENT)
    receipt = {'made': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds'),
               'purpose': 'review capture of the Council Route; never on the site; written outside the repository',
               'base_commit': built['base_sha'], 'base_repo': preview.ROOT,
               'fragment_sha256': frag_sha, 'new_inline_script_hash': built['script_hash'],
               'chrome_args': ARGS, 'caps_bytes': CAPS,
               'generative_models': 'none', 'audio': 'none', 'tools': versions(), 'devices': {}}
    if a.motion == 'living':
        receipt['method'] = ('Playwright Chrome (software raster; WebGL on SwiftShader), Motion Living on a capture clock (Playwright clock: Date '
                             'fixed at %s, timers, requestAnimationFrame and performance.now advanced 1/fps per frame); the route\'s '
                             'Web Animations held paused and seeked per frame through cr:seek; page animations running and endless when '
                             'first seen held paused and set to the frame\'s page time, finite ones still running finished, endless ones '
                             'the page paused held at 0; PNG frames piped to ffmpeg FFV1 (lossless) then SVT-AV1 10-bit and x264, -an, '
                             '+faststart' % CLOCK_T0)
        receipt['omits'] = ('No pointer moves, so pointer-driven tilt and hover states are absent. The press is shown by the button '
                            'label changing to Pause at frame %d (0.5 s); the real Play also scrolls #crRun into view with block '
                            'nearest, which does not move the page here because the block is already in view (see fit).' % int(PRE * a.fps))
    else:
        receipt['method'] = ('Playwright Chrome (software raster), Web Animations held paused and seeked per frame through cr:seek; other page '
                             'animations paused at 0; Motion Calm; PNG frames piped to ffmpeg FFV1 (lossless) then SVT-AV1 '
                             '10-bit and x264, -an, +faststart')
        receipt['omits'] = ('Page animations outside the route are held at frame 0 for determinism, so the capture does not show '
                            'the default theme card sheen (z-sheen, 13 s) or the Codex and Ember rain. On the live page the sheen '
                            'still crosses the card outside the stage; inside the stage the flat ground (--cr-g) masks it.')
    for dev in a.devices.split(','):
        an = None
        if a.flash:
            import flash_check
            field = (0.75, 1 / 3) if dev == 'phone' and not a.clip_route else (1 / 3, 1 / 3)
            an = lambda w, h: flash_check.Analyzer(w, h, a.fps, field)
        enc = not a.flash and not a.limit
        info, h1 = capture(dev, a.fps, built, a.out, encode=enc, theme=a.theme, motion=a.motion, analyzer=an,
                           clip_route=a.clip_route, limit=a.limit)
        made = info.pop('analyzer', None)
        tag = tag_of(dev, a.theme, a.motion)
        if a.flash:
            info['flash'] = made.finish()
            info['outputs'] = {}
        elif enc:
            info['outputs'] = encode(tag, a.out)
        else:
            info['outputs'] = {}
        if a.verify:
            _, h2 = capture(dev, a.fps, built, os.path.join(a.out, 'verify'), encode=False, theme=a.theme, motion=a.motion, limit=a.limit)
            diff = [i for i, (x, y) in enumerate(zip(h1, h2)) if x != y]
            info['determinism'] = {'second_pass_frames': len(h2), 'identical': len(h1) == len(h2) and not diff,
                                   'differing_frames': diff[:50], 'differing_count': len(diff)}
        receipt['devices'][tag] = info
        print(dev, json.dumps({k: v for k, v in info.items() if k not in ('outputs', 'capture_clock')})[:900], flush=True)
        for k, v in info['outputs'].items():
            print('  ', k, v['bytes'], v['sha256'][:16], 'audio', v['audio_streams'], 'cap ok', v['within_cap'], flush=True)
    p = os.path.join(a.out, 'receipt.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(receipt, f, indent=1)
    print('receipt', p)


if __name__ == '__main__':
    main()
