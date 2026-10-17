"""Homepage Theater chapter gates ("Where ZOTHEOS listens."): its place before the Explore gateway, the exact landing
CSP additions and nothing more, the PREVIEW_AUTOPLAY switch (owner default on; off meets the no-autoplay contract, and
the visible wording follows the switch both ways), the owner's decision (previews start muted in view; the OS
reduced-motion setting an unconditional floor, with no motion question or override), no provider contacted at load
(images and the player only once the section has stayed near for half a second, never on a jump past it), the privacy
text naming when and which hosts are contacted, claiming neither anonymous playback nor no provider data, and matching
the separate Theater's own rule, the mirror and the FAQ naming the Theater's connections, the chapter in Translate a
section (reading text only, no player controls), the controls straight under the screen with one Before Watching note
after them (a status that asks for Play where the window is too short to start), the featured story's hold state taken from the Theater, one visible Haptics preference that the Council Route honours too,
a flat section with no glow or gradient, no em or en dash, the solo founder voice, 44px controls, no rule reaching the
header, no extra font file at load, a status line that does not shift, the hero door on the actions row, and the
featured preview and six stories checked against the Theater's own records and anchors. The controller itself is
exercised in test_theater_showcase.cjs (node, run here on index.html).

  py -3.10 -m pytest tools/tests/test_theater_showcase.py -q -p no:cacheprovider
Stdlib only. Line endings are folded to LF before any comparison.
"""
import base64
import collections
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import csp_sync  # noqa: E402


def read(p):
    with open(os.path.join(ROOT, p), encoding='utf-8', newline='') as f:
        return f.read().replace('\r\n', '\n').replace('\r', '\n')


PAGE = read('index.html')


def block(a, b, inclusive=True):
    assert PAGE.count(a) == 1 and PAGE.count(b) == 1, a
    i, j = PAGE.index(a), PAGE.index(b)
    assert j > i
    return PAGE[i:j + len(b)] if inclusive else PAGE[i + len(a):j]


MARKUP = block('<!-- theater-showcase:markup -->', '<!-- /theater-showcase:markup -->')
CSS = block('/* theater-showcase:css */', '/* /theater-showcase:css */')
JS = block('/* theater-showcase:js */', '/* /theater-showcase:js */')
PRIVACY = re.search(r'<details class="website-privacy" id="site-privacy">(.*?)</details>', PAGE, re.S).group(1)
HERO_DOOR = re.search(r'<a class="hero-theater" href="#theater-screen">([^<]*)</a>', PAGE)
FILMS = json.loads(read('data/theater/films.json'))
RECORDS = {f['id']: f for f in FILMS['films']}
THEATER = read('theater.html')
FEATURED = 'deaf-indigenous-dance-group'
STORIES = ['birgejupmi-three-voices', 'sulagad-system', 'indigenous-peoples-network-southern-africa-launch',
           'qeqchi-territory-aepdi', 'nfb-evans-drum', 'nfb-to-wake-up-the-nakota-language']
# The landing policy before this chapter, with exactly its additions (frame-src replaces 'none'; two image hosts).
# script-src is the page's own inline hash list (csp_sync), checked separately.
LANDING_POLICY = [
    ('default-src', ["'none'"]), ('base-uri', ["'none'"]), ('object-src', ["'none'"]), ('script-src', None),
    ('script-src-attr', ["'none'"]), ('style-src', ["'self'", "'unsafe-inline'"]), ('font-src', ["'self'"]),
    ('img-src', ["'self'", 'data:', 'https://zotheos.org', 'https://i.ytimg.com', 'https://assets.nfbcdn.ca']),
    ('media-src', ["'self'", 'https://zotheos.org']), ('connect-src', ['https://formspree.io']),
    ('form-action', ['https://formspree.io']), ('frame-src', ['https://www.youtube-nocookie.com']),
    ('worker-src', ["'none'"]), ('manifest-src', ["'self'"]), ('frame-ancestors', ["'none'"]),
]
CHAPTER_HOSTS = ('www.youtube-nocookie.com', 'i.ytimg.com', 'assets.nfbcdn.ca')


def directives(policy):
    return [(d.split()[0], d.split()[1:]) for d in (x.strip() for x in policy.split(';')) if d]


def header_policies():
    rules = json.loads(read('vercel.json'))['headers']
    return {r['source']: next(h['value'] for h in r['headers'] if h['key'] == 'Content-Security-Policy')
            for r in rules if any(h['key'] == 'Content-Security-Policy' for h in r['headers'])}


def meta_policy():
    return re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]*)"', PAGE).group(1)


def section_script_hash():
    body = re.search(r'<script>(\n/\* theater-showcase:js \*/.*?/\* /theater-showcase:js \*/\n)</script>', PAGE, re.S).group(1)
    return "'sha256-" + base64.b64encode(hashlib.sha256(body.encode('utf-8')).digest()).decode('ascii') + "'"


