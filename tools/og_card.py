"""Renders the site-wide share card static/og.png (1200 x 630, og:image on every page) from HTML with Playwright.

The card: the shipped ZOTHEOS wordmark (static/zotheos_logo.png, white on transparent, resized once with Lanczos to its
exact pixel box so the browser draws it 1:1), "A private, local AI council. You decide." in the site's self-hosted
Instrument Serif, and zotheos.org in the self-hosted JetBrains Mono, on a flat obsidian ground. No gradient, glow,
blur, grain or haze; no claim beyond the landing's own words. Centered, so a square center crop keeps the wordmark and
the first line whole. Every resource is inlined as a data URI: no network request is made.

  py -3.10 tools/og_card.py              writes static/og.png and prints its size and sha256
  py -3.10 tools/og_card.py --check      renders in memory and exits 1 if static/og.png differs (same Chrome build)
  py -3.10 tools/og_card.py --out FILE   writes elsewhere
Needs Playwright with Chrome (channel "chrome") and Pillow.
"""
import argparse
import base64
import hashlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1200, 630
LOGO_W = 540          # CSS px (the wordmark is 3878 x 814)
TOP, LINE_TOP, SIZE, RULE_TOP, FOOT_TOP = 96, 262, 72, 486, 512

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:IS;src:url(data:font/woff2;base64,%(serif)s) format('woff2');font-weight:400;font-style:normal}
@font-face{font-family:IS;src:url(data:font/woff2;base64,%(serif_i)s) format('woff2');font-weight:400;font-style:italic}
@font-face{font-family:JBM;src:url(data:font/woff2;base64,%(mono)s) format('woff2');font-weight:100 800}
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:%(W)dpx;height:%(H)dpx;background:#050507;overflow:hidden}
body{position:relative;color:#fff;-webkit-font-smoothing:antialiased;text-align:center}
.mark{position:absolute;left:%(LX)dpx;top:%(TOP)dpx;width:%(LW)dpx;height:%(LH)dpx;display:block}
.line{position:absolute;left:0;right:0;top:%(LINE_TOP)dpx;font:400 %(SIZE)dpx/1.08 IS,serif;letter-spacing:-.01em;color:#FFFFFF}
.line i{font-style:italic;color:#C8C8C8}
.rule{position:absolute;left:%(RX)dpx;width:64px;top:%(RULE_TOP)dpx;height:1px;background:#8A8A8A}
.foot{position:absolute;left:0;right:0;top:%(FOOT_TOP)dpx;font:500 18px/1 JBM,monospace;letter-spacing:.14em;color:#A3A3A3}
</style></head><body>
<img class="mark" src="%(LOGO)s" alt="">
<p class="line">A private, local AI council.<br><i>You decide.</i></p>
<div class="rule"></div>
<div class="foot">zotheos.org</div>
</body></html>"""


def b64(p):
    with open(p, 'rb') as f:
        return base64.b64encode(f.read()).decode('ascii')


def render():
    from PIL import Image
    from playwright.sync_api import sync_playwright
    logo = Image.open(os.path.join(ROOT, 'static', 'zotheos_logo.png')).convert('RGBA')
    lh = round(LOGO_W * logo.height / logo.width)
    buf = io.BytesIO()
    logo.resize((LOGO_W, lh), Image.LANCZOS).save(buf, 'PNG')
    fonts = os.path.join(ROOT, 'static', 'fonts')
    html = PAGE % dict(serif=b64(os.path.join(fonts, 'instrument-serif-latin.woff2')),
                       serif_i=b64(os.path.join(fonts, 'instrument-serif-italic-latin.woff2')),
                       mono=b64(os.path.join(fonts, 'jetbrains-mono-var-latin.woff2')),
                       LOGO='data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii'),
                       W=W, H=H, LW=LOGO_W, LH=lh, LX=(W - LOGO_W) // 2, RX=W // 2 - 32, TOP=TOP,
                       LINE_TOP=LINE_TOP, SIZE=SIZE, RULE_TOP=RULE_TOP, FOOT_TOP=FOOT_TOP)
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=['--mute-audio', '--font-render-hinting=none'])
        pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
        external = []
        pg.on('request', lambda r: external.append(r.url[:80]) if not r.url.startswith(('data:', 'about:')) else None)
        pg.set_content(html, wait_until='load')
        loaded = pg.evaluate("document.fonts.ready.then(() => Array.from(document.fonts)"
                             ".filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.style))")
        shot = pg.screenshot(type='png', clip={'x': 0, 'y': 0, 'width': W, 'height': H})
        chrome = b.version
        b.close()
    assert not external, external
    assert sorted(loaded) == ['IS italic', 'IS normal', 'JBM normal'], loaded
    im = Image.open(io.BytesIO(shot)).convert('RGB')
    assert im.size == (W, H), im.size
    out = io.BytesIO()
    im.save(out, 'PNG', optimize=True)
    return out.getvalue(), chrome


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'static', 'og.png'))
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    data, chrome = render()
    info = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'size': [W, H], 'chrome': chrome}
    if a.check:
        with open(a.out, 'rb') as f:
            same = f.read() == data
        info['matches'] = same
        print(json.dumps(info))
        sys.exit(0 if same else 1)
    with open(a.out, 'wb') as f:
        f.write(data)
    info['out'] = a.out
    print(json.dumps(info))


if __name__ == '__main__':
    main()
