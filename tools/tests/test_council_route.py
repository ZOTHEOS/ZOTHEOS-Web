"""Council Route gates: caption-to-site phrase parity, no em or en dashes, byte caps, no external URLs or requests (the
Audio slot loads nothing until the owner configures a same-origin sound file), no inline handlers, the motion and colour
contract, the playback contract (autoplay on view in Living and Calm, CC, the hidden Audio slot, guarded haptics), the
fragment equal to the blocks integrated in index.html (placement and CSP hash included), and the controller checks in
test_council_route.cjs (node, run on the fragment and on index.html).

  py -3.10 -m pytest tools/tests/test_council_route.py -q -p no:cacheprovider
The landing page is the repository's index.html; CR_BASE_INDEX overrides it. Line endings are folded to LF before any
comparison (a Windows checkout may hold CRLF; the repository and the CSP hash use LF). Stdlib plus brotli (already
pinned for the site's size gate).
"""
import ast
import base64
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
from html.parser import HTMLParser

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
FRAGMENT = os.path.join(ROOT, 'tools', 'route', 'council_route.fragment.html')
MARKERS = {
    'markup': ('<!-- council-route:markup -->', '<!-- /council-route:markup -->'),
    'css': ('/* council-route:css */', '/* /council-route:css */'),
    'js': ('/* council-route:js */', '/* /council-route:js */'),
}
# Wrappers the integration adds around the CSS and JS blocks (one <style>, one new inline <script>).
WRAP = len('<style>\n') + len('\n</style>\n') + len('<script>\n') + len('\n</script>\n')
# Everything else the integration adds to index.html, counted against the same cap (review B-F6): the line break and
# indentation before the markup block, and the new hash csp_sync writes into the page's own meta policy
# (" 'sha256-" + 44 base64 characters + "'"). The vercel.json header copy is not in index.html.
INSERT_LINE = len('\n' + ' ' * 10)
META_HASH = len(" 'sha256-" + 'A' * 44 + "'")
# The prototype's budget was 18 KiB raw and 6 KiB brotli. The owner's playback request (autoplay on view, CC, the Audio
# slot and haptics, 16 Oct 2026) added about 2.5 KiB raw and 0.8 KiB brotli, so the caps moved to 22 KiB and 7 KiB.
RAW_CAP, BROTLI_CAP = 22528, 7168


def read(p):
    with open(p, encoding='utf-8', newline='') as f:
        return f.read()


def index_path():
    p = os.environ.get('CR_BASE_INDEX') or os.path.join(ROOT, 'index.html')
    assert os.path.isfile(p), 'no landing index.html at ' + p
    return p


def page():
    return read(index_path()).replace('\r\n', '\n').replace('\r', '\n')


def site_text():
    """The landing's visible text without the route's own block, so the parity checks compare the route with the rest
    of the page (the Fusion figure, its caption, the Method notes and the cards) and never with itself."""
    s = page()
    a, b = MARKERS['markup']
    if a in s:
        s = s[:s.index(a)] + s[s.index(b) + len(b):]
    return norm(visible(s))


FRAG = read(FRAGMENT)


def block(name):
    a, b = MARKERS[name]
    assert FRAG.count(a) == 1 and FRAG.count(b) == 1, name
    return FRAG[FRAG.index(a):FRAG.index(b) + len(b)]


MARKUP, CSS, JS = block('markup'), block('css'), block('js')


class Text(HTMLParser):
    """Visible text: everything outside script, style and template; <br> as a space."""

    def __init__(self, skip=('script', 'style', 'template')):
        super().__init__(convert_charrefs=True)
        self.skip, self.depth, self.out = skip, 0, []

    def handle_starttag(self, tag, attrs):
        if tag in self.skip:
            self.depth += 1
        elif tag == 'br':
            self.out.append(' ')

    def handle_endtag(self, tag):
        if tag in self.skip and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            self.out.append(data)


def visible(src, skip=('script', 'style', 'template')):
    p = Text(skip)
    p.feed(src)
    return re.sub(r'\s+', ' ', ''.join(p.out)).strip()


def norm(s):
    return re.sub(r'\s+', ' ', html.unescape(s)).strip().lower()


def captions():
    ol = re.search(r'<ol id="crList">(.*?)</ol>', MARKUP, re.S).group(1)
    return [visible(li) for li in re.findall(r'<li>(.*?)</li>', ol, re.S)]