def visible(fragment):
    """Text a visitor can see or hear: tags and comments removed, entities decoded, plus every attribute value."""
    no_comments = re.sub(r'<!--.*?-->', '', fragment, flags=re.S)
    attrs = ' '.join(html.unescape(v) for v in re.findall(r'\s[\w:-]+="([^"]*)"', no_comments))
    return html.unescape(re.sub(r'<[^>]+>', ' ', no_comments)) + ' ' + attrs


def js_strings(src):
    no_comments = re.sub(r'/\*.*?\*/', '', src, flags=re.S)
    return re.findall(r"'((?:[^'\\\n]|\\.)*)'", no_comments)


# ---- placement -------------------------------------------------------------------------------------------------

def test_own_chapter_after_mission_and_its_divider_before_the_explore_gateway():
    mission = PAGE.index('<section id="mission">')
    mission_end = PAGE.index('</section>', mission) + len('</section>')
    start = PAGE.index('<!-- theater-showcase:markup -->')
    end = PAGE.index('<!-- /theater-showcase:markup -->') + len('<!-- /theater-showcase:markup -->')
    gateway = PAGE.index('<section class="world-showcase" id="explore-zotheos"')
    assert mission_end < start < end < gateway
    gap = PAGE[mission_end:start]
    assert gap.count('<div class="greca-divider">') == 1 and re.fullmatch(
        r'\s*<div class="greca-divider">.*?<span class="seal-dot"></span>\s*</div>\s*', gap, re.S), 'only the divider after #mission'
    assert PAGE[end:gateway].strip() == '', 'the gateway follows directly'
    assert MARKUP.count('<section ') == 1 and '<section class="tsc" id="theater"' in MARKUP
    assert re.search(r'</section>\s*<div class="greca-divider">.*?</div>\s*<!-- /theater-showcase:markup -->$', MARKUP, re.S), \
        'the chapter brings its own greca divider'
    assert PAGE.count('id="theater"') == 1 and PAGE.count('id="theater-screen"') == 1


def test_script_is_its_own_inline_block_at_the_end_of_the_body():
    tail = PAGE[PAGE.index(JS):]
    assert PAGE[PAGE.index(JS) - len('<script>\n'):PAGE.index(JS)] == '<script>\n'
    assert tail.startswith(JS + '\n</script>\n<script>\n/* council-route:js */'), 'just before the Council Route block'


# ---- policy ----------------------------------------------------------------------------------------------------

@pytest.mark.parametrize('source', ['/', '/index', '/index.html'])
def test_landing_policy_is_the_old_policy_plus_exactly_the_chapter_additions(source):
    pol = header_policies()[source]
    got = directives(pol)
    assert [d for d, _ in got] == [d for d, _ in LANDING_POLICY], 'same directives, same order'
    for (name, vals), (_, want) in zip(got, LANDING_POLICY):
        if want is not None:
            assert vals == want, f'{source} {name}: {vals}'
    scripts = dict(got)['script-src']
    assert scripts == csp_sync.page_hashes(PAGE), 'script-src is exactly the page inline hashes'
    assert section_script_hash() in scripts


def test_meta_policy_matches_the_header_less_frame_ancestors():
    assert meta_policy() == csp_sync.meta_policy(header_policies()['/'])


def test_no_other_policy_gains_the_chapter_hosts():
    for source, pol in header_policies().items():
        if source in ('/', '/index', '/index.html') or source.startswith('/theater'):
            continue
        for host in CHAPTER_HOSTS:
            assert host not in pol, f'{source} gained {host}'
    for source in ('/download', '/download.html'):
        assert dict(directives(header_policies()[source]))['frame-src'] == ["'none'"]


# ---- the switch ------------------------------------------------------------------------------------------------

def test_preview_autoplay_defaults_to_the_owner_preview_and_the_off_switch_removes_every_autoplay_path():
    assert JS.count('var PREVIEW_AUTOPLAY = true;') == 1 and 'PREVIEW_AUTOPLAY = false' not in JS
    # Off: no message interface, no autoplay permission, no enablejsapi or mute in the address, OS floor reads Still.
    assert "var api = PREVIEW_AUTOPLAY && (provider === 'youtube' || provider === 'vimeo');" in JS
    assert "frame.allow = (api ? 'autoplay; ' : '') + 'encrypted-media; picture-in-picture; fullscreen';" in JS
    assert "(api ? 'enablejsapi=1&origin=' + o + '&' : '')" in JS
    assert "function previewPossible(m) { return PREVIEW_AUTOPLAY && eligible && api && autoplayMode(m) && !saveData; }" in JS
    assert "quiet = known && previewPossible(mode());" in JS and "(quiet ? '&mute=1' : '')" in JS
    assert "if (!frame || !frame.contentWindow || !api) return;" in JS, 'send() is inert without the interface'
    assert 'function autoLikely() { return previewPossible(mode()) &&' in JS
    assert 'function wantAuto(m) {\n        return previewPossible(m) && !failed && known && inView >= 0.6 && barSeen' in JS


def test_owner_decision_reduced_motion_is_an_unconditional_floor_with_no_question():
    """David's decision (2026-10-16): previews start muted when in view, do not ask again; the OS reduced-motion
    setting is a floor. No question, no Keep Motion or Change Motion, no override, in markup, style or script."""
    mode_fn = JS[JS.index('function mode() {'):JS.index('function mode() {') + 400]
    assert mode_fn.startswith("function mode() {\n        if (reduceMQ.matches) return 'still';"), 'the floor comes first'
    for part in (MARKUP, CSS, JS, PRIVACY):
        for bad in ('tscAsk', 'tsc-ask', 'data-answer', 'Keep Motion', 'Use Calm', 'Use Still', 'Change Motion',
                    'tscMotionAgain', 'askOpen', 'first asks whether'):
            assert bad not in part, bad
    assert "store('zotheos_motion'" not in JS, 'the section never writes the page Motion'
    assert 'function autoplayMode(m) { return m === \'living\' || m === \'calm\'; }' in JS


SWAPS = re.findall(r'\[(section|privacy)\] "([^"]+)" => "([^"]+)"', JS)
AUTOPLAY_CLAIMS = ('starts by itself', 'starts without sound', 'stops after 45 seconds', 'started by itself',
                   '60% of the screen')


def page_block(page, a, b):
    return page[page.index(a):page.index(b) + len(b)]


def wording_follows(page, switch_on):
    markup = page_block(page, '<!-- theater-showcase:markup -->', '<!-- /theater-showcase:markup -->')
    privacy = re.search(r'<details class="website-privacy" id="site-privacy">(.*?)</details>', page, re.S).group(1)
    where = {'section': ' '.join(visible(markup).split()), 'privacy': ' '.join(visible(privacy).split())}
    for part, on, off in SWAPS:
        want, gone = (on, off) if switch_on else (off, on)
        assert html.unescape(want) in where[part], (part, want)
        assert html.unescape(gone) not in where[part], (part, gone)
    if not switch_on:   # with the switch off, nothing about this page's own section claims a start on its own
        shown = where['section']
        own = where['privacy'][:where['privacy'].index('The separate Theater')]
        for claim in AUTOPLAY_CLAIMS:
            assert claim not in shown and claim not in own, claim


def test_privacy_wording_follows_the_switch():
    assert [p for p, _, _ in SWAPS] == ['section', 'privacy'], 'the swap list sits beside the switch'
    owner = 'var PREVIEW_AUTOPLAY = true;' in JS
    wording_follows(PAGE, owner)
    assert "CAP_MS = 45000, PHONE_CAP_MS = 15000" in JS and "mq('(max-width: 719px)')" in JS


def test_the_swap_list_alone_turns_the_page_into_the_no_autoplay_wording():
    rest = PAGE.replace(JS, '\0JS\0')   # the swap list itself lives in the script block
    for part, on, off in SWAPS:
        assert rest.count(on) == 1, on   # each sentence to swap is on the page exactly once
        rest = rest.replace(on, off)
    flipped = rest.replace('\0JS\0', JS.replace('var PREVIEW_AUTOPLAY = true;', 'var PREVIEW_AUTOPLAY = false;'))
    wording_follows(flipped, False)


def test_story_links_stay_native_while_the_theater_resolves_only_film_anchors():
    theater_js = read('static/theater/theater.js')
    resolves_story = bool(re.search(r"[?&]story=|searchParams\.get\(['\"]story['\"]\)|get\('story'\)", theater_js))
    assert ('var STORY_WATCH_LINKS = ' + ('true' if resolves_story else 'false') + ';') in JS
    assert '#film-' in theater_js


# ---- no provider before the section nears ------------------------------------------------------------------------