# (phrase in the route's own text, phrase in the live landing's visible text). A copy change on either side fails here
# until the drawing and its captions are reviewed again.
PARITY = {
    1: [('Sources enter when supplied or retrieved.', 'Sources enter when supplied or retrieved.'),
        ('run on your hardware', 'runs on your hardware')],
    2: [('builds the first draft from the question, reasoning and available evidence',
         'Builds the first draft from the question, reasoning and available evidence.')],
    3: [('also reads that draft', "Also reads the Analyst's draft"), ('possibly shortened', 'that context can be shortened'),
        ('who is affected, what matters', 'who is affected, what matters'), ('what it overlooks', 'what the first draft overlooks')],
    4: [('also reads both earlier drafts', 'Also reads both earlier drafts'),
        ('against their strongest agreement, not against you', 'argues against the strongest agreement between the other two minds, not against you')],
    5: [('One synthesized draft', 'One synthesized draft'), ('combines the perspectives', 'Combines the perspectives'),
        ("Synthesis normally reuses the Analyst's model", "Synthesis normally reuses the Analyst's model"),
        ('not an independent fourth judge', 'rather than adding an independent fourth judge')],
    6: [('Accept, question or reject the draft. The decision stays with you.',
         'Accept, question or reject the draft. The decision stays with you.')],
    7: [('Agreement is not proof.', 'agreement is not proof'),
        ('the standard full council route, not a live run', 'Illustration of the standard full council route, not a live run.')],
}
LABELS = [('Your question + supporting sources', 'Your question + supporting sources'),
          ('Connection needed for model downloads and optional tools', 'Connection needed for model downloads and optional tools'),
          ('Optional extra cross-critique,', 'Optional extra cross-critique.'), ('off by default', 'This extra round is off by default.'),
          ("Analyst's model", "reuses the Analyst's model"), ('Strongest agreement,', 'the strongest agreement between the earlier perspectives'),
          ('A separate debate mode can use additional rounds.', 'A separate debate mode can use additional rounds.'),
          ('Modes, settings and model availability can change the stages.', 'Modes, settings and model availability can change the stages.')]


def test_seven_captions_in_order():
    c = captions()
    assert len(c) == 7
    assert c[0].startswith('You bring a question.') and c[6].endswith('Timing is not to scale.')


@pytest.mark.parametrize('beat', sorted(PARITY))
def test_caption_phrase_parity_with_site(beat):
    site = site_text()
    cap = norm(captions()[beat - 1])
    for mine, theirs in PARITY[beat]:
        assert norm(mine) in cap, 'beat %d caption lost its key phrase: %r' % (beat, mine)
        assert norm(theirs) in site, 'site sentence changed for beat %d: %r' % (beat, theirs)


def test_label_and_transcript_parity_with_site():
    site = site_text()
    mine = norm(visible(MARKUP))
    for a, b in LABELS:
        assert norm(a) in mine, a
        assert norm(b) in site, b


def test_no_em_or_en_dashes_anywhere():
    for bad in ('\u2013', '\u2014', '&ndash;', '&mdash;', '&#8211;', '&#8212;', '&#x2013;', '&#x2014;', '\\u2013', '\\u2014'):
        assert bad not in FRAG, repr(bad)


def test_claim_words_only_where_allowed():
    text = norm(visible(MARKUP))
    assert text.count('independent') == 1 and 'not an independent fourth judge' in text
    assert 'disagreement' not in text, 'the disagreements claim waits for the confirmed variant'
    for word in ('independently', 'accurate', 'accuracy', 'guarantee', 'proves', 'conscious', 'available now', 'live run of'):
        assert word not in text, word


def test_byte_caps():
    import brotli
    added = (MARKUP + CSS + JS).encode('utf-8')
    raw = len(added) + WRAP
    integrated = raw + INSERT_LINE + META_HASH
    br = len(brotli.compress(added, quality=11))
    print('council route added: blocks+wrappers raw %d B, integrated growth of index.html raw %d B (meta-CSP hash and '
          'insert line included), brotli %d B' % (raw, integrated, br))
    assert integrated <= RAW_CAP, integrated
    assert br <= BROTLI_CAP, br