def test_no_third_party_url_is_fetched_at_load():
    assert '<iframe' not in MARKUP and not re.search(r'\ssrc="https?:', MARKUP)
    imgs = re.findall(r'<img\b[^>]*>', MARKUP)
    assert len(imgs) == 7
    for tag in imgs:
        m = re.search(r'\sdata-src="(https://(i\.ytimg\.com|assets\.nfbcdn\.ca)/[^"]+)"', tag)
        assert m and ' src=' not in tag, tag
        assert 'loading="lazy"' in tag and 'referrerpolicy="no-referrer"' in tag
    rest = PAGE.replace(MARKUP, '').replace(JS, '')
    for host in CHAPTER_HOSTS:
        assert not re.search(r'\b(src|srcset|href)="[^"]*' + re.escape(host), rest), host + ' outside the chapter'
    # The images fill at 1250px, the player at 400px; the only other paths are a visitor's own Play and a browser
    # without IntersectionObserver.
    assert "{ rootMargin: '1250px 0px' }" in JS and "{ rootMargin: '400px 0px' }" in JS
    # without an IntersectionObserver what is in view is unknown: nothing fills, connects or starts on its own
    assert "known = true;" in JS and 'near = true; inView = 1; barSeen = true;' not in JS
    # ...and both wait until the section has stayed inside that distance for half a second, not flying past
    assert 'var DWELL_MS = 500, FLY = 2;' in JS
    assert "gate('gateImages', 1250, function () { images(); io.disconnect(); });" in JS
    assert "gate('gateNear', 400, function () { near = true; images(); io.disconnect(); apply(); });" in JS
    calls = re.findall(r'(?<![\w.])connect\(\);', re.sub(r'/\*.*?\*/', '', JS, flags=re.S))
    assert len(calls) == 2 and "if (near && !frame) connect();" in JS
    assert "if (!frame) { pendingUser = true; near = true; images(); connect(); paint(); return; }" in JS
    assert len(re.findall(r'\bimages\(\);', JS)) == 3
    assert "if (/^https:\\/\\/(i\\.ytimg\\.com|assets\\.nfbcdn\\.ca)\\//.test(u)) img.setAttribute('src', u);" in JS


def test_hero_door_is_a_same_page_anchor_on_the_actions_row():
    assert HERO_DOOR and HERO_DOOR.group(1) == 'Watch in the Theater: Indigenous voices first, %d selections' % len(FILMS['films'])
    actions = re.search(r'<div class="hero-actions stagger reveal">(.*?)\n      </div>', PAGE, re.S).group(1)
    assert HERO_DOOR.group(0) in actions, 'on the row, so the hero keeps main height and its status line'
    assert actions.rstrip().endswith(HERO_DOOR.group(0)), 'after the quiet link'
    assert 'font: italic 400 19px/24px var(--serif)' in CSS, 'whole-pixel lines when it wraps on phones'



def test_privacy_text_names_when_and_which_hosts_are_contacted():
    """Contact is disclosed for the moment it can happen: as the section approaches the screen, once the page has been
    near it for half a second. Only a jump past it (a link or the End key) is promised to contact neither provider;
    ordinary key and wheel scrolling past it, even quickly, was measured to contact them, and the text says so. No
    claim of anonymous playback or of no provider data."""
    text = ' '.join(visible(PRIVACY).split())
    assert ('The Theater section on this page contacts YouTube and the National Film Board of Canada as it approaches '
            'the screen, once the page has been near it for half a second') in text
    assert ('A link or the End key that jumps past the section contacts neither. Scrolling past it, even quickly, '
            'usually contacts them, and so does a link that lands near it, such as one to the Explore section after '
            'it.') in text
    for host in CHAPTER_HOSTS:
        assert host in text, host
    assert 'A visit that never comes near the section, or only jumps past it, contacts none of them.' in text
    assert 'theme, motion, effects, rain, haptics and intro sound preferences' in text
    assert 'for the rest of the visit it remembers that the intro has played' in text
    assert 'In Still, when your device asks for reduced motion and while your browser asks to save data, it waits for Play.' in text
    fine = ' '.join(visible(MARKUP).split())
    assert ('Privacy: this section contacts YouTube and the National Film Board of Canada as it approaches the screen, '
            'once the page has been near it for half a second. A link or the End key that jumps past it contacts '
            'neither; scrolling past it, even quickly, usually does, and so does a link that lands near it.') in fine
    for where in (text, fine, ' '.join(re.findall(r'/\*.*?\*/', JS, re.S))):
        for promise in ('fast scroll', 'fling past', 'flings past', 'a key or a fling', 'a link, a key'):
            assert promise not in where, 'no promise about scrolling past: ' + promise
    for where in (text, fine):
        assert 'requests to Google services can carry cookies your browser already holds for Google' in where
        assert 'privacy-enhanced domain does not make playback anonymous' in where
        assert 'receive your IP address and request information' in where
        for claim in ('no cookies', 'set no cookies', 'anonymous playback', 'collects no data', 'no data is'):
            assert claim not in where, claim
    assert ('Featuring these stories here does not mean their makers, publishers or the people in them endorse '
            'ZOTHEOS.') in fine
    assert "'Connecting to ' + name + '.'" in JS, 'the status names the provider while it connects'


def test_controls_straight_under_the_screen_and_one_before_watching_note_after_them():
    """The controls sit straight under the screen (refinement R3-ZONE): a preview starts on its own only with 60% of
    the screen and the whole control row in view, so nothing may lengthen the reach from the screen to the row, or the
    preview cannot start after the hero door on common laptop heights and never on landscape phones. The chapter's
    note appears once, after the controls and their status line. Play carries it as its description until the
    preview first plays (the visitor's own Play or a start they see), and screen readers hear it once more at the
    first automatic start. The status line does not repeat it, and in a window too short for the start rule it asks
    for Play instead of promising a start."""
    shown = visible(MARKUP)
    assert shown.count('Before watching:') == 1
    stage = MARKUP[MARKUP.index('<div class="tsc-stage">'):MARKUP.index('<div class="tsc-program">')]
    assert '<p class="tsc-before" id="tscBefore"><strong>Before watching:</strong>' in stage
    order = [stage.index(k) for k in ('id="tscScreen"', '<div class="tsc-tiers"', 'id="tscBar"', 'id="tscStatus"',
                                      'id="tscBefore"', 'id="tscComfort"')]
    assert order == sorted(order), 'screen, its frame, the controls, the status line, the note, Pause Light'
    assert re.search(r'<div class="tsc-tiers"[^>]*>(?:\s*<span [^>]*></span>)+\s*</div>\s*</div>\s*'
                     r'(?:<!--(?:(?!-->).)*-->\s*)?<div class="tsc-bar"', stage, re.S), 'the control row follows the frame directly'
    assert re.search(r'<button class="tsc-btn tsc-play" id="tscPlay" [^>]*aria-describedby="tscBefore"', stage)
    assert ("if (playing && (spokeStart || owned) && playBtn.hasAttribute('aria-describedby')) "
            "playBtn.removeAttribute('aria-describedby');") in JS
    assert 'tsc-before' not in MARKUP[MARKUP.index('<div class="tsc-program">'):]
    assert "say(msg, first && noteText ? msg + ' Before watching: ' + noteText : '', first);" in JS
    assert 'data-note' not in CSS and "setAttribute('data-note'" not in JS
    # a window too short for the start rule: the status asks for Play, and follows a resize
    assert 'return 0.6 * s.height + (b.bottom - s.bottom) + 72 <= h;' in JS
    assert "if (!PREVIEW_AUTOPLAY || blocked || owned || !known || !roomy()) return 'Ready. Press Play to watch.';" in JS
    assert "window.addEventListener('resize', function () { later('fit', 150, paint); });" in JS
    # without script the empty status line takes no room between the screen and the note
    assert '.tsc:not([data-script]) .tsc-status { display: none; }' in CSS
    # the hero door lands low enough to show the control row (never past the start rule), and the council story's own
    # anchor aims are kept for every other target
    assert "var doorEl = $('theater-screen'), priorAim = window.zAnchorAim;" in JS
    assert "if (target !== doorEl) return typeof priorAim === 'function' ? priorAim(target) : null;" in JS
    assert 'return base + Math.max(0, Math.min(over, (s.top - a.top) + (roomy() ? 0.4 * s.height : 0)));' in JS
    assert JS.count('window.zAnchorAim = ') == 1, 'one assignment, chaining the earlier owner'