def test_no_external_urls_or_requests():
    urls = re.findall(r'(?:https?:)?//[^\s\'"<>)]+', FRAG.replace('<!--', '').replace('-->', ''))
    urls = [u for u in urls if u not in ('http://www.w3.org/2000/svg',)]
    assert not urls, urls
    # The one request the route can ever make is the owner's own sound: a same-origin file named in SOUND_FILE, which
    # ships empty, made only inside the Audio button's handler, which is attached only when SOUND_FILE is set.
    assert "const SOUND_FILE = '';" in JS
    assert JS.count('au.src = SOUND_FILE;') == 1 and JS.count("createElement('audio')") == 1
    handler = JS[JS.index('if (SOUND_FILE) bS.addEventListener('):]
    assert handler.index("createElement('audio')") < handler.index('});'), 'the sound element is made only on a press'
    rest = FRAG.replace('au.src = SOUND_FILE;', '')
    for bad in (r'\bsrc\s*=', r'@import', r'\bfetch\s*\(', r'XMLHttpRequest', r'\bimport\s*\(', r'sendBeacon',
                r'new\s+(Image|Audio|WebSocket|Worker)\b', r'\.load\s*\('):
        assert not re.search(bad, rest), bad
    assert re.findall(r'url\(([^)]*)\)', FRAG) == ['#crMk'], 'only the in-document mask reference'
    assert not re.search(r'<(audio|video|img|iframe|object|embed|link)\b', MARKUP)


def test_no_inline_handlers_or_unsafe_dom():
    assert not re.search(r'\son[a-z]+\s*=', MARKUP, re.I)
    assert not re.search(r'\.on[a-z]+\s*=', JS)
    assert not re.search(r'setAttribute\(\s*[\'"]on', JS)
    for bad in ('innerHTML', 'outerHTML', 'insertAdjacentHTML', 'document.write', 'eval(', 'new Function', 'javascript:', 'setInterval', 'requestAnimationFrame', 'requestIdleCallback'):
        assert bad not in JS, bad
    assert JS.count('addEventListener(') >= 6


def test_ships_hidden_and_accessible():
    root = re.search(r'<div class="cr" id="councilRoute"[^>]*>', MARKUP).group(0)
    assert ' hidden' in root, 'only the script reveals the stage'
    assert re.search(r'id="crStage" aria-hidden="true"', MARKUP)
    assert re.search(r'<p id="crCap" aria-live="off">', MARKUP), 'the live region exists from load'
    assert 'R.hidden = false' in JS
    order = [m.group(1) for m in re.finditer(r'<button type="button" class="cr-b[^"]*" id="(\w+)"', MARKUP)]
    assert order == ['crPlay', 'crPrev', 'crNext', 'crCc', 'crSnd']
    assert 'id="crCc" aria-pressed="true">' in MARKUP, 'captions on by default'
    assert 'id="crSnd" aria-pressed="false" hidden>' in MARKUP, 'the Audio slot ships hidden'
    # CC and Audio sit in the bar under the stage, after the step status and right above the caption line they serve
    # (as in a video player), so the Play row stays one line on phones.
    bar = MARKUP[MARKUP.index('<div class="cr-bar">'):MARKUP.index('id="crCb"')]
    assert bar.index('class="cr-st"') < bar.index('id="crCc"') < bar.index('id="crSnd"')
    assert MARKUP.index('id="crStage"') < MARKUP.index('<div class="cr-bar">')
    assert MARKUP.index('crNext') < MARKUP.index('<summary>Read the route as text</summary>')
    assert MARKUP.index('id="crCtl"') < MARKUP.index('id="crStage"') < MARKUP.index('id="crCap"'), 'controls above the stage, caption below'
    # Review F1: one scroll target spans the controls, the stage and the reserved caption box, and nothing else.
    run = MARKUP[MARKUP.index('<div id="crRun">'):MARKUP.index('<details')]
    assert 'id="crCtl"' in run and 'id="crStage"' in run and 'id="crCb"' in run and 'crText' not in run
    assert "$('crRun').scrollIntoView({block: 'nearest'});" in JS and JS.count('scrollIntoView') == 1
    assert 'role="group"' in MARKUP and 'aria-label="Council route"' in MARKUP