class _Export:
    """The page's Translate a section copy step, in stdlib: a clone of the section with script, style, form fields,
    [contenteditable], [aria-hidden="true"] and [hidden] removed, its text with whitespace folded. The section script
    runs after the translation script, so the copy sees the markup as it is written."""
    DROP_TAGS = {'script', 'style', 'form', 'input', 'textarea', 'select'}
    VOID = {'br', 'img', 'input', 'meta', 'link', 'hr', 'source', 'wbr', 'path', 'rect'}

    def __init__(self, fragment):
        import html.parser
        out, stack, drop = [], [], [0]
        outer = self

        class Parser(html.parser.HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag in outer.VOID:
                    return
                a = dict(attrs)
                gone = tag in outer.DROP_TAGS or 'hidden' in a or a.get('aria-hidden') == 'true' or 'contenteditable' in a
                stack.append(gone)
                drop[0] += gone

            def handle_endtag(self, tag):
                if tag not in outer.VOID and stack and stack.pop():
                    drop[0] -= 1

            def handle_data(self, data):
                if not drop[0]:
                    out.append(data)

        Parser(convert_charrefs=True).feed(re.sub(r'<!--.*?-->', '', fragment, flags=re.S))
        self.text = ' '.join(''.join(out).split())


def test_the_chapter_is_in_translate_a_section_with_reading_text_and_no_player_controls():
    sections = re.search(r'var sections = \[(.*?)\], texts = \[\];', PAGE, re.S).group(1)
    ids = re.findall(r"\['([\w-]+)', '([^']+)'\]", sections)
    names = [i for i, _ in ids]
    assert ('theater', 'Theater') in ids
    assert names.index('mission') + 1 == names.index('theater') == names.index('compare') - 1, \
        'between Mission and Comparison, the chapters on either side of it'
    head = '/* Translation sends public reading text only after an explicit press.'
    trans = PAGE[PAGE.index(head):PAGE.index('/* Floral xochitl band */')]
    assert """'script, style, form, input, textarea, select, [contenteditable], [aria-hidden="true"], [hidden]'""" in trans
    assert PAGE.index(head) < PAGE.index(JS), 'the copy is taken before the section script shows its controls'
    section = MARKUP[MARKUP.index('<section class="tsc"'):MARKUP.index('</section>') + len('</section>')]
    text = _Export(section).text
    for must in ('Where ZOTHEOS listens', 'Indigenous voices come first', 'The Deaf Indigenous Dance Group',
                 'Before watching: Contains discussion of barriers', 'Six stories from the Theater',
                 'Birgejupmi: A Cinematic Essay By Three Voices', 'The Sulagad System', "Evan's Drum",
                 'To Wake Up the Nakota Language', 'Privacy: this section contacts YouTube'):
        assert must in text, must
    for control in ('Play preview', 'Pause preview', 'Turn Sound On', 'Sound Off', 'CC Captions', 'Pause Light',
                    'Resting', 'Watch On YouTube', 'Press Play', 'This player uses its own controls',
                    'Pauses the ambient light', 'Starting the preview', 'Connecting to'):
        assert control not in text, control
    assert not re.search(r'\b(Play|Pause|Sound|CC)\b', text), 'no control label'
    assert len(text) < 2 * 4500, 'two parts at most'


def test_featured_story_hold_state_is_the_theaters_own():
    """A difficult-content, audio-led or unconfirmed-caption hold on the Theater keeps this preview behind Play too."""
    sec = re.search(r'<section class="tsc" id="theater"[^>]*>', MARKUP).group(0)
    art = re.search(r'<article class="th-film" id="film-%s"[^>]*>' % FEATURED, THEATER).group(0)
    theater_state = re.search(r'\sdata-preview="([^"]+)"', art).group(1)
    ours = re.search(r'\sdata-preview="([^"]+)"', sec).group(1)
    assert ours == ('eligible' if theater_state == 'ok' else 'held'), (ours, theater_state)
    assert re.search(r'\sdata-cap-lang="en"', art) and 'data-captions="en"' in sec


def test_one_visible_haptics_preference_for_the_section_and_the_council_route():
    row = re.search(r'<div class="ap-row" id="apHapticsRow" hidden>.*?</div>\s*</div>', PAGE, re.S).group(0)
    assert 'data-haptics="on"' in row and 'data-haptics="off"' in row
    assert 'title="Short pulses from the Theater and Council Route controls and steps"' in row
    js_row = JS[JS.index('var hapRow ='):JS.index("var root = $('theater');")]
    assert "store('zotheos_haptics', haptics ? 'on' : 'off');" in js_row and 'hapRow.hidden = false;' in js_row
    assert JS.index('var hapRow =') < JS.index("if (!root || !root.hasAttribute('data-tsc')) return;"), \
        'the preference is set up before the section, so it stays visible without it'
    council = block('/* council-route:js */', '/* /council-route:js */')
    buzz = council[council.index('function buzz'):council.index('function sync')]
    assert "localStorage.getItem('zotheos_haptics')" in buzz and "p !== 'off'" in buzz, 'the Council Route honours it'
    assert "navigator.userActivation.isActive" in JS, 'the section pulses only inside a real press'


def test_the_separate_theater_is_described_by_its_own_rule():
    """The homepage keeps main's own sentences about the separate Theater word for word (main's copy wins) and adds the
    Theater page's own conditions, so a change on either page fails here. Both pages follow one rule: muted previews
    in view, none in Still or under reduced motion, 45 s and 15 s limits."""
    text = ' '.join(visible(PRIVACY).split())
    theater_on = re.search(r'<html[^>]*\sdata-preview-autoplay="on"', THEATER) is not None
    rule = ('Eligible YouTube and Vimeo previews start without sound when the screen and controls are in view, '
            'except in Still or when the device requests reduced motion.')
    limits = 'Previews stop after 45 seconds on desktop and 15 seconds on phones unless you deliberately take control.'
    if theater_on:
        assert rule in THEATER and limits in THEATER, 'the Theater still states this rule itself'
        assert ('The separate Theater automatically loads publisher thumbnails and the selected ready player on opening '
                'the page. Their providers receive your IP address and request information under their own privacy '
                'policies. Eligible previews may start muted when in view; other stories wait for Play.') in text, \
            "main's own sentences, word for word"
        assert ('None start on their own in Still or when the device requests reduced motion, and previews stop after '
                '45 seconds on desktop and 15 seconds on phones unless you deliberately take control.') in text
        assert 'Playback waits for Play.' not in text
        assert 'nothing starts until you answer' not in text, 'no difference left under reduced motion'
    else:
        assert 'Playback begins when you press Play.' in THEATER
        assert 'may start muted' not in text


def test_the_mirror_and_the_faq_name_the_theater_connections():
    row = re.search(r'<div class="mirror-row"><span>Theater section</span><span class="mr-val" id="mrTheater">([^<]*)</span></div>', PAGE)
    assert row and row.group(1) == 'YouTube and NFB, as the section nears'
    assert "mirrorRow.textContent = 'YouTube and NFB, contacted'" in JS, 'the row changes only once a provider is contacted'
    note = re.search(r'<div class="mirror-note">([^<]*)</div>', PAGE).group(1)
    assert 'its Theater section contacts YouTube and the National Film Board of Canada as that section nears the screen' in note
    faq = 'Its Theater section contacts YouTube and the National Film Board of Canada as that section approaches the screen.'
    assert PAGE.count(faq) == 2, 'the visible FAQ answer and its structured data say the same'


# ---- look ----------------------------------------------------------------------------------------------------

def test_section_css_has_no_glow_haze_blur_or_gradient():
    code = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)
    for bad in ('gradient(', 'box-shadow', 'text-shadow', 'filter', 'blur(', 'backdrop', 'drop-shadow', 'mix-blend'):
        assert bad not in code, bad
    assert re.search(r'#theater \{[^}]*background: var\(--tsc-floor\);', code), 'one opaque floor'
    assert '.theater-invitation' not in re.sub(r'/\*.*?\*/', '', PAGE, flags=re.S), 'the retired rules are gone'
    for rule in re.findall(r'[^{}]*\.ws-theater[^{}]*\{[^}]*\}', PAGE):
        assert 'gradient' not in rule and 'shadow' not in rule, rule


def test_no_rule_in_the_block_reaches_the_header_and_no_extra_font_file_loads():
    code = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)
    assert '.header-nav' not in code and 'header' not in code, 'the header stays as main has it'
    # the series title uses the serif italic the page already loads, not a DM Sans italic file
    assert '.tsc-credit-line cite { font-family: var(--serif); font-style: italic;' in code
    for rule in re.findall(r'[^{}]*\{[^}]*font-style: italic[^}]*\}', code):
        assert 'var(--serif)' in rule, rule
    for rule in re.findall(r'[^{}]*\{[^}]*font: italic[^}]*\}', code):
        assert 'var(--serif)' in rule, rule


def test_the_status_line_reserves_its_height():
    code = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)
    assert re.search(r'\.tsc-status \{ min-height: 42px;', code)
    assert '.tsc-status { min-height: 63px; }' in code
    assert 'font-size: 15px' not in code[code.index('.tsc-status'):code.index('.tsc-before')]


def test_controls_are_at_least_44px():
    code = re.sub(r'/\*.*?\*/', '', CSS, flags=re.S)
    def rule(sel):
        m = re.search(r'(?m)^' + re.escape(sel) + r' \{([^}]*)\}', code)
        assert m, sel
        return m.group(1)
    for sel in ('.tsc-btn', '.tsc-link', '.tsc-credit summary', '.tsc-poster-cta', '.hero-theater'):
        assert 'min-height: 44px' in rule(sel), sel
    assert 'min-width: 44px' in rule('.tsc-btn')
    assert 'min-height: 52px' in rule('.tsc-enter')


def test_no_em_or_en_dash_anywhere_in_the_chapter():
    door = HERO_DOOR.group(0)
    for name, part in (('markup', MARKUP), ('css', CSS), ('js', JS), ('privacy', PRIVACY), ('door', door)):
        for bad in ('—', '–', '&mdash;', '&ndash;', '&#8212;', '&#8211;', '&#x2014;', '&#x2013;', '\\u2014', '\\u2013'):
            assert bad not in part, f'{name}: {bad!r}'


def test_solo_founder_voice():
    text = visible(MARKUP) + ' ' + visible(PRIVACY) + ' ' + ' '.join(js_strings(JS))
    text = text.replace('Our Deaf Ways', '')   # a series title
    assert not re.search(r"\b(we|our|ours|us|we're|we've|we'll)\b", text, re.I), re.findall(r".{30}\b(?:we|our|us)\b.{30}", text, re.I)


# ---- the records ------------------------------------------------------------------------------------------------

def test_counts_are_the_theaters_own():
    counts = collections.Counter(f['viewing'] for f in FILMS['films'])
    assert re.search(r'<span class="tsc-n">%d</span>' % len(FILMS['films']), MARKUP)
    assert '<span class="tsc-state">%d selections</span>' % len(FILMS['films']) in MARKUP
    for viewing, label in (('full-film', 'full films'), ('short', 'shorts'), ('trailer', 'trailers'), ('excerpt', 'excerpts'),
                           ('recorded-program', 'recorded programs'), ('official-page', 'official pages')):
        assert '<li><span class="tsc-c">%d</span>%s</li>' % (counts[viewing], label) in MARKUP, viewing