def test_css_contract():
    # The one allowed mention of transition removes motion: in Still the site's ::details-content height transition
    # (which the site's own Still rule does not reach) left the transcript opened at load clipped part-way.
    still_snap = '[data-motion=still] .cr-text::details-content{transition:none}'
    assert CSS.count(still_snap) == 1
    body = CSS.replace(still_snap, '')
    for bad in ('gradient', 'blur', 'box-shadow', 'text-shadow', 'drop-shadow', 'filter', 'text-transform', 'letter-spacing', '@keyframes', 'animation', 'transition', 'position:sticky', 'position:fixed'):
        assert bad not in body, bad
    sizes = [float(x) for x in re.findall(r'font(?:-size)?:[^;}]*?(\d+(?:\.\d+)?)px', body)]
    assert sizes and min(sizes) >= 12, sizes
    assert re.search(r'\.cr-b\{[^}]*min-width:44px;min-height:44px', body)
    assert re.search(r'\.cr-text summary\{[^}]*min-height:44px', body)
    strokes = set(re.findall(r'stroke:([^;}]+)', body))
    assert strokes <= {'var(--cr-l)', 'var(--cr-n)', 'var(--cr-a)', '#fff', 'none'}, strokes
    assert '--cr-l:var(--ink-3)' in body and '--cr-n:var(--ink-2)' in body, 'strokes in ink-3 or stronger'
    assert '[data-theme=skeleton] .cr{--cr-a:var(--ink);' in body, 'Obsidian Ember crimson cannot carry meaning (2.22:1)'
    # Review F2: ink-3 at 1.2 px antialiases below 3:1 at 1.25x on the Ember halo and the Codex paper. Ember: rest lines
    # and the enclosure in ink-2. Codex: the paper darkens toward the viewport bottom (fixed page gradient and vignette,
    # about rgb(184,161,111)), where even ink-2 is 4.33:1 at full coverage, so lines, frames and stage labels are ink.
    # Review F3: the stage gets a flat ground (default #000 = the card body, Maya floor over the aurora); Codex and
    # Ember keep their textured ground, where a floor would show as a slab.
    assert '[data-theme=skeleton] .cr{--cr-a:var(--ink);--cr-l:var(--ink-2);--cr-g:none}' in body
    assert '[data-theme=codex] .cr{--cr-l:var(--ink);--cr-n:var(--ink);--cr-t:var(--ink);--cr-g:none}' in body
    assert '--cr-t:var(--ink-2)' in body and re.search(r'\.cr-l\{[^}]*color:var\(--cr-t\)', body)
    assert '--cr-g:var(--bg-floor)' in body and re.search(r'\.cr-stage\{[^}]*background:var\(--cr-g\)', body)
    assert '.cr .b,.cr .n,.cr .en{stroke:var(--cr-l);stroke-width:calc(var(--u)*1.2px)}' in body
    # Review B-F2: the status digit has a fixed box, so "of 7" never moves. Review F4: transcript text in ink.
    assert '#crN{display:inline-block;width:.6em' in body
    assert re.search(r'\.cr \.cr-text li,\.cr \.cr-text p\{[^}]*color:var\(--ink\)\}', body)
    assert '@media (forced-colors:active)' in body and '.cr .bg{fill:Canvas}' in body, 'review B-F5: the draft sheet follows Canvas'
    # CC hides the caption line only; the step status and the transcript stay.
    assert body.count('.cr[data-cc=off] .cr-cb{display:none}') == 1 and 'data-cc=off] .cr-st' not in body
    assert 'data-cc=off] .cr-text' not in body and 'data-cc=off] #crText' not in body
    # Pressed toggles are marked by shape (a filled dot) as well as colour; hover stays neutral.
    assert '.cr-b[aria-pressed=true] .cr-m{background:currentColor}' in body
    assert '.cr-b:hover{border-color:var(--ink-2)}' in body


def test_playback_contract():
    """Autoplay like a video preview: at 60% of the stage in view, never in Still; pause under 25%; haptics short,
    guarded and switchable. The controller's behaviour itself is exercised in test_council_route.cjs."""
    assert 'threshold: [0, .25, .6]' in JS
    assert ('function auto() {\n  if (!playing && !held && !ended && !still() && !d.hidden && seen >= .6 && gone()) play();'
            in JS)
    assert 'if (seen >= .25) vis = true;\n  else if (vis) pause();' in JS
    ms = [int(x) for x in re.findall(r'nv\.vibrate\((\d+)\)', JS)]
    assert ms and all(8 <= x <= 12 for x in ms), ms
    buzz = JS[JS.index('function buzz'):JS.index('function sync')]
    assert "localStorage.getItem('zotheos_haptics')" in buzz and "p !== 'off'" in buzz
    assert 'nv.userActivation.hasBeenActive' in buzz and '!still()' in buzz
    assert JS.count('scrollIntoView') == 1 and "if (s) $('crRun').scrollIntoView" in JS, 'only a press of Play scrolls'