def test_featured_preview_matches_its_record():
    r = RECORDS[FEATURED]
    sec = re.search(r'<section class="tsc" id="theater"[^>]*>', MARKUP).group(0)
    assert 'data-video-id="%s"' % r['youtube_id'] in sec and 'data-provider="youtube"' in sec
    assert 'data-title="%s"' % r['title'] in sec
    assert 'data-note="%s."' % r['content_note'].split('. ')[0].rstrip('.') in sec
    m, s = re.fullmatch(r'(\d+)m (\d+)s', r['runtime']).groups()
    assert 'data-media-seconds="%d"' % (int(m) * 60 + int(s)) in sec
    text = ' '.join(visible(MARKUP).split())
    assert r['title'] in text and r['runtime'] in text and r['content_note'] in text and r['synopsis'] in text
    assert r['location'] in text and 'SBS On Demand' in r['publisher']
    assert 'Series created by Paula Thornton, Deaf Australia; additional editing by Max Banyat; music by Max Gosford.' in r['credits']
    assert 'Series created by Paula Thornton, Deaf Australia; additional editing by Max Banyat; music by Max Gosford.' in text
    assert r['viewing'] == 'recorded-program' and 'Recorded Program' in text and r['form'] == 'talk' and 'Recorded Talk' in text
    assert 'caption metadata' in r['accessibility_note'] and 'data-captions="en"' in sec
    assert html.unescape(re.search(r'id="tscPoster" href="([^"]+)"', MARKUP).group(1)) == r['watch_url']
    assert html.unescape(re.search(r'<a class="tsc-poster"[^>]*><img data-src="([^"]+)"', MARKUP).group(1)) == r['thumbnail_url']


@pytest.mark.parametrize('rid', [FEATURED] + STORIES)
def test_story_links_resolve_on_the_theater(rid):
    assert rid in RECORDS
    assert 'href="/theater#film-%s" data-story="%s"' % (rid, rid) in MARKUP
    assert THEATER.count('id="film-%s"' % rid) == 1


@pytest.mark.parametrize('rid', STORIES)
def test_each_story_matches_its_record(rid):
    r = RECORDS[rid]
    item = re.search(r'<li class="tsc-item"><a href="/theater#film-%s".*?</li>' % re.escape(rid), MARKUP, re.S).group(0)
    text = ' '.join(visible(item).split())
    title = r['title']
    assert html.unescape(re.search(r'aria-label="([^"]*)"', item).group(1)) == 'Explore ' + title
    assert html.unescape(re.search(r'<span class="tsc-item-title">([^<]*)</span>', item).group(1)) == title
    thumb = html.unescape(re.search(r'<img data-src="([^"]+)"', item).group(1))
    if r.get('youtube_id'):   # the strip uses YouTube's 480px frame of the same video, not the 1280px original
        assert r['thumbnail_url'].startswith('https://i.ytimg.com/vi/%s/maxresdefault.jpg' % r['youtube_id'])
        assert thumb == 'https://i.ytimg.com/vi/%s/hqdefault.jpg' % r['youtube_id']
        assert 'width="480" height="360"' in item
    else:
        assert thumb == r['thumbnail_url']
    who = html.unescape(re.search(r'<span class="tsc-item-who">([^<]*)</span>', item).group(1))
    credits = r['credits'] + ' ' + r['publisher']
    names = re.sub(r'^(Directors|Directed by|Produced by|Panel by|A project account by) ', '', who)
    for name in re.split(r' and ', names):
        assert name in credits, (rid, name)
    if r.get('runtime') and re.fullmatch(r'\d+m \d+s', r['runtime']):
        assert r['runtime'] in text
    if r.get('year'):
        assert str(r['year']) in text
    if r.get('location'):
        # the place line is the record's own location, or the land it names before its colon; every people kept
        place = re.search(r'<span class="tsc-item-place">([^<]*)</span>', item)
        loc = r['location'].rstrip('.')
        assert place and html.unescape(place.group(1)) in (loc, loc.split(':')[0]), (rid, place and place.group(1))
    pub = {'National Film Board of Canada', 'Cultural Survival', 'Tebtebba'}
    assert any(p in text for p in pub if p in r['publisher']) or 'Saami Council' in text
    kind = {'short': 'Short film', 'recorded-program': 'Recorded program', 'trailer': 'Official trailer'}[r['viewing']]
    assert kind in text


# ---- unchanged neighbours ------------------------------------------------------------------------------------------

def test_intro_sound_is_untouched():
    with open(os.path.join(ROOT, 'static', 'zotheos_intro.mp3'), 'rb') as f:
        assert hashlib.sha256(f.read()).hexdigest() == '3f0b3db8cccfff2b9c38808076aa30729e501cefc398522a25c5ec281b75aaa5'


def test_controller_checks_in_node():
    node = shutil.which('node')
    if not node:
        pytest.skip('node is not installed')
    r = subprocess.run([node, os.path.join(HERE, 'test_theater_showcase.cjs'), os.path.join(ROOT, 'index.html')],
                       capture_output=True, text=True, encoding='utf-8', timeout=120)
    assert r.returncode == 0, r.stdout[-4000:] + r.stderr[-2000:]