def parse_moves():
    src = re.search(r'let M = (\[\[.*?\]\]);', JS, re.S).group(1)
    return ast.literal_eval(src)


def test_timing_rule_and_motion_vocabulary():
    durs = []
    for c in captions():
        x = 1.5 + 0.26 * len(c.split(' '))
        durs.append(-(-x * 2 // 1) / 2)
    assert durs == [6.0, 5.0, 6.5, 6.0, 7.0, 4.5, 7.0], durs
    assert sum(durs) == 42.0 and sum(durs) <= 45
    moves = parse_moves()
    assert {m[1] for m in moves} <= {'d', 'f', 'n', 't'}
    for beat in range(1, 8):
        ends = [m[3] + m[4] for m in moves if m[0] == beat]
        assert max(ends or [0]) <= 2.5, 'beat %d animates longer than 2.5 s' % beat
    for m in moves:
        if m[1] == 'd':
            assert 0.3 <= m[4] <= 1.2
        if m[1] == 't':
            assert m[4] == 0.9, 'travel takes 900 ms'
    assert not [m for m in moves if m[0] == 7], 'nothing moves in beat 7'


def test_owner_switch_defaults():
    assert 'const CONFIRMED = false;' in JS
    assert 'const TIE = true;' in JS
    assert 'const GLYPH_ACTIVE = false;' in JS
    assert 'const PLAY_IN_STILL = false;' in JS
    for g in ('glyph-analyst', 'glyph-humanist', 'glyph-skeptic'):
        assert "'#glyph-'" in JS and g.split('-')[1] in JS
    assert '<symbol' not in FRAG and 'fret' not in FRAG.lower(), 'no new motif; glyphs are reused by <use>'


def test_fragment_matches_index_blocks():
    s = page()
    for name, (a, b) in MARKERS.items():
        assert s.count(a) == 1 and s.count(b) == 1, name + ': index.html must carry the block exactly once'
        assert s[s.index(a):s.index(b) + len(b)] == block(name), name + ' differs from the fragment'


def test_integrated_placement():
    s = page()
    # Markup: inside the Fusion card, directly after the unchanged figure and figcaption, before the Method notes.
    fig = s.index('<figcaption class="fusion-caption">')
    end = s.index('</figure>', fig) + len('</figure>')
    assert s[end:].startswith('\n' + ' ' * 10 + MARKUP + '\n          <details class="fusion-method">')
    # CSS: one <style> of its own in the head. JS: one new inline script, the last one, after the motion floor.
    own_style = '<style>\n' + CSS + '\n</style>'
    assert s.count(own_style) == 1
    assert s.index('<head>') < s.index(own_style) < s.index('</head>')
    assert s.rstrip().endswith('<script>\n' + JS + '\n</script>\n</body>\n</html>')


def test_script_hash_in_both_policies():
    body = '\n' + JS + '\n'
    h = "'sha256-" + base64.b64encode(hashlib.sha256(body.encode('utf-8')).digest()).decode('ascii') + "'"
    meta = re.search(r'<meta\b[^>]*http-equiv="Content-Security-Policy"[^>]*\bcontent="([^"]*)"', page()).group(1)
    assert h in re.search(r"script-src[^;]*", meta).group(0), 'meta policy lacks ' + h
    with open(os.path.join(ROOT, 'vercel.json'), encoding='utf-8') as f:
        rules = json.load(f)['headers']
    for src in ('/', '/index', '/index.html'):
        pol = [x['value'] for r in rules if r['source'] == src for x in r['headers'] if x['key'] == 'Content-Security-Policy']
        assert pol and h in re.search(r"script-src[^;]*", pol[0]).group(0), src + ' header lacks ' + h


@pytest.mark.parametrize('target', ['fragment', 'index'])
def test_controller_checks_in_node(target):
    node = shutil.which('node')
    if not node:
        pytest.skip('node is not installed')
    src = FRAGMENT if target == 'fragment' else index_path()
    r = subprocess.run([node, os.path.join(HERE, 'test_council_route.cjs'), src],
                       capture_output=True, text=True, encoding='utf-8', timeout=120)
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
